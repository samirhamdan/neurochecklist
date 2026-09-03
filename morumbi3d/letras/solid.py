"""Construcao do solido da letra: extrusao, caixa oca, chanfro e furos.

Todo mundo aqui devolve lista de triangulos ``((x,y,z), (x,y,z), (x,y,z))``
com as normais para fora, no mesmo formato que ``morumbi3d.mesh`` consome —
o que deixa o gerador conferir o proprio resultado (malha fechada? cabe na
mesa?) antes de gravar o STL.
"""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass, field
from pathlib import Path

from .geom2d import (
    Anel, Face, Ponto, caixa, circulo, como_anti_horario, como_horario, dentro,
    erodir_face, triangular,
)

Triangulo = tuple[tuple[float, float, float], ...]


class GeometriaInvalida(ValueError):
    """Parametros que nao produzem solido imprimivel."""


# --------------------------------------------------------------- utilidades


def _face_em_z(face: Face, z: float, para_cima: bool) -> list[Triangulo]:
    """Tampa horizontal: triangula a face e leva para a altura ``z``."""

    triangulos = []
    for a, b, c in triangular(face):
        tri = ((a[0], a[1], z), (b[0], b[1], z), (c[0], c[1], z))
        triangulos.append(tri if para_cima else tri[::-1])
    return triangulos


def _parede(anel: Anel, z0: float, z1: float) -> list[Triangulo]:
    """Tira vertical ao longo do anel, entre duas alturas.

    A normal sai para a direita do sentido de percurso: num anel anti-horario
    ela aponta para fora do material, que e o que se quer no contorno
    externo; para a parede de uma cavidade, passe o anel invertido.
    """

    triangulos = []
    n = len(anel)
    for i in range(n):
        x0, y0 = anel[i]
        x1, y1 = anel[(i + 1) % n]
        a = (x0, y0, z0)
        b = (x1, y1, z0)
        c = (x1, y1, z1)
        d = (x0, y0, z1)
        triangulos.append((a, b, c))
        triangulos.append((a, c, d))
    return triangulos


def _loft(inferior: Anel, superior: Anel, z0: float, z1: float) -> list[Triangulo]:
    """Costura dois aneis de MESMA contagem de pontos (usado no chanfro)."""

    if len(inferior) != len(superior):
        raise GeometriaInvalida(
            f"chanfro pede aneis correspondentes ({len(inferior)} x {len(superior)})"
        )
    triangulos = []
    n = len(inferior)
    for i in range(n):
        a = (*inferior[i], z0)
        b = (*inferior[(i + 1) % n], z0)
        c = (*superior[(i + 1) % n], z1)
        d = (*superior[i], z1)
        triangulos.append((a, b, c))
        triangulos.append((a, c, d))
    return triangulos


def _paredes_da_face(face: Face, z0: float, z1: float) -> list[Triangulo]:
    """Paredes externas de uma face solida (externo + contornos dos furos)."""

    triangulos = _parede(como_anti_horario(face.externo), z0, z1)
    for furo in face.furos:
        triangulos += _parede(como_horario(furo), z0, z1)
    return triangulos


def _paredes_da_cavidade(cavidade: Face, z0: float, z1: float) -> list[Triangulo]:
    """Paredes de um vazio: normais apontando PARA DENTRO do vazio."""

    triangulos = _parede(como_horario(cavidade.externo), z0, z1)
    for furo in cavidade.furos:
        triangulos += _parede(como_anti_horario(furo), z0, z1)
    return triangulos


def _anel_da_parede(face: Face, cavidade: Face) -> list[Face]:
    """A secao de material no fundo: a face menos a cavidade.

    Sai como uma lista de faces: o anel entre o contorno externo e a
    cavidade, mais um anel em volta de cada contra-forma da letra.
    """

    partes = [
        Face(
            externo=como_anti_horario(face.externo),
            furos=[como_horario(cavidade.externo)],
        )
    ]
    for furo_face, furo_cavidade in zip(face.furos, cavidade.furos):
        partes.append(
            Face(
                externo=como_anti_horario(furo_cavidade),
                furos=[como_horario(furo_face)],
            )
        )
    return partes


# ------------------------------------------------------------------- escala


