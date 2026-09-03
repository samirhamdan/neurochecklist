"""Leitura de SVG: caminhos, formas basicas e transformacoes.

Entrega os contornos ja em coordenadas de trabalho — Y para cima, curvas
achatadas em segmentos de reta dentro da tolerancia pedida. Nao renderiza
nada: so precisa do contorno preenchido da letra.

Um SVG de letra caixa vem, na pratica, de um texto convertido em curvas no
Illustrator/Inkscape/CorelDRAW. Traco (``stroke``) e ignorado de proposito:
o que vira material e o preenchimento.
"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .geom2d import Anel, Ponto, limpar

# ------------------------------------------------------------ transformacao

Matriz = tuple[float, float, float, float, float, float]
IDENTIDADE: Matriz = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def compor(m: Matriz, n: Matriz) -> Matriz:
    """m aplicada depois de n (m * n)."""

    a1, b1, c1, d1, e1, f1 = m
    a2, b2, c2, d2, e2, f2 = n
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    )


def aplicar(m: Matriz, p: Ponto) -> Ponto:
    a, b, c, d, e, f = m
    return (a * p[0] + c * p[1] + e, b * p[0] + d * p[1] + f)


_RE_TRANSFORM = re.compile(r"(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)")
_RE_NUM = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")


def _numeros(texto: str) -> list[float]:
    return [float(n) for n in _RE_NUM.findall(texto or "")]


def ler_transform(texto: str | None) -> Matriz:
    if not texto:
        return IDENTIDADE
    resultado = IDENTIDADE
    for nome, argumentos in _RE_TRANSFORM.findall(texto):
        v = _numeros(argumentos)
        if nome == "matrix" and len(v) >= 6:
            m = (v[0], v[1], v[2], v[3], v[4], v[5])
        elif nome == "translate" and v:
            m = (1.0, 0.0, 0.0, 1.0, v[0], v[1] if len(v) > 1 else 0.0)
        elif nome == "scale" and v:
            sx = v[0]
            sy = v[1] if len(v) > 1 else sx
            m = (sx, 0.0, 0.0, sy, 0.0, 0.0)
        elif nome == "rotate" and v:
            rad = math.radians(v[0])
            cos, sen = math.cos(rad), math.sin(rad)
            m = (cos, sen, -sen, cos, 0.0, 0.0)
            if len(v) >= 3:
                cx, cy = v[1], v[2]
                m = compor(
                    (1.0, 0.0, 0.0, 1.0, cx, cy),
                    compor(m, (1.0, 0.0, 0.0, 1.0, -cx, -cy)),
                )
        elif nome == "skewX" and v:
            m = (1.0, 0.0, math.tan(math.radians(v[0])), 1.0, 0.0, 0.0)
        elif nome == "skewY" and v:
            m = (1.0, math.tan(math.radians(v[0])), 0.0, 1.0, 0.0, 0.0)
        else:
            continue
        resultado = compor(resultado, m)
    return resultado


# ---------------------------------------------------------------- achatamento


def _achatar_cubica(p0, p1, p2, p3, tolerancia: float, saida: list, nivel: int = 0):
    """Subdivide ate a curva caber dentro da tolerancia (De Casteljau)."""

    if nivel >= 16:
        saida.append(p3)
        return
    dx, dy = p3[0] - p0[0], p3[1] - p0[1]
    corda = math.hypot(dx, dy)
    if corda < 1e-12:
        planura = max(math.dist(p1, p0), math.dist(p2, p0))
    else:
        planura = max(
            abs((p1[0] - p0[0]) * dy - (p1[1] - p0[1]) * dx),
            abs((p2[0] - p0[0]) * dy - (p2[1] - p0[1]) * dx),
        ) / corda
    if planura <= tolerancia:
        saida.append(p3)
        return

    def meio(a, b):
        return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)

    p01, p12, p23 = meio(p0, p1), meio(p1, p2), meio(p2, p3)
    p012, p123 = meio(p01, p12), meio(p12, p23)
    centro = meio(p012, p123)
    _achatar_cubica(p0, p01, p012, centro, tolerancia, saida, nivel + 1)
    _achatar_cubica(centro, p123, p23, p3, tolerancia, saida, nivel + 1)


def _cubica_de_quadratica(p0, p1, p2):
    return (
        (p0[0] + 2.0 / 3.0 * (p1[0] - p0[0]), p0[1] + 2.0 / 3.0 * (p1[1] - p0[1])),
        (p2[0] + 2.0 / 3.0 * (p1[0] - p2[0]), p2[1] + 2.0 / 3.0 * (p1[1] - p2[1])),
    )


def _achatar_arco(p0, rx, ry, rotacao, arco_grande, varredura, p1, tolerancia, saida):
    """Arco eliptico do SVG -> segmentos (parametrizacao do apendice F.6)."""

    if abs(rx) < 1e-12 or abs(ry) < 1e-12:
        saida.append(p1)
        return
    rx, ry = abs(rx), abs(ry)
    rad = math.radians(rotacao)
    cos, sen = math.cos(rad), math.sin(rad)
    dx2 = (p0[0] - p1[0]) / 2.0
    dy2 = (p0[1] - p1[1]) / 2.0
    x1 = cos * dx2 + sen * dy2
    y1 = -sen * dx2 + cos * dy2

    correcao = x1 * x1 / (rx * rx) + y1 * y1 / (ry * ry)
    if correcao > 1.0:
        escala = math.sqrt(correcao)
        rx, ry = rx * escala, ry * escala

    denominador = rx * rx * y1 * y1 + ry * ry * x1 * x1
    if denominador < 1e-12:
        saida.append(p1)
        return
    numerador = max(0.0, rx * rx * ry * ry - denominador)
    coeficiente = math.sqrt(numerador / denominador)
    if arco_grande == varredura:
        coeficiente = -coeficiente
    cx1 = coeficiente * rx * y1 / ry
    cy1 = -coeficiente * ry * x1 / rx
    cx = cos * cx1 - sen * cy1 + (p0[0] + p1[0]) / 2.0
    cy = sen * cx1 + cos * cy1 + (p0[1] + p1[1]) / 2.0

    def angulo(ux, uy, vx, vy):
        pontos = ux * vx + uy * vy
        normas = math.hypot(ux, uy) * math.hypot(vx, vy)
        if normas < 1e-12:
            return 0.0
        valor = max(-1.0, min(1.0, pontos / normas))
        sinal = -1.0 if (ux * vy - uy * vx) < 0 else 1.0
        return sinal * math.acos(valor)

    theta1 = angulo(1.0, 0.0, (x1 - cx1) / rx, (y1 - cy1) / ry)
    delta = angulo(
        (x1 - cx1) / rx, (y1 - cy1) / ry, (-x1 - cx1) / rx, (-y1 - cy1) / ry
    )
    if not varredura and delta > 0:
        delta -= 2.0 * math.pi
    elif varredura and delta < 0:
        delta += 2.0 * math.pi

    raio = max(rx, ry)
    passo = 2.0 * math.acos(max(-1.0, min(1.0, 1.0 - tolerancia / raio))) if raio > tolerancia else math.pi / 8.0
    segmentos = max(2, int(math.ceil(abs(delta) / max(passo, 1e-3))))
    for i in range(1, segmentos + 1):
        t = theta1 + delta * i / segmentos
        x = cos * rx * math.cos(t) - sen * ry * math.sin(t) + cx
        y = sen * rx * math.cos(t) + cos * ry * math.sin(t) + cy
        saida.append((x, y))


# ------------------------------------------------------------------ caminhos

_RE_COMANDO = re.compile(r"([MmZzLlHhVvCcSsQqTtAa])|([-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?)")


def _tokens(d: str):
    for comando, numero in _RE_COMANDO.findall(d or ""):
        yield ("cmd", comando) if comando else ("num", float(numero))


def ler_path(d: str, tolerancia: float = 0.1) -> list[Anel]:
    """Converte o atributo ``d`` de um <path> em contornos fechados."""

    contornos: list[Anel] = []
    atual: Anel = []
    pilha = list(_tokens(d))
    posicao = 0
    inicio: Ponto = (0.0, 0.0)
    ponto: Ponto = (0.0, 0.0)
    controle: Ponto | None = None
    comando = ""

    def numeros(quantos: int) -> list[float] | None:
        nonlocal posicao
        valores = []
        while len(valores) < quantos and posicao < len(pilha):
            tipo, valor = pilha[posicao]
            if tipo != "num":
                return None
            valores.append(valor)
            posicao += 1
        return valores if len(valores) == quantos else None

    def fechar():
        nonlocal atual
        if len(atual) >= 3:
            contornos.append(atual)
        atual = []

    while posicao < len(pilha):
        tipo, valor = pilha[posicao]
        if tipo == "cmd":
            comando = valor
            posicao += 1
            if comando in "Zz":
                fechar()
                ponto = inicio
                controle = None
                continue
        elif not comando:
            posicao += 1
            continue
        elif comando in "Mm":
            comando = "L" if comando == "M" else "l"  # coordenadas extras viram linha

        relativo = comando.islower()
        chave = comando.upper()

        if chave == "M":
            v = numeros(2)
            if v is None:
                break
            fechar()
            ponto = (ponto[0] + v[0], ponto[1] + v[1]) if relativo else (v[0], v[1])
            inicio = ponto
            atual = [ponto]
            controle = None
        elif chave == "L":
            v = numeros(2)
            if v is None:
                break
            ponto = (ponto[0] + v[0], ponto[1] + v[1]) if relativo else (v[0], v[1])
            atual.append(ponto)
            controle = None
        elif chave == "H":
            v = numeros(1)
            if v is None:
                break
            ponto = (ponto[0] + v[0], ponto[1]) if relativo else (v[0], ponto[1])
            atual.append(ponto)
            controle = None
        elif chave == "V":
            v = numeros(1)
            if v is None:
                break
            ponto = (ponto[0], ponto[1] + v[0]) if relativo else (ponto[0], v[0])
            atual.append(ponto)
            controle = None
        elif chave in ("C", "S"):
            v = numeros(6 if chave == "C" else 4)
            if v is None:
                break
            if chave == "C":
                c1 = (ponto[0] + v[0], ponto[1] + v[1]) if relativo else (v[0], v[1])
                c2 = (ponto[0] + v[2], ponto[1] + v[3]) if relativo else (v[2], v[3])
                fim = (ponto[0] + v[4], ponto[1] + v[5]) if relativo else (v[4], v[5])
            else:
                c1 = (
                    (2 * ponto[0] - controle[0], 2 * ponto[1] - controle[1])
                    if controle
                    else ponto
                )
                c2 = (ponto[0] + v[0], ponto[1] + v[1]) if relativo else (v[0], v[1])
                fim = (ponto[0] + v[2], ponto[1] + v[3]) if relativo else (v[2], v[3])
            if not atual:
                atual = [ponto]
            _achatar_cubica(ponto, c1, c2, fim, tolerancia, atual)
            controle, ponto = c2, fim
        elif chave in ("Q", "T"):
            v = numeros(4 if chave == "Q" else 2)
            if v is None:
                break
            if chave == "Q":
                q = (ponto[0] + v[0], ponto[1] + v[1]) if relativo else (v[0], v[1])
                fim = (ponto[0] + v[2], ponto[1] + v[3]) if relativo else (v[2], v[3])
            else:
                q = (
                    (2 * ponto[0] - controle[0], 2 * ponto[1] - controle[1])
                    if controle
                    else ponto
                )
                fim = (ponto[0] + v[0], ponto[1] + v[1]) if relativo else (v[0], v[1])
            c1, c2 = _cubica_de_quadratica(ponto, q, fim)
            if not atual:
                atual = [ponto]
            _achatar_cubica(ponto, c1, c2, fim, tolerancia, atual)
            controle, ponto = q, fim
        elif chave == "A":
            v = numeros(7)
            if v is None:
                break
            fim = (ponto[0] + v[5], ponto[1] + v[6]) if relativo else (v[5], v[6])
            if not atual:
                atual = [ponto]
            _achatar_arco(
                ponto, v[0], v[1], v[2], bool(v[3]), bool(v[4]), fim, tolerancia, atual
            )
            controle, ponto = None, fim
        else:
            posicao += 1
            continue

    fechar()
    return [c for c in (limpar(c) for c in contornos) if len(c) >= 3]


# ------------------------------------------------------------ formas basicas


def _contorno_de_forma(tag: str, atributos: dict, tolerancia: float) -> list[Anel]:
    def n(chave: str, padrao: float = 0.0) -> float:
        try:
            return float(_RE_NUM.findall(atributos.get(chave, ""))[0])
        except (IndexError, ValueError, TypeError):
            return padrao

    if tag == "rect":
        x, y, w, h = n("x"), n("y"), n("width"), n("height")
        if w <= 0 or h <= 0:
            return []
        return [[(x, y), (x + w, y), (x + w, y + h), (x, y + h)]]
    if tag in ("circle", "ellipse"):
        cx, cy = n("cx"), n("cy")
        rx = n("r") or n("rx")
        ry = n("r") or n("ry")
        if rx <= 0 or ry <= 0:
            return []
        raio = max(rx, ry)
        passo = (
            2.0 * math.acos(max(-1.0, min(1.0, 1.0 - tolerancia / raio)))
            if raio > tolerancia
            else math.pi / 16.0
        )
        segmentos = max(12, int(math.ceil(2 * math.pi / max(passo, 1e-3))))
        return [
            [
                (cx + rx * math.cos(2 * math.pi * i / segmentos),
                 cy + ry * math.sin(2 * math.pi * i / segmentos))
                for i in range(segmentos)
            ]
        ]
    if tag in ("polygon", "polyline"):
        v = _numeros(atributos.get("points", ""))
        pontos = [(v[i], v[i + 1]) for i in range(0, len(v) - 1, 2)]
        return [pontos] if len(pontos) >= 3 else []
    return []


_FORMAS = {"rect", "circle", "ellipse", "polygon", "polyline"}


def carregar_svg(caminho: Path | str, tolerancia: float = 0.1) -> list[Anel]:
    """Le um SVG e devolve os contornos, com Y ja apontando para cima."""

    caminho = Path(caminho)
    if not caminho.is_file():
        raise FileNotFoundError(f"SVG nao encontrado: {caminho}")
    try:
        raiz = ET.parse(caminho).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"SVG invalido: {exc}") from exc

    contornos: list[Anel] = []

    def visitar(elemento: ET.Element, matriz: Matriz) -> None:
        tag = elemento.tag.split("}")[-1]
        atual = compor(matriz, ler_transform(elemento.get("transform")))
        if tag == "path":
            for anel in ler_path(elemento.get("d", ""), tolerancia):
                contornos.append([aplicar(atual, p) for p in anel])
        elif tag in _FORMAS:
            for anel in _contorno_de_forma(tag, dict(elemento.attrib), tolerancia):
                contornos.append([aplicar(atual, p) for p in anel])
        elif tag in ("defs", "clipPath", "mask", "symbol"):
            return  # nao viram material
        for filho in elemento:
            visitar(filho, atual)

    visitar(raiz, IDENTIDADE)
    # SVG cresce para baixo; o mundo 3D cresce para cima.
    espelhados = [[(x, -y) for x, y in anel] for anel in contornos]
    return [c for c in (limpar(a) for a in espelhados) if len(c) >= 3]
