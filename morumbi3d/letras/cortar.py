"""Corte de letra maior que a mesa.

Letreiro nao cabe na impressora: uma letra de 40 cm nao entra numa mesa de
25 cm. Este modulo corta o solido por planos verticais e TAMPA cada corte,
para cada pedaco sair fechado e imprimivel — e depois colar.

O corte e sempre vertical (paralelo a Z), entao a face da letra continua
inteira em cada pedaco e a emenda fica na lateral, onde disfarca melhor.
"""

from __future__ import annotations

import math

from .geom2d import montar_faces, triangular
from .malha import cortar_um_plano
from .solid import Triangulo, costurar_juntas_t

EPS = 1e-7


def sugerir_cortes(
    largura: float,
    profundidade_peca: float,
    mesa_x: float,
    mesa_y: float,
) -> list[float]:
    """Onde cortar uma peca de ``largura`` para caber em ``mesa_x``.

    Devolve as posicoes dos planos, em partes iguais — emenda regular fica
    menos visivel do que um pedaco grande e uma lasquinha. ``pedacos_extra``
    divide em mais partes do que o minimo, para deslocar TODOS os planos de
    uma vez quando algum deles cai num lugar ruim.
    """

    util = mesa_x if profundidade_peca <= mesa_y else min(mesa_x, mesa_y)
    if util <= 0 or largura <= util:
        return []
    pedacos = int(math.ceil(largura / util))
    passo = largura / pedacos
    return [passo * i for i in range(1, pedacos)]


def _interpolar(a, b, t):
    return tuple(a[k] + (b[k] - a[k]) * t for k in range(3))


def _fatiar_triangulo(tri: Triangulo, eixo: int, corte: float):
    """Divide um triangulo pelo plano. Devolve (abaixo, acima, segmento).

    Vertice pousado EXATAMENTE no plano conta como ponto de corte. Sem isso,
    cortar um circulo bem no meio (onde o plano passa por cima de vertices)
    deixa buracos na tampa — o plano nao gera intersecao naquela aresta e a
    borda da tampa fica sem par.
    """

    d = [v[eixo] - corte for v in tri]
    if all(x >= -EPS for x in d):
        return [], [tri], None
    if all(x <= EPS for x in d):
        return [tri], [], None

    abaixo, acima = [], []
    cortes: list = []
    vistos: set = set()

    def anotar(ponto):
        k = _chave(ponto)
        if k not in vistos:
            vistos.add(k)
            cortes.append(ponto)

    for i in range(3):
        atual, seguinte = tri[i], tri[(i + 1) % 3]
        di, dj = d[i], d[(i + 1) % 3]
        if di <= EPS:
            abaixo.append(atual)
        if di >= -EPS:
            acima.append(atual)
        if abs(di) <= EPS:
            anotar(atual)  # vertice em cima do plano
        elif (di < -EPS and dj > EPS) or (di > EPS and dj < -EPS):
            t = di / (di - dj)
            ponto = _interpolar(atual, seguinte, t)
            abaixo.append(ponto)
            acima.append(ponto)
            anotar(ponto)

    def leque(pontos):
        return [
            (pontos[0], pontos[i], pontos[i + 1]) for i in range(1, len(pontos) - 1)
        ] if len(pontos) >= 3 else []

    segmento = (cortes[0], cortes[1]) if len(cortes) == 2 else None
    return leque(abaixo), leque(acima), segmento


def _chave(p, casas=5):
    return (round(p[0], casas), round(p[1], casas), round(p[2], casas))