def medidas(faces: list[Face]) -> tuple[float, float, float, float]:
    pontos = [p for f in faces for anel in f.aneis() for p in anel]
    if not pontos:
        raise GeometriaInvalida("nenhum contorno no arquivo")
    return caixa(pontos)


def escalar_para_altura(faces: list[Face], altura_mm: float) -> list[Face]:
    """Escala uniforme para a altura pedida e encosta a peca na origem."""

    if altura_mm <= 0:
        raise GeometriaInvalida("altura deve ser maior que zero")
    x0, y0, x1, y1 = medidas(faces)
    alto = y1 - y0
    if alto <= 0:
        raise GeometriaInvalida("contornos sem altura (arquivo degenerado)")
    escala = altura_mm / alto

    def mover(anel: Anel) -> Anel:
        return [((x - x0) * escala, (y - y0) * escala) for x, y in anel]

    return [Face(externo=mover(f.externo), furos=[mover(h) for h in f.furos]) for f in faces]


# -------------------------------------------------------------------- furos


def _circulo_cabe(anel: Anel, regiao: Face) -> bool:
    """O circulo esta inteiro dentro da regiao (e fora das contra-formas)?"""

    for ponto in anel:
        if not dentro(ponto, regiao.externo):
            return False
        if any(dentro(ponto, furo) for furo in regiao.furos):
            return False
    return True


def furos_automaticos(regiao: Face, diametro: float, espacamento: float) -> list[Ponto]:
    """Distribui furos numa grade dentro da regiao util."""

    if diametro <= 0 or espacamento <= 0:
        return []
    x0, y0, x1, y1 = caixa(regiao.externo)
    raio = diametro / 2.0
    posicoes: list[Ponto] = []
    passo = espacamento
    y = y0 + passo / 2.0
    while y < y1:
        x = x0 + passo / 2.0
        while x < x1:
            if _circulo_cabe(circulo((x, y), raio + 0.6, 16), regiao):
                posicoes.append((x, y))
            x += passo
        y += passo
    return posicoes


# ------------------------------------------------------------------ modelos


@dataclass
class Letra:
    """Resultado da geracao."""

    triangulos: list[Triangulo] = field(default_factory=list)
    macica: bool = False
    profundidade: float = 0.0
    furos: list[Ponto] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    remendos: int = 0
    """Juntas em T costuradas — detalhe interno, nao e problema do usuario."""

    def __len__(self) -> int:
        return len(self.triangulos)


