"""Geometria 2D: contornos, furos, deslocamento e triangulacao.

Base do gerador de letra caixa. Tudo em milimetros, com o eixo Y ja apontando
para cima (a inversao do SVG acontece na leitura).

Convencao de orientacao, valida no modulo inteiro:

* contorno externo -> sentido anti-horario (area positiva);
* furo (contra-forma do "O", "A", "e") -> sentido horario (area negativa).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

Ponto = tuple[float, float]
Anel = list[Ponto]

EPS = 1e-9


# ------------------------------------------------------------------ basicos


def area_assinada(anel: Anel) -> float:
    """Area pela formula do cadarco. Positiva se anti-horario."""

    total = 0.0
    n = len(anel)
    for i in range(n):
        x1, y1 = anel[i]
        x2, y2 = anel[(i + 1) % n]
        total += x1 * y2 - x2 * y1
    return total / 2.0


def anti_horario(anel: Anel) -> bool:
    return area_assinada(anel) > 0


def como_anti_horario(anel: Anel) -> Anel:
    return anel if anti_horario(anel) else anel[::-1]


def como_horario(anel: Anel) -> Anel:
    return anel[::-1] if anti_horario(anel) else anel


def caixa(anel: Anel) -> tuple[float, float, float, float]:
    xs = [p[0] for p in anel]
    ys = [p[1] for p in anel]
    return min(xs), min(ys), max(xs), max(ys)


def perimetro(anel: Anel) -> float:
    n = len(anel)
    return sum(
        math.dist(anel[i], anel[(i + 1) % n]) for i in range(n)
    )


def dentro(ponto: Ponto, anel: Anel) -> bool:
    """Ponto dentro do anel, por lancamento de raio (par/impar)."""

    x, y = ponto
    dentro_ = False
    n = len(anel)
    for i in range(n):
        x1, y1 = anel[i]
        x2, y2 = anel[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            corte = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if corte > x:
                dentro_ = not dentro_
    return dentro_


def _cruz(o: Ponto, a: Ponto, b: Ponto) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def limpar(anel: Anel, tolerancia: float = 1e-7) -> Anel:
    """Remove pontos repetidos e colineares."""

    pontos: Anel = []
    for p in anel:
        if not pontos or math.dist(p, pontos[-1]) > tolerancia:
            pontos.append(p)
    while len(pontos) > 1 and math.dist(pontos[0], pontos[-1]) <= tolerancia:
        pontos.pop()
    if len(pontos) < 3:
        return pontos
    saida: Anel = []
    n = len(pontos)
    for i in range(n):
        a, b, c = pontos[i - 1], pontos[i], pontos[(i + 1) % n]
        if abs(_cruz(a, b, c)) > tolerancia * max(1.0, math.dist(a, c)):
            saida.append(b)
    return saida if len(saida) >= 3 else pontos


def simplificar(anel: Anel, tolerancia: float) -> Anel:
    """Douglas-Peucker num anel fechado, para segurar a contagem de pontos.

    Malhas de letra vindas de SVG chegam com milhares de pontos depois de
    achatar as curvas; a triangulacao e quadratica, entao vale reduzir.
    """

    if tolerancia <= 0 or len(anel) < 5:
        return anel

    def _dp(pontos: Anel) -> Anel:
        if len(pontos) < 3:
            return pontos
        inicio, fim = pontos[0], pontos[-1]
        comprimento = math.dist(inicio, fim)
        pior, indice = 0.0, 0
        for i in range(1, len(pontos) - 1):
            if comprimento < EPS:
                d = math.dist(pontos[i], inicio)
            else:
                d = abs(_cruz(inicio, fim, pontos[i])) / comprimento
            if d > pior:
                pior, indice = d, i
        if pior <= tolerancia:
            return [inicio, fim]
        return _dp(pontos[: indice + 1])[:-1] + _dp(pontos[indice:])

    # Corta o anel em duas metades para nao ancorar no mesmo ponto duas vezes.
    meio = len(anel) // 2
    a = _dp(anel[: meio + 1])
    b = _dp(anel[meio:] + [anel[0]])
    return limpar(a[:-1] + b[:-1])


# ------------------------------------------------------- contornos e faces


@dataclass
class Face:
    """Uma regiao preenchida: um contorno externo e seus furos."""

    externo: Anel
    furos: list[Anel] = field(default_factory=list)

    def caixa(self) -> tuple[float, float, float, float]:
        return caixa(self.externo)

    def area(self) -> float:
        return abs(area_assinada(self.externo)) - sum(
            abs(area_assinada(f)) for f in self.furos
        )

    def aneis(self) -> list[Anel]:
        return [self.externo, *self.furos]


def _ponto_representativo(anel: Anel, aperto: float = 1e-3) -> Ponto:
    """Um ponto dentro do anel e COLADO na borda dele.

    Colado de proposito: este ponto serve para descobrir aninhamento, e um
    ponto no meio do "B" cairia dentro da propria barriga da letra, fazendo
    o contorno externo se declarar furo. Andar so ``aperto`` para dentro a
    partir de um vertice mantem o ponto longe dos furos internos.
    """

    n = len(anel)
    for i in range(n):
        a, b, c = anel[i - 1], anel[i], anel[(i + 1) % n]
        meio = ((a[0] + c[0]) / 2.0, (a[1] + c[1]) / 2.0)
        candidato = (
            b[0] + (meio[0] - b[0]) * aperto,
            b[1] + (meio[1] - b[1]) * aperto,
        )
        if dentro(candidato, anel):
            return candidato
    # Formas degeneradas: cai para o centro de uma aresta empurrado para dentro
    for i in range(n):
        a, b = anel[i], anel[(i + 1) % n]
        candidato = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
        if dentro(candidato, anel):
            return candidato
    return anel[0]


def montar_faces(contornos: list[Anel]) -> list[Face]:
    """Separa contornos em faces externas e furos, pela regra par/impar.

    Um contorno contido num numero par de outros e material; num numero
    impar, e furo — e o furo pertence ao contorno mais interno que o contem.
    """

    aneis = [limpar(c) for c in contornos]
    aneis = [a for a in aneis if len(a) >= 3 and abs(area_assinada(a)) > EPS]
    if not aneis:
        return []

    pontos = [_ponto_representativo(a) for a in aneis]
    areas = [abs(area_assinada(a)) for a in aneis]
    contidos: list[list[int]] = []
    for i, ponto in enumerate(pontos):
        # So um anel MAIOR pode conter este: a area corta empate numerico
        # quando dois contornos se tocam.
        pais = [
            j
            for j, outro in enumerate(aneis)
            if j != i and areas[j] > areas[i] and dentro(ponto, outro)
        ]
        contidos.append(pais)

    faces: list[Face] = []
    indice_face: dict[int, int] = {}
    for i, pais in enumerate(contidos):
        if len(pais) % 2 == 0:  # profundidade par -> material
            indice_face[i] = len(faces)
            faces.append(Face(externo=como_anti_horario(aneis[i])))

    for i, pais in enumerate(contidos):
        if len(pais) % 2 == 0:
            continue
        # pai imediato: entre os que o contem, o de menor area
        pai = min(pais, key=lambda j: abs(area_assinada(aneis[j])))
        if pai in indice_face:
            faces[indice_face[pai]].furos.append(como_horario(aneis[i]))
    return faces


# ------------------------------------------------------------ deslocamento


def deslocar_anel(anel: Anel, distancia: float, limite_bico: float = 4.0) -> Anel:
    """Desloca o anel por ``distancia``, mantendo 1 ponto para 1 ponto.

    O sinal fala da REGIAO FECHADA pelo anel, nao do sentido dele: positivo
    cresce, negativo encolhe — vale igual para um contorno externo
    anti-horario e para um furo horario. A
    correspondencia um-a-um e proposital: e ela que deixa costurar a parede
    e o chanfro como uma tira de quadrilateros, sem reamostrar nada.

    Cantos agudos viram bico infinito; ``limite_bico`` corta o bico em
    multiplos da distancia (mesma ideia do miter limit dos fatiadores).
    """

    if abs(distancia) < EPS or len(anel) < 3:
        return list(anel)

    horario = not anti_horario(anel)
    d = -distancia if horario else distancia
    n = len(anel)
    saida: Anel = []

    for i in range(n):
        anterior, atual, seguinte = anel[i - 1], anel[i], anel[(i + 1) % n]
        e1 = (atual[0] - anterior[0], atual[1] - anterior[1])
        e2 = (seguinte[0] - atual[0], seguinte[1] - atual[1])
        c1 = math.hypot(*e1) or EPS
        c2 = math.hypot(*e2) or EPS
        # normal a direita da aresta: para fora num anel anti-horario
        n1 = (e1[1] / c1, -e1[0] / c1)
        n2 = (e2[1] / c2, -e2[0] / c2)
        bx, by = n1[0] + n2[0], n1[1] + n2[1]
        comprimento = math.hypot(bx, by)
        if comprimento < 1e-6:  # inversao de 180 graus
            saida.append((atual[0] + n2[0] * d, atual[1] + n2[1] * d))
            continue
        bx, by = bx / comprimento, by / comprimento
        cosseno = bx * n1[0] + by * n1[1]
        escala = 1.0 / max(cosseno, 1.0 / limite_bico)
        saida.append((atual[0] + bx * d * escala, atual[1] + by * d * escala))
    return saida


def _grosso_o_bastante(original: Anel, deslocado: Anel, distancia: float) -> bool:
    """O deslocamento sobreviveu, ou a forma era fina demais e se inverteu?"""

    if len(deslocado) < 3:
        return False
    area_nova = area_assinada(deslocado)
    area_velha = area_assinada(original)
    if area_velha == 0 or area_nova == 0:
        return False
    if (area_nova > 0) != (area_velha > 0):
        return False  # anel virou do avesso
    if abs(distancia) > EPS and abs(area_nova) >= abs(area_velha):
        return False  # encolher deveria diminuir a area
    return True


def erodir_face(face: Face, distancia: float) -> Face | None:
    """Encolhe a face por ``distancia`` — externo para dentro, furos para fora.

    Devolve ``None`` quando a parede nao cabe (traco mais fino que duas
    paredes), que e o sinal para a letra sair macica.

    Quando devolve uma face, os furos saem na MESMA ORDEM e com a MESMA
    contagem de pontos dos originais: e essa correspondencia um-a-um que
    permite costurar parede e chanfro como tiras de quadrilateros.
    """

    if distancia <= EPS:
        return Face(externo=list(face.externo), furos=[list(f) for f in face.furos])

    externo = deslocar_anel(face.externo, -distancia)
    if not _grosso_o_bastante(face.externo, externo, distancia):
        return None

    area_externo = abs(area_assinada(externo))
    furos: list[Anel] = []
    for furo in face.furos:
        # o vazio do furo cresce: e ele que come a parede por dentro
        dilatado = deslocar_anel(furo, distancia)
        if len(dilatado) < 3:
            continue
        area_furo = abs(area_assinada(dilatado))
        if area_furo <= abs(area_assinada(furo)):
            return None  # deslocamento se perdeu: sem cavidade confiavel
        if area_furo >= area_externo or not dentro(
            _ponto_representativo(dilatado), externo
        ):
            # o furo passou por cima da parede: nao ha cavidade possivel
            return None
        furos.append(dilatado)

    cavidade = Face(externo=externo, furos=furos)
    if cavidade.area() <= EPS:
        return None
    return cavidade


def circulo(centro: Ponto, raio: float, segmentos: int = 48) -> Anel:
    cx, cy = centro
    return [
        (
            cx + raio * math.cos(2.0 * math.pi * i / segmentos),
            cy + raio * math.sin(2.0 * math.pi * i / segmentos),
        )
        for i in range(segmentos)
    ]


# ------------------------------------------------------------ triangulacao


def _dentro_do_triangulo(p: Ponto, a: Ponto, b: Ponto, c: Ponto) -> bool:
    d1 = _cruz(a, b, p)
    d2 = _cruz(b, c, p)
    d3 = _cruz(c, a, p)
    negativo = d1 < -EPS or d2 < -EPS or d3 < -EPS
    positivo = d1 > EPS or d2 > EPS or d3 > EPS
    return not (negativo and positivo)


def _costurar_furo(externo: Anel, furo: Anel) -> Anel:
    """Liga um furo ao contorno externo por uma ponte de ida e volta.

    Receita do Eberly: pega o ponto do furo mais a direita (M), lanca um raio
    para +x e ancora no contorno. O resultado e um poligono simples com uma
    fenda de largura zero, que o recorte de orelhas ja sabe triangular.

    A ancora e o PROPRIO ponto de intersecao, inserido como vertice novo, e
    nao um vertice que ja existia: dois furos costurados no mesmo vertice
    criariam um ponto de pinca que trava o recorte de orelhas (foi o que
    aconteceu com a letra "B" na primeira versao). Ancora nova para cada
    furo, sem repetir vertice.
    """

    indice_m = max(range(len(furo)), key=lambda i: (furo[i][0], furo[i][1]))
    m = furo[indice_m]

    melhor_x = math.inf
    melhor_i = -1
    ponto_i: Ponto | None = None
    n = len(externo)
    for i in range(n):
        a, b = externo[i], externo[(i + 1) % n]
        if (a[1] > m[1]) == (b[1] > m[1]):
            continue  # a aresta nao cruza a horizontal de M
        if abs(b[1] - a[1]) < EPS:
            continue
        x = a[0] + (m[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
        if x >= m[0] - EPS and x < melhor_x:
            melhor_x, melhor_i, ponto_i = x, i, (x, m[1])

    if melhor_i < 0 or ponto_i is None:
        # furo fora do contorno (dado inconsistente): devolve so o externo
        return list(externo)

    a, b = externo[melhor_i], externo[(melhor_i + 1) % n]
    extremo = a if a[0] > b[0] else b

    # Vertices reflexos dentro do triangulo M-I-extremo bloqueiam a visada;
    # entre eles vale o de menor angulo com o eixo +x.
    bloqueio = -1
    melhor_angulo = math.inf
    for j in range(n):
        anterior, atual, seguinte = externo[j - 1], externo[j], externo[(j + 1) % n]
        if _cruz(anterior, atual, seguinte) > 0:
            continue  # convexo, nao bloqueia
        if not _dentro_do_triangulo(atual, m, ponto_i, extremo):
            continue
        angulo = abs(math.atan2(atual[1] - m[1], atual[0] - m[0]))
        if angulo < melhor_angulo:
            melhor_angulo, bloqueio = angulo, j

    poligono = list(externo)
    if bloqueio >= 0:
        indice_p = bloqueio
    elif math.dist(ponto_i, externo[melhor_i]) < EPS:
        indice_p = melhor_i
    elif math.dist(ponto_i, externo[(melhor_i + 1) % n]) < EPS:
        indice_p = (melhor_i + 1) % n
    else:
        indice_p = melhor_i + 1
        poligono.insert(indice_p, ponto_i)

    furo_girado = furo[indice_m:] + furo[:indice_m]
    return (
        poligono[: indice_p + 1]
        + furo_girado
        + [furo_girado[0]]
        + poligono[indice_p:]
    )


def _recortar_orelhas(poligono: Anel) -> list[tuple[Ponto, Ponto, Ponto]]:
    """Recorte de orelhas classico, num poligono simples anti-horario."""

    indices = list(range(len(poligono)))
    triangulos: list[tuple[Ponto, Ponto, Ponto]] = []
    tentativas_sem_orelha = 0

    while len(indices) > 3:
        achou = False
        total = len(indices)
        for k in range(total):
            anterior = poligono[indices[k - 1]]
            atual = poligono[indices[k]]
            seguinte = poligono[indices[(k + 1) % total]]
            if _cruz(anterior, atual, seguinte) <= EPS:
                continue  # reflexo ou degenerado
            bloqueado = False
            for j in indices:
                ponto = poligono[j]
                if ponto in (anterior, atual, seguinte):
                    continue
                if _cruz(poligono[j - 1], ponto, poligono[j]) > EPS:
                    continue  # so vertices reflexos podem bloquear
                if _dentro_do_triangulo(ponto, anterior, atual, seguinte):
                    bloqueado = True
                    break
            if bloqueado:
                continue
            triangulos.append((anterior, atual, seguinte))
            indices.pop(k)
            achou = True
            break
        if not achou:
            tentativas_sem_orelha += 1
            if tentativas_sem_orelha > 2:
                break  # poligono nao simples: entrega o que deu
            indices = indices[1:] + indices[:1]

    if len(indices) == 3:
        triangulos.append(tuple(poligono[i] for i in indices))  # type: ignore[arg-type]
    return triangulos


def triangular(face: Face) -> list[tuple[Ponto, Ponto, Ponto]]:
    """Triangula uma face com furos. Devolve triangulos anti-horarios."""

    externo = limpar(como_anti_horario(face.externo))
    if len(externo) < 3:
        return []
    poligono = externo
    # Furos da direita para a esquerda: a ponte de um nao atravessa o outro.
    for furo in sorted(face.furos, key=lambda f: -max(p[0] for p in f)):
        limpo = limpar(como_horario(furo))
        if len(limpo) >= 3:
            poligono = _costurar_furo(poligono, limpo)
    return _recortar_orelhas(poligono)