def _encadear(segmentos) -> list[list]:
    """Junta os segmentos do corte em aneis FECHADOS.

    O consumo e por SEGMENTO, nao por vertice: onde a secao do corte se toca
    num ponto so (dois pedacos de parede que se encostam), aquele vertice
    tem quatro segmentos, e marcar o vertice como usado fecharia o anel
    errado e deixaria a tampa incompleta.

    Corrente que nao volta ao ponto de partida e descartada em vez de virar
    anel torto: melhor faltar tampa — e o verificador reclamar — do que
    gravar um STL com geometria inventada.
    """

    vizinhos: dict[tuple, list] = {}
    for indice, (a, b) in enumerate(segmentos):
        ka, kb = _chave(a), _chave(b)
        if ka == kb:
            continue
        vizinhos.setdefault(ka, []).append((indice, b))
        vizinhos.setdefault(kb, []).append((indice, a))

    usados: set[int] = set()
    aneis: list[list] = []
    for indice, (a, b) in enumerate(segmentos):
        if indice in usados or _chave(a) == _chave(b):
            continue
        partida = _chave(a)
        anel = [a, b]
        usados.add(indice)
        atual = _chave(b)
        while atual != partida:
            seguinte = None
            for outro, destino in vizinhos.get(atual, []):
                if outro not in usados:
                    seguinte = (outro, destino)
                    break
            if seguinte is None:
                break
            usados.add(seguinte[0])
            anel.append(seguinte[1])
            atual = _chave(seguinte[1])
        if atual == partida and len(anel) >= 4:
            aneis.append(anel[:-1])  # o ultimo ponto repete o primeiro
    return aneis


def _tampar(segmentos, eixo: int, corte: float, para_mais: bool) -> list[Triangulo]:
    """Fecha a secao do corte com triangulos no plano."""

    aneis3d = _encadear(segmentos)
    if not aneis3d:
        return []

    # Plano X=c -> usa (Y, Z); plano Y=c -> usa (X, Z).
    outro = 1 if eixo == 0 else 0
    planos = [[(p[outro], p[2]) for p in anel] for anel in aneis3d]
    faces = montar_faces(planos)

    triangulos: list[Triangulo] = []
    for face in faces:
        for a, b, c in triangular(face):
            def para3d(p):
                if eixo == 0:
                    return (corte, p[0], p[1])
                return (p[0], corte, p[1])

            tri = (para3d(a), para3d(b), para3d(c))
            # A normal da tampa aponta para fora do pedaco.
            precisa_inverter = (eixo == 0) == para_mais
            triangulos.append(tri if precisa_inverter else tri[::-1])
    return triangulos


def _afastar_da_degenerescencia(
    triangulos: list[Triangulo], eixo: int, corte: float, folga: float = 1e-5
) -> float:
    """Empurra o plano para longe de vertices rasantes.

    Plano passando bem em cima de um vertice e o caso ruim do corte: a
    aresta nao gera intersecao limpa e a tampa fica com furo. Meio centesimo
    de milimetro de desvio resolve, sem diferenca nenhuma na peca — e a
    mesma manha que os fatiadores usam para nao fatiar em cima de uma face.
    """

    for desvio in (0.0, 0.01, -0.01, 0.02, -0.02, 0.05, -0.05):
        candidato = corte + desvio
        if not any(
            abs(v[eixo] - candidato) < folga for tri in triangulos for v in tri
        ):
            return candidato
    return corte


def _partir(triangulos: list[Triangulo], eixo: int, corte: float) -> list[list[Triangulo]]:
    """Um corte so, pelo cortador proprio: devolve os pedacos ja tampados."""

    abaixo: list[Triangulo] = []
    acima: list[Triangulo] = []
    segmentos = []
    vistos_segmento: set = set()
    for tri in triangulos:
        parte_baixo, parte_cima, segmento = _fatiar_triangulo(tri, eixo, corte)
        abaixo += parte_baixo
        acima += parte_cima
        if segmento:
            # Aresta que encosta no plano aparece nos dois triangulos
            # vizinhos: guardar duas vezes bagunca o encadeamento.
            chave = tuple(sorted((_chave(segmento[0]), _chave(segmento[1]))))
            if chave not in vistos_segmento:
                vistos_segmento.add(chave)
                segmentos.append(segmento)
    abaixo += _tampar(segmentos, eixo, corte, para_mais=True)
    acima += _tampar(segmentos, eixo, corte, para_mais=False)
    return [
        parte
        for parte in (costurar_juntas_t(abaixo)[0], costurar_juntas_t(acima)[0])
        if parte
    ]