def gerar(
    faces: list[Face],
    *,
    profundidade: float = 20.0,
    parede: float = 2.0,
    frente: float = 2.0,
    chanfro: float = 0.0,
    macica: bool = False,
    furos: list[Ponto] | None = None,
    furos_auto: bool = False,
    espacamento_furo: float = 60.0,
    diametro_furo: float = 4.0,
) -> Letra:
    """Monta o solido da letra a partir das faces 2D.

    ``macica=False`` produz a letra caixa: face na frente, paredes de
    ``parede`` mm e fundo aberto. Quando o traco da letra e fino demais para
    duas paredes, a peca sai macica e o aviso explica por que.
    """

    if profundidade <= 0:
        raise GeometriaInvalida("profundidade deve ser maior que zero")
    if not faces:
        raise GeometriaInvalida("nenhuma face para gerar")

    resultado = Letra(profundidade=profundidade)
    if chanfro < 0:
        chanfro = 0.0
    if chanfro >= profundidade:
        raise GeometriaInvalida(
            f"chanfro ({chanfro} mm) tem que ser menor que a profundidade "
            f"({profundidade} mm)"
        )
    if not macica and chanfro >= frente:
        resultado.avisos.append(
            f"chanfro de {chanfro} mm >= face de {frente} mm: a face foi "
            f"engrossada para {chanfro + 0.4:.1f} mm para nao furar a frente"
        )
        frente = chanfro + 0.4
    if not macica and frente >= profundidade:
        raise GeometriaInvalida(
            f"face ({frente} mm) tem que ser menor que a profundidade "
            f"({profundidade} mm)"
        )

    z_topo = profundidade
    z_chanfro = profundidade - chanfro

    for face in faces:
        triangulos: list[Triangulo] = []
        face_topo = face
        if chanfro > 0:
            encolhida = erodir_face(face, chanfro)
            if encolhida is None:
                resultado.avisos.append(
                    "chanfro maior que a metade do traco em alguma parte: "
                    "gerado sem chanfro nessa face"
                )
                chanfro_local = 0.0
            else:
                face_topo = encolhida
                chanfro_local = chanfro
        else:
            chanfro_local = 0.0

        cavidade = None if macica else erodir_face(face, parede)
        if not macica and cavidade is None:
            resultado.avisos.append(
                f"traco fino demais para parede de {parede} mm: face gerada macica"
            )

        # --- furos ------------------------------------------------------
        # Cada face tem a sua area util. Um furo pedido a mao que nao cabe
        # AQUI pode caber na letra do lado, entao o aviso so sai no fim,
        # quando nenhuma face aceitou. Os furos automaticos sao calculados
        # por face e nunca viram aviso: sao sugestao, nao pedido.
        regiao_furo = cavidade if cavidade is not None else face
        aceitos: list[Anel] = []
        pedidos = list(furos or [])
        if furos_auto:
            pedidos += furos_automaticos(regiao_furo, diametro_furo, espacamento_furo)
        for centro in pedidos:
            anel = como_horario(circulo(centro, diametro_furo / 2.0, 32))
            if _circulo_cabe(anel, regiao_furo) and _circulo_cabe(anel, face_topo):
                aceitos.append(anel)
                resultado.furos.append(centro)

        topo_com_furos = Face(
            externo=face_topo.externo, furos=[*face_topo.furos, *aceitos]
        )

        if cavidade is None:  # ---------------------------------- macica
            triangulos += _face_em_z(topo_com_furos, z_topo, para_cima=True)
            base = Face(externo=face.externo, furos=[*face.furos, *aceitos])
            triangulos += _face_em_z(base, 0.0, para_cima=False)
            triangulos += _paredes_da_face(face, 0.0, z_chanfro if chanfro_local else z_topo)
            if chanfro_local:
                triangulos += _loft(face.externo, face_topo.externo, z_chanfro, z_topo)
                for original, encolhido in zip(face.furos, face_topo.furos):
                    triangulos += _loft(original, encolhido, z_chanfro, z_topo)
            for anel in aceitos:  # furo passante
                triangulos += _parede(anel, 0.0, z_topo)
            resultado.macica = True
        else:  # ------------------------------------------------- caixa
            z_teto = profundidade - frente
            triangulos += _face_em_z(topo_com_furos, z_topo, para_cima=True)
            for parte in _anel_da_parede(face, cavidade):
                triangulos += _face_em_z(parte, 0.0, para_cima=False)
            triangulos += _paredes_da_face(face, 0.0, z_chanfro if chanfro_local else z_topo)
            if chanfro_local:
                triangulos += _loft(face.externo, face_topo.externo, z_chanfro, z_topo)
                for original, encolhido in zip(face.furos, face_topo.furos):
                    triangulos += _loft(original, encolhido, z_chanfro, z_topo)
            triangulos += _paredes_da_cavidade(cavidade, 0.0, z_teto)
            teto = Face(externo=cavidade.externo, furos=[*cavidade.furos, *aceitos])
            triangulos += _face_em_z(teto, z_teto, para_cima=False)
            for anel in aceitos:  # furo so na face da frente
                triangulos += _parede(anel, z_teto, z_topo)

        resultado.triangulos += triangulos

    if not resultado.triangulos:
        raise GeometriaInvalida("nenhum triangulo gerado")

    for centro in furos or []:
        if centro not in resultado.furos:
            resultado.avisos.append(
                f"furo pedido em ({centro[0]:.1f}, {centro[1]:.1f}) cai fora da "
                "area util de qualquer letra e foi ignorado"
            )

    resultado.triangulos, resultado.remendos = costurar_juntas_t(resultado.triangulos)
    return resultado


# ---------------------------------------------------------------- gravacao


def escrever_stl(triangulos: list[Triangulo], caminho: Path | str, nome: str = "letra") -> Path:
    """Grava STL binario, calculando a normal de cada face."""

    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("wb") as fh:
        cabecalho = nome.encode("ascii", "replace")[:79]
        fh.write(cabecalho + b"\0" * (80 - len(cabecalho)))
        fh.write(struct.pack("<I", len(triangulos)))
        for a, b, c in triangulos:
            ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
            vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
            nx = uy * vz - uz * vy
            ny = uz * vx - ux * vz
            nz = ux * vy - uy * vx
            norma = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            fh.write(struct.pack("<3f", nx / norma, ny / norma, nz / norma))
            for ponto in (a, b, c):
                fh.write(struct.pack("<3f", *ponto))
            fh.write(struct.pack("<H", 0))
    return caminho