_config_do_corte: list = []


def _sao(pedaco: list[Triangulo]) -> bool:
    """O pedaco saiu fechado e inteiro? Usa o mesmo analisador da curadoria.

    A configuracao fica em cache: esta funcao roda uma vez por candidato de
    plano, e reler o TOML do disco a cada chamada dominava o tempo de corte
    de uma peca grande.
    """

    from ..config import carregar_config
    from ..mesh import analisar_triangulos

    if not pedaco:
        return False
    if not _config_do_corte:
        _config_do_corte.append(carregar_config())
    return analisar_triangulos(pedaco, _config_do_corte[0]).fechada


def cortar(
    triangulos: list[Triangulo],
    eixo: int,
    posicoes: list[float],
    tolerancia_desvio: float = 4.0,
) -> tuple[list[list[Triangulo]], list[str]]:
    """Corta o solido nos planos dados e devolve ``(pedacos, avisos)``.

    Cada corte e CONFERIDO: se um pedaco sair aberto ou nao-manifold, o plano
    anda e tenta de novo, ate ``tolerancia_desvio`` milimetros do lugar
    pedido. Acontece em peca simetrica cortada no eixo de simetria, e onde o
    plano pega uma nesga fina de material no meio de uma contra-forma grande.
    Melhor a emenda alguns milimetros fora do meio do que um STL que o
    fatiador recusa — por isso quem chama passa como tolerancia a folga que
    ainda sobra na mesa.
    """

    avisos: list[str] = []
    if not posicoes:
        return [list(triangulos)], avisos

    pedacos = [list(triangulos)]
    for pedido in sorted(posicoes):
        atual = pedacos.pop()  # so o ultimo pedaco pode conter o proximo corte
        desvios = [0.0]
        passo = 0.3
        while passo <= tolerancia_desvio:
            desvios += [passo, -passo]
            passo *= 1.6
        if tolerancia_desvio > 1.0:  # ultima tentativa: varredura larga
            desvios += [
                d
                for i in range(1, 6)
                for d in (tolerancia_desvio * i / 5.0, -tolerancia_desvio * i / 5.0)
            ]

        def tentar(motor, desvios_) -> tuple[list, float] | None:
            for desvio in desvios_:
                corte = _afastar_da_degenerescencia(atual, eixo, pedido + desvio)
                partes = motor(atual, eixo, corte)
                if partes is None:
                    continue
                partes = [p for p in partes if p]
                if partes and all(_sao(parte) for parte in partes):
                    return partes, corte
            return None

        # O cortador proprio vem primeiro: medindo em letreiro grande ele sai
        # na frente do trimesh e e varias vezes mais rapido. O trimesh entra
        # so onde ele falhou em TODOS os planos — ali, um motor de producao
        # testado por muita gente vale a tentativa extra.
        achado = tentar(_partir, desvios) or tentar(cortar_um_plano, desvios)
        resultado = None
        if achado is not None:
            resultado, corte = achado
            if abs(corte - pedido) > 0.05:
                avisos.append(
                    f"corte movido de {pedido:.1f} para {corte:.1f} mm "
                    "para sair com malha fechada"
                )

        if resultado is None:
            corte = _afastar_da_degenerescencia(atual, eixo, pedido)
            resultado = [p for p in _partir(atual, eixo, corte) if p]
            avisos.append(
                f"corte em {pedido:.1f} mm saiu com malha suspeita — confira o "
                "pedaco no fatiador antes de imprimir"
            )
        pedacos.extend(resultado)
    return pedacos, avisos


def _extensao(triangulos: list[Triangulo], eixo: int) -> tuple[float, float]:
    valores = [v[eixo] for tri in triangulos for v in tri]
    return (min(valores), max(valores)) if valores else (0.0, 0.0)


def cortar_para_caber(
    triangulos: list[Triangulo], mesa_x: float, mesa_y: float
) -> tuple[list[list[Triangulo]], list[str]]:
    """Corta o quanto for preciso, nos dois eixos, ate tudo caber na mesa.

    Letreiro comprido pede corte em X; letra alta (uma "M" de 40 cm) pede
    corte em Y tambem. Cada eixo e resolvido na sua vez, e cada pedaco e
    conferido antes de virar arquivo.
    """

    avisos: list[str] = []

    def folga(comprimento: float, mesa: float) -> float:
        """Quanto o plano pode andar sem estourar a mesa."""

        if comprimento <= mesa:
            return 0.0
        partes = math.ceil(comprimento / mesa)
        return max(1.0, (mesa - comprimento / partes) * 0.45)

    cortou_em = set()

    def cortar_corpo(corpo: list[Triangulo]) -> list[list[Triangulo]]:
        """Corta UM corpo nos dois eixos, na medida que ele precisar."""

        cx0, cx1 = _extensao(corpo, 0)
        cy0, cy1 = _extensao(corpo, 1)
        largura_c, altura_c = cx1 - cx0, cy1 - cy0

        posicoes_x = [
            cx0 + p for p in sugerir_cortes(largura_c, altura_c, mesa_x, mesa_y)
        ]
        if posicoes_x:
            cortou_em.add("largura")
        pedacos, notas = cortar(
            corpo, 0, posicoes_x, tolerancia_desvio=folga(largura_c, mesa_x)
        )
        avisos.extend(notas)

        saida: list[list[Triangulo]] = []
        for pedaco in pedacos:
            py0, py1 = _extensao(pedaco, 1)
            posicoes_y = [
                py0 + p for p in sugerir_cortes(py1 - py0, 0.0, mesa_y, mesa_y)
            ]
            if not posicoes_y:
                saida.append(pedaco)
                continue
            cortou_em.add("altura")
            partes, mais = cortar(
                pedaco, 1, posicoes_y, tolerancia_desvio=folga(py1 - py0, mesa_y)
            )
            avisos.extend(mais)
            saida.extend(partes)
        return saida

    x0, x1 = _extensao(triangulos, 0)
    y0, y1 = _extensao(triangulos, 1)
    largura, altura = x1 - x0, y1 - y0

    if largura <= mesa_x and altura <= mesa_y:
        # Cabe inteiro: sai num arquivo so, com as letras juntas como estao.
        # Separar corpos aqui viraria um STL por letra sem necessidade.
        return [list(triangulos)], avisos

    # Corta a peca inteira, sem separar as letras antes. Separar parecia boa
    # ideia (cada plano cairia dentro de material em vez de cair no vazio
    # entre as letras), mas medindo o resultado piorou: a 800 mm foram 21% de
    # peca aberta contra 0% sem separar, e seis vezes mais lento. Quem ja
    # resolvia o vazio era o descarte de pedaco vazio, no laco de corte.
    corpos = [list(triangulos)]

    finais: list[list[Triangulo]] = []
    for corpo in corpos:
        finais.extend(cortar_corpo(corpo))

    if "largura" in cortou_em:
        avisos.append(
            f"largura de {largura:.0f} mm nao cabe na mesa util de "
            f"{mesa_x:.0f} mm: cortada na vertical"
        )
    if "altura" in cortou_em:
        avisos.append(
            f"altura de {altura:.0f} mm nao cabe na mesa util de "
            f"{mesa_y:.0f} mm: cortada na horizontal"
        )
    if len(finais) > 1:
        avisos.append(
            f"{len(finais)} pecas no total, a partir de {len(corpos)} corpo(s) "
            "separado(s) — cada letra e cortada por conta propria"
        )
    return finais, avisos