# ------------------------------------------------------- reparo de junta T


def _chave(p, casas: int = 6):
    return (round(p[0], casas), round(p[1], casas), round(p[2], casas))


def costurar_juntas_t(
    triangulos: list[Triangulo], tolerancia: float = 1e-4, voltas: int = 6
) -> tuple[list[Triangulo], int]:
    """Fecha junta em T: vertice pousado no MEIO da aresta de outra face.

    Acontece de forma legitima aqui: a triangulacao costura o furo ao
    contorno inserindo um vertice novo na borda da tampa, e a parede — que
    veio do anel original — nao tem esse vertice. A aresta fica sem par e a
    malha aparece "aberta" para o fatiador, mesmo com a geometria certa.

    O conserto e local: acha a aresta de borda, encontra o vertice que esta
    em cima dela e divide o triangulo dono da aresta nesse ponto. Devolve os
    triangulos e quantas divisoes foram feitas.
    """

    indices: dict[tuple, int] = {}
    vertices: list[tuple[float, float, float]] = []
    faces: list[list[int]] = []
    for tri in triangulos:
        face = []
        for ponto in tri:
            k = _chave(ponto)
            i = indices.get(k)
            if i is None:
                i = len(vertices)
                indices[k] = i
                vertices.append((float(ponto[0]), float(ponto[1]), float(ponto[2])))
            face.append(i)
        if face[0] != face[1] and face[1] != face[2] and face[0] != face[2]:
            faces.append(face)

    total_divisoes = 0
    for _ in range(voltas):
        contagem: dict[tuple[int, int], int] = {}
        for a, b, c in faces:
            for i, j in ((a, b), (b, c), (c, a)):
                chave = (i, j) if i < j else (j, i)
                contagem[chave] = contagem.get(chave, 0) + 1
        bordas = [e for e, n in contagem.items() if n == 1]
        if not bordas:
            break
        # So vertices que ja estao numa borda podem estar no meio de outra.
        candidatos = sorted({v for e in bordas for v in e})

        # Uma aresta pode ter MUITOS vertices em cima: a tampa de um corte
        # perde os pontos colineares que a parede manteve. Por isso a aresta
        # e dividida de uma vez em leque, e nao um ponto por volta.
        divisoes: dict[tuple[int, int], list[int]] = {}
        for i, j in bordas:
            a, b = vertices[i], vertices[j]
            comprimento = math.dist(a, b)
            if comprimento < tolerancia:
                continue
            encontrados: list[tuple[float, int]] = []
            for v in candidatos:
                if v in (i, j):
                    continue
                p = vertices[v]
                t = sum((p[k] - a[k]) * (b[k] - a[k]) for k in range(3)) / (comprimento ** 2)
                if not (1e-9 < t < 1 - 1e-9):
                    continue
                projetado = tuple(a[k] + (b[k] - a[k]) * t for k in range(3))
                if math.dist(p, projetado) > tolerancia:
                    continue
                encontrados.append((t, v))
            if encontrados:
                encontrados.sort()
                divisoes[(i, j)] = [v for _, v in encontrados]

        if not divisoes:
            break

        novas: list[list[int]] = []
        for face in faces:
            dividida = False
            for k in range(3):
                a, b, c = face[k], face[(k + 1) % 3], face[(k + 2) % 3]
                meio = divisoes.get((a, b)) or divisoes.get((b, a))
                if not meio:
                    continue
                if divisoes.get((b, a)) and not divisoes.get((a, b)):
                    meio = list(reversed(meio))
                corrente = [a, *meio, b]
                for n in range(len(corrente) - 1):
                    novas.append([corrente[n], corrente[n + 1], c])
                total_divisoes += len(meio)
                dividida = True
                break
            if not dividida:
                novas.append(face)
        faces = novas

    saida = [
        (vertices[a], vertices[b], vertices[c])
        for a, b, c in faces
        if a != b and b != c and a != c
    ]
    return saida, total_divisoes
