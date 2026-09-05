#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
====================================================================
 GERADOR DE LOGO 3D  -  Morumbi 3D
====================================================================
Converte uma imagem (JPG ou PNG) em arquivo(s) STL prontos para
impressao 3D, seguindo a mesma logica do gerador de letreiro:

  - Pipeline automatizado (uma imagem entra, STLs saem)
  - Variantes de peca (unica / base+relevo / multicor)
  - Checagem de robustez mecanica ANTES de imprimir
  - Relatorio de producao com alturas de troca de filamento

USO BASICO
----------
  python3 gerar_logo_3d.py logo.png

  python3 gerar_logo_3d.py logo.png --largura 150 --cores 3

  python3 gerar_logo_3d.py logo.jpg --modo silhueta --sem-placa

PRINCIPAIS PARAMETROS
---------------------
  --largura N        Largura final da peca em mm (padrao 150)
  --altura-base N    Espessura da placa de fundo em mm (padrao 3.0)
  --altura-relevo N  Altura do logo acima da placa em mm (padrao 2.0)
  --cores N          Quantas cores separar (1 = silhueta, padrao 1)
  --modo             silhueta | cores
  --sem-placa        Nao gera placa de fundo (pecas soltas)
  --borda N          Margem da placa ao redor do logo em mm (padrao 4.0)
  --largura-minima N Largura minima de traco aceita em mm (padrao 1.2)
  --engordar         Dilata o logo para salvar tracos finos
"""

import argparse
import os
import sys

import numpy as np
import cv2
from PIL import Image

from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity

import trimesh


# ====================================================================
# 1. CARREGAMENTO E LIMPEZA DA IMAGEM
# ====================================================================

def carregar_imagem(caminho, resolucao_max=1400, resolucao_min=1100):
    """Carrega a imagem e retorna (rgb, alpha ou None)."""
    if not os.path.exists(caminho):
        sys.exit(f"ERRO: arquivo nao encontrado -> {caminho}")

    img = Image.open(caminho)

    # Reduz se for gigante (acelera muito o processamento)
    if max(img.size) > resolucao_max:
        fator = resolucao_max / max(img.size)
        novo = (int(img.size[0] * fator), int(img.size[1] * fator))
        img = img.resize(novo, Image.LANCZOS)
        print(f"   Imagem reduzida para {novo[0]}x{novo[1]} px")

    # Amplia se for pequena. Logo de 500px tem texto secundario com
    # traco de 2 a 3 pixels: a limpeza morfologica come esse traco
    # antes de virar geometria. Ampliar preserva o detalhe fino.
    elif max(img.size) < resolucao_min:
        fator = resolucao_min / max(img.size)
        novo = (int(img.size[0] * fator), int(img.size[1] * fator))
        img = img.resize(novo, Image.LANCZOS)
        print(f"   Imagem ampliada para {novo[0]}x{novo[1]} px "
              f"(preserva traco fino)")

    alpha = None
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
        alpha = np.array(img.split()[-1])
        # Compoe sobre branco para nao sujar as cores
        fundo = Image.new("RGB", img.size, (255, 255, 255))
        fundo.paste(img, mask=img.split()[-1])
        rgb = np.array(fundo)
        if alpha.min() > 250:      # PNG sem transparencia real
            alpha = None
    else:
        rgb = np.array(img.convert("RGB"))

    return rgb, alpha


def mascara_do_objeto(rgb, alpha, tolerancia=32):
    """
    Separa o logo do fundo.
    Prioridade: canal alpha > cor dos cantos > limiar automatico.
    """
    if alpha is not None:
        print("   Fundo detectado pelo canal alpha (PNG transparente)")
        return (alpha > 128).astype(np.uint8) * 255

    h, w = rgb.shape[:2]
    # Amostra os 4 cantos para descobrir a cor de fundo
    amostra = 8
    cantos = np.concatenate([
        rgb[0:amostra, 0:amostra].reshape(-1, 3),
        rgb[0:amostra, w - amostra:w].reshape(-1, 3),
        rgb[h - amostra:h, 0:amostra].reshape(-1, 3),
        rgb[h - amostra:h, w - amostra:w].reshape(-1, 3),
    ])
    cor_fundo = np.median(cantos, axis=0)
    desvio = np.abs(rgb.astype(np.int16) - cor_fundo).sum(axis=2)
    mask = (desvio > tolerancia).astype(np.uint8) * 255

    ocupacao = (mask > 0).mean()
    if ocupacao < 0.005 or ocupacao > 0.97:
        print("   Cantos inconclusivos -> usando limiar Otsu")
        cinza = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        _, mask = cv2.threshold(cinza, 0, 255,
                                cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    else:
        print(f"   Fundo detectado por cor dos cantos RGB{tuple(cor_fundo.astype(int))}")

    return mask


def mascara_por_cor(rgb, cor_hex, tolerancia=40):
    """
    Isola o logo pela COR dele, em vez de subtrair o fundo.
    Muito mais robusto quando o fundo e escuro, texturizado ou
    tem a mesma cor de partes do desenho (ex: logo vazado).
    Distancia calculada em LAB (perceptual), nao em RGB.
    """
    cor_hex = cor_hex.lstrip("#")
    alvo = np.array([int(cor_hex[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.uint8)

    lab_img = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    lab_alvo = cv2.cvtColor(alvo.reshape(1, 1, 3),
                            cv2.COLOR_RGB2LAB).astype(np.float32).reshape(3)

    dist = np.sqrt(((lab_img - lab_alvo) ** 2).sum(axis=2))
    mask = (dist < tolerancia).astype(np.uint8) * 255
    print(f"   Isolado pela cor #{cor_hex.upper()} "
          f"(tolerancia {tolerancia}): {100.0 * (mask > 0).mean():.1f}% da imagem")
    return mask


def profundidade_contornos(hierarquia):
    """Calcula a profundidade de aninhamento de cada contorno."""
    profundidades = []
    for i in range(len(hierarquia)):
        d, pai = 0, hierarquia[i][3]
        while pai != -1:
            d += 1
            pai = hierarquia[pai][3]
        profundidades.append(d)
    return profundidades


def preencher_mascara(mask, modo):
    """
    Converte desenho de CONTORNO em forma SOLIDA.

    modo 'tudo'     : preenche todo buraco fechado.
                      Bom para logo sem contraforma (sem miolo de A, O, R).

    modo 'contorno' : regra de paridade pelo aninhamento. Em arte de
                      contorno cada traco gera 2 niveis de profundidade,
                      entao o solido fica nos niveis 4k e o vazado nos
                      niveis 4k+3. Assim o miolo do 'A' continua vazado
                      e o corpo da letra fica cheio.
    """
    if modo == "nenhum":
        return mask

    contornos, hier = cv2.findContours((mask > 0).astype(np.uint8),
                                       cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if hier is None or not contornos:
        return mask
    hier = hier[0]
    prof = profundidade_contornos(hier)

    saida = np.zeros_like(mask)
    # Ordem crescente de profundidade: o mais fundo sobrescreve o mais raso
    ordem = sorted(range(len(contornos)), key=lambda i: prof[i])

    if modo == "tudo":
        for i in ordem:
            if prof[i] == 0:
                cv2.drawContours(saida, [contornos[i]], -1, 255, -1)
    else:
        for i in ordem:
            if prof[i] % 4 == 0:
                cv2.drawContours(saida, [contornos[i]], -1, 255, -1)
            elif prof[i] % 4 == 3:
                cv2.drawContours(saida, [contornos[i]], -1, 0, -1)

    ganho = (saida > 0).mean() / max((mask > 0).mean(), 1e-9)
    print(f"   Contorno preenchido (modo {modo}): "
          f"area multiplicada por {ganho:.1f}x")
    return saida


def limpar_mascara(mask, abertura=1, fechamento=2, area_minima_pct=0.002):
    """Remove ruido, fecha buracos minusculos e descarta sujeira solta."""
    if abertura > 0:
        # Abertura de raio 1 por iteracao, em vez de um nucleo grande
        # de uma vez: limpa o mesmo ruido sem devorar traco de 2px.
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=int(abertura))
    if fechamento > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (fechamento * 2 + 1,) * 2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)

    # Remove componentes minusculos (poeira, artefato de JPG).
    # O limite e relativo a AREA DO DESENHO, nao a area da imagem:
    # num logo pequeno dentro de uma tela grande, medir pela imagem
    # classifica letra de verdade como sujeira.
    n, labels, stats, _ = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8), 8)
    area_desenho = max(int((mask > 0).sum()), 1)
    area_min = max(6.0, area_desenho * area_minima_pct)
    saida = np.zeros_like(mask)
    removidos = 0
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= area_min:
            saida[labels == i] = 255
        else:
            removidos += 1
    if removidos:
        print(f"   {removidos} fragmento(s) de ruido descartado(s)")
    return saida


# ====================================================================
# 2. SEPARACAO DE CORES
# ====================================================================

def separar_cores(rgb, mask_objeto, n_cores):
    """
    Quantiza o logo em N cores usando k-means no espaco LAB
    (agrupamento mais proximo da percepcao humana que RGB).
    Retorna lista de (mascara, cor_hex, percentual).
    """
    if n_cores <= 1:
        return [(mask_objeto, None, 100.0)]

    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    pixels = lab[mask_objeto > 0].astype(np.float32)

    if len(pixels) < n_cores:
        sys.exit("ERRO: imagem com area util pequena demais para separar cores.")

    criterio = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.5)
    _, rotulos, centros = cv2.kmeans(pixels, n_cores, None, criterio,
                                     8, cv2.KMEANS_PP_CENTERS)
    rotulos = rotulos.flatten()

    # Converte centros LAB de volta para RGB (para nomear as pecas)
    centros_rgb = cv2.cvtColor(centros.reshape(-1, 1, 3).astype(np.uint8),
                               cv2.COLOR_LAB2RGB).reshape(-1, 3)

    mapa = np.full(mask_objeto.shape, -1, dtype=np.int16)
    mapa[mask_objeto > 0] = rotulos

    camadas = []
    total = len(rotulos)
    for i in range(n_cores):
        m = ((mapa == i).astype(np.uint8)) * 255
        pct = 100.0 * (rotulos == i).sum() / total
        r, g, b = centros_rgb[i]
        camadas.append((m, f"#{r:02X}{g:02X}{b:02X}", pct))

    # Cor mais usada primeiro (vira a peca principal)
    camadas.sort(key=lambda c: -c[2])
    return camadas


# ====================================================================
# 3. VETORIZACAO: MASCARA -> POLIGONOS
# ====================================================================

def mascara_para_poligonos(mask, escala_mm, simplificacao=0.15):
    """
    Converte uma mascara binaria em geometria shapely em milimetros,
    preservando buracos internos (o miolo do 'O', por exemplo).
    """
    contornos, hierarquia = cv2.findContours((mask > 0).astype(np.uint8),
                                             cv2.RETR_CCOMP,
                                             cv2.CHAIN_APPROX_SIMPLE)
    if not contornos:
        return None

    altura_px = mask.shape[0]
    hierarquia = hierarquia[0]

    def para_mm(c):
        pts = c.reshape(-1, 2).astype(np.float64)
        # Inverte Y: imagem cresce para baixo, o mundo 3D cresce para cima
        return np.column_stack([pts[:, 0] * escala_mm,
                                (altura_px - pts[:, 1]) * escala_mm])

    poligonos = []
    for i, c in enumerate(contornos):
        if hierarquia[i][3] != -1:      # e um buraco, tratado pelo pai
            continue
        if len(c) < 3:
            continue

        casca = para_mm(c)
        buracos = []
        filho = hierarquia[i][2]
        while filho != -1:
            if len(contornos[filho]) >= 3:
                buracos.append(para_mm(contornos[filho]))
            filho = hierarquia[filho][0]

        try:
            p = Polygon(casca, buracos)
            if not p.is_valid:
                p = p.buffer(0)
            if p.is_empty:
                continue
            if simplificacao > 0:
                p = p.simplify(simplificacao, preserve_topology=True)
            if p.is_valid and p.area > 0.05:
                poligonos.append(p)
        except Exception:
            continue

    if not poligonos:
        return None

    geo = unary_union(poligonos)
    return geo if not geo.is_empty else None


def como_lista(geo):
    """Normaliza Polygon / MultiPolygon em lista de Polygon."""
    if geo is None or geo.is_empty:
        return []
    if isinstance(geo, Polygon):
        return [geo]
    if isinstance(geo, MultiPolygon):
        return [g for g in geo.geoms if isinstance(g, Polygon) and not g.is_empty]
    return [g for g in getattr(geo, "geoms", []) if isinstance(g, Polygon)]


# ====================================================================
# 4. CHECAGEM DE ROBUSTEZ MECANICA
# ====================================================================

def auditar_geometria(geo, largura_minima, nome="logo"):
    """
    Licao aprendida no letreiro: geometria valida no papel pode ser
    fragil na bancada. Aqui checamos tracos finos e pecas soltas
    ANTES de gastar filamento.
    """
    partes = como_lista(geo)
    alertas = []

    print(f"\n   AUDITORIA DE ROBUSTEZ ({nome})")
    print(f"      Corpos independentes : {len(partes)}")

    # Erosao pela metade da largura minima: o que sumir e fino demais
    raio = largura_minima / 2.0
    erodido = geo.buffer(-raio)
    if erodido.is_empty:
        alertas.append(f"TODO o desenho tem traco abaixo de {largura_minima}mm "
                       f"- aumente o tamanho da peca ou use --engordar")
        print("      Area em tracos finos : 100.0%")
    else:
        perdida = geo.area - erodido.buffer(raio).area
        pct = 100.0 * perdida / geo.area if geo.area else 0
        print(f"      Area em tracos finos : {pct:.1f}%")
        if pct > 12:
            alertas.append(f"{pct:.0f}% da area total tem traco fino "
                           f"(< {largura_minima}mm) - considere --engordar")

    # Checagem POR CORPO: um detalhe pequeno e fragil e um risco real
    # mesmo representando pouca area do conjunto.
    fragis = 0
    for p in partes:
        sobra = p.buffer(-raio)
        restante = 0.0 if sobra.is_empty else sobra.buffer(raio).area / p.area
        if restante < 0.6:
            fragis += 1
    if fragis:
        alertas.append(f"{fragis} corpo(s) sao predominantemente finos "
                       f"e podem quebrar ao soltar da mesa")

    if len(partes) > 1:
        areas = sorted((p.area for p in partes), reverse=True)
        if areas[-1] < 25:
            alertas.append(f"Existem pecas soltas muito pequenas "
                           f"(menor = {areas[-1]:.1f} mm2) - use a placa de fundo")

    for a in alertas:
        print(f"      [!] {a}")
    if not alertas:
        print("      [OK] Geometria aprovada para impressao")

    return alertas


# ====================================================================
# 5. EXTRUSAO E EXPORTACAO
# ====================================================================

def extrudar(geo, altura, z_base=0.0):
    """Transforma geometria 2D em malha 3D solida."""
    malhas = []
    for p in como_lista(geo):
        if p.area < 0.01:
            continue
        try:
            m = trimesh.creation.extrude_polygon(p, height=altura, engine="earcut")
        except Exception:
            try:
                m = trimesh.creation.extrude_polygon(p.buffer(0), height=altura)
            except Exception:
                continue

        # Costura cada corpo separadamente, ANTES de juntar. Juntar
        # vertices depois grudaria corpos que so se encostam, criando
        # aresta com 4 faces e abrindo a malha.
        m.merge_vertices()
        m.fix_normals()

        # Furo que encosta na casca (miolo de R, B, A que a
        # simplificacao colou na borda) forma um estrangulamento que
        # o triangulador nao fecha. Micro-abertura de 0.01mm separa o
        # ponto sem mudar nada visivel na peca.
        if not m.is_watertight:
            try:
                reparado = p.buffer(0.01).buffer(-0.01)
                alt = trimesh.creation.extrude_polygon(
                    reparado, height=altura, engine="earcut")
                alt.merge_vertices()
                alt.fix_normals()
                if alt.is_watertight:
                    m = alt
            except Exception:
                pass

        if z_base:
            m.apply_translation([0, 0, z_base])
        malhas.append(m)

    if not malhas:
        return None
    if len(malhas) == 1:
        return malhas[0]

    # concatenate sem tratamento posterior: cada corpo ja esta fechado
    # e devem permanecer independentes.
    malha = trimesh.util.concatenate(malhas)

    if not malha.is_watertight:
        print("      [!] malha aberta - o fatiador pode pedir reparo")

    return malha


def criar_placa(geo_total, borda, altura, formato="contorno", raio_canto=3.0):
    """
    Placa de fundo que segura todas as partes soltas do logo.
    formato: contorno (segue o desenho) | retangulo
    """
    if formato == "retangulo":
        minx, miny, maxx, maxy = geo_total.bounds
        from shapely.geometry import box
        placa = box(minx - borda, miny - borda, maxx + borda, maxy + borda)
        if raio_canto > 0:
            placa = placa.buffer(-raio_canto).buffer(raio_canto * 2).buffer(-raio_canto)
    else:
        # Dilata, funde e suaviza: contorno organico que acompanha o logo
        placa = geo_total.buffer(borda, join_style=1, resolution=16)
        placa = placa.buffer(-borda * 0.25).buffer(borda * 0.25)
        placa = unary_union(placa)
        # Fecha buracos internos da placa (fundo tem que ser solido)
        placa = unary_union([Polygon(p.exterior) for p in como_lista(placa)])

    return extrudar(placa, altura, z_base=0.0)


# ====================================================================
# 6. PIPELINE PRINCIPAL
# ====================================================================

def gerar(args):
    nome = os.path.splitext(os.path.basename(args.imagem))[0].upper()
    nome = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in nome)
    saida = args.saida or os.path.join(os.getcwd(), f"{nome}_3D")
    os.makedirs(saida, exist_ok=True)

    print("=" * 62)
    print(f" GERADOR DE LOGO 3D  -  {nome}")
    print("=" * 62)

    # --- 1. Imagem -------------------------------------------------
    print("\n[1] Lendo imagem")
    rgb, alpha = carregar_imagem(args.imagem)
    print(f"   Resolucao de trabalho: {rgb.shape[1]}x{rgb.shape[0]} px")

    # --- 2. Recorte do fundo ---------------------------------------
    print("\n[2] Separando logo do fundo")
    if args.cor_alvo:
        mask = mascara_por_cor(rgb, args.cor_alvo, args.tolerancia_cor)
    else:
        mask = mascara_do_objeto(rgb, alpha, args.tolerancia_fundo)

    # Limpeza ANTES de preencher: tira poeira/estrela que viraria buraco falso
    mask = limpar_mascara(mask, args.suavizar, args.fechar_vaos,
                          area_minima_pct=args.ruido_minimo)

    if args.preencher != "nenhum":
        mask = preencher_mascara(mask, args.preencher)
    if (mask > 0).sum() == 0:
        sys.exit("ERRO: nada foi detectado. Tente --tolerancia-fundo menor "
                 "ou use um PNG com fundo transparente.")
    print(f"   Area util: {100.0 * (mask > 0).mean():.1f}% da imagem")

    # --- 3. Escala mm/px -------------------------------------------
    xs, ys = np.where(mask > 0)[1], np.where(mask > 0)[0]
    larg_px = xs.max() - xs.min() + 1
    alt_px = ys.max() - ys.min() + 1
    if args.altura_mm:
        escala = args.altura_mm / alt_px
    else:
        escala = args.largura / larg_px
    print(f"   Escala: {escala:.4f} mm/px  ->  "
          f"{larg_px * escala:.1f} x {alt_px * escala:.1f} mm")

    # --- 4. Camadas de cor -----------------------------------------
    print(f"\n[3] Separando cores (modo: {args.modo})")
    n_cores = 1 if args.modo == "silhueta" else max(1, args.cores)
    camadas = separar_cores(rgb, mask, n_cores)
    for i, (_, hexcor, pct) in enumerate(camadas, 1):
        etiqueta = hexcor or "peca unica"
        print(f"   Camada {i}: {etiqueta}  ({pct:.1f}% da area)")

    # --- 5. Vetorizacao --------------------------------------------
    print("\n[4] Vetorizando contornos")
    geos = []
    for i, (m, hexcor, pct) in enumerate(camadas, 1):
        if args.engordar > 0:
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            passos = max(1, int(round(args.engordar / escala / 2)))
            m = cv2.dilate(m, k, iterations=passos)
        g = mascara_para_poligonos(m, escala, args.simplificar)
        if g is None:
            print(f"   Camada {i}: vazia apos limpeza, ignorada")
            continue
        # Folga: pequena sobreposicao evita fresta entre cores vizinhas
        if n_cores > 1 and args.folga > 0:
            g = g.buffer(args.folga, join_style=1)
        geos.append((g, hexcor, pct))
        print(f"   Camada {i}: {len(como_lista(g))} corpo(s), "
              f"{g.area:.0f} mm2")

    if not geos:
        sys.exit("ERRO: nenhuma geometria valida gerada.")

    # --- 6. Centraliza no plano ------------------------------------
    total = unary_union([g for g, _, _ in geos])
    minx, miny, maxx, maxy = total.bounds
    dx, dy = -(minx + maxx) / 2, -(miny + maxy) / 2
    geos = [(affinity.translate(g, dx, dy), c, p) for g, c, p in geos]
    total = affinity.translate(total, dx, dy)

    # --- 7. Auditoria ----------------------------------------------
    alertas = auditar_geometria(total, args.largura_minima, nome)

    # --- 8. Malhas 3D ----------------------------------------------
    print("\n[5] Gerando malhas 3D")
    arquivos = []
    usa_placa = not args.sem_placa

    z_logo = args.altura_base if usa_placa else 0.0

    if usa_placa:
        placa = criar_placa(total, args.borda, args.altura_base,
                            args.formato_placa, args.raio_canto)
        if placa is not None:
            cam = os.path.join(saida, f"{nome}_01_placa.stl")
            placa.export(cam)
            arquivos.append((cam, "Placa de fundo", args.altura_base, None))
            print(f"   Placa: {placa.volume / 1000:.1f} cm3")

    for i, (g, hexcor, pct) in enumerate(geos, 1):
        malha = extrudar(g, args.altura_relevo, z_base=z_logo)
        if malha is None:
            continue
        sufixo = hexcor.replace("#", "") if hexcor else "logo"
        cam = os.path.join(saida, f"{nome}_{i + 1:02d}_{sufixo}.stl")
        malha.export(cam)
        arquivos.append((cam, hexcor or "Logo", args.altura_relevo, hexcor))
        print(f"   Camada {i} ({hexcor or 'unica'}): "
              f"{malha.volume / 1000:.1f} cm3, "
              f"{'fechada' if malha.is_watertight else 'ATENCAO: aberta'}")

    # --- 9. Preview ------------------------------------------------
    salvar_preview(rgb, geos, saida, nome)

    # --- 10. Relatorio ---------------------------------------------
    escrever_relatorio(saida, nome, args, arquivos, geos, total,
                       z_logo, alertas)

    print("\n" + "=" * 62)
    print(f" PRONTO -> {saida}")
    print("=" * 62)
    return saida


def salvar_preview(rgb, geos, saida, nome):
    """Preview PNG das camadas separadas, para conferir antes de fatiar."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Polygon as MplPoly

        fig, ax = plt.subplots(figsize=(7, 7))
        for g, hexcor, _ in geos:
            cor = hexcor if hexcor else "#333333"
            for p in como_lista(g):
                ax.add_patch(MplPoly(np.array(p.exterior.coords),
                                     closed=True, facecolor=cor,
                                     edgecolor="#000000", linewidth=0.4))
                for h in p.interiors:
                    ax.add_patch(MplPoly(np.array(h.coords), closed=True,
                                         facecolor="white",
                                         edgecolor="#000000", linewidth=0.4))
        ax.autoscale_view()
        ax.set_aspect("equal")
        ax.set_xlabel("mm")
        ax.set_ylabel("mm")
        ax.set_title(f"{nome} - preview das camadas")
        ax.grid(alpha=0.25, linestyle=":")
        cam = os.path.join(saida, f"{nome}_preview.png")
        fig.savefig(cam, dpi=130, bbox_inches="tight")
        plt.close(fig)
        print(f"   Preview salvo: {os.path.basename(cam)}")
    except Exception as e:
        print(f"   (preview nao gerado: {e})")


def escrever_relatorio(saida, nome, args, arquivos, geos, total, z_logo, alertas):
    minx, miny, maxx, maxy = total.bounds
    altura_total = z_logo + args.altura_relevo

    linhas = []
    linhas.append("=" * 60)
    linhas.append(f" RELATORIO DE PRODUCAO - {nome}")
    linhas.append("=" * 60)
    linhas.append("")
    linhas.append("DIMENSOES FINAIS")
    linhas.append(f"  Largura .......... {maxx - minx:.1f} mm")
    linhas.append(f"  Altura ........... {maxy - miny:.1f} mm")
    linhas.append(f"  Espessura total .. {altura_total:.1f} mm")
    linhas.append("")
    linhas.append("PECAS GERADAS")
    for cam, desc, alt, hexcor in arquivos:
        linhas.append(f"  - {os.path.basename(cam)}")
        linhas.append(f"      descricao: {desc}   altura: {alt:.1f} mm")
    linhas.append("")
    linhas.append("CONFIGURACAO NO FATIADOR")
    linhas.append("  1. Importe TODOS os STL de uma vez e responda SIM para")
    linhas.append("     'carregar como objeto unico' - eles ja estao alinhados.")
    if not args.sem_placa:
        linhas.append(f"  2. Troca de filamento na altura Z = {args.altura_base:.1f} mm")
        linhas.append("     (fim da placa, inicio do logo em relevo)")
    linhas.append("  3. Camadas solidas no topo: 5 a 6 "
                  "(evita textura do preenchimento aparecer)")
    linhas.append("  4. Preenchimento: 15% a 20% - a peca e decorativa")
    linhas.append("  5. Altura de camada: 0.2 mm")
    linhas.append("  6. Sem suporte: a peca e plana, imprime deitada")
    linhas.append("")
    if alertas:
        linhas.append("ALERTAS DE ROBUSTEZ")
        for a in alertas:
            linhas.append(f"  [!] {a}")
    else:
        linhas.append("ROBUSTEZ: aprovado, nenhum alerta.")
    linhas.append("")
    linhas.append("PARAMETROS USADOS")
    linhas.append(f"  modo={args.modo}  cores={args.cores}  "
                  f"largura={args.largura}mm")
    linhas.append(f"  altura_base={args.altura_base}  "
                  f"altura_relevo={args.altura_relevo}  borda={args.borda}")
    linhas.append(f"  largura_minima={args.largura_minima}  "
                  f"simplificar={args.simplificar}  engordar={args.engordar}")
    linhas.append(f"  cor_alvo={args.cor_alvo}  preencher={args.preencher}")

    cam = os.path.join(saida, f"{nome}_RELATORIO.txt")
    with open(cam, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))
    print(f"   Relatorio salvo: {os.path.basename(cam)}")


# ====================================================================
# 7. LINHA DE COMANDO
# ====================================================================

def main():
    p = argparse.ArgumentParser(
        description="Gerador de Logo 3D - Morumbi 3D",
        formatter_class=argparse.RawDescriptionHelpFormatter)

    p.add_argument("imagem", help="arquivo JPG ou PNG de entrada")
    p.add_argument("--saida", default=None, help="pasta de saida")

    # Tamanho
    p.add_argument("--largura", type=float, default=150.0,
                   help="largura final em mm (padrao 150)")
    p.add_argument("--altura-mm", type=float, default=None,
                   help="define pela altura em vez da largura")

    # Espessuras
    p.add_argument("--altura-base", type=float, default=3.0,
                   help="espessura da placa de fundo em mm")
    p.add_argument("--altura-relevo", type=float, default=2.0,
                   help="altura do logo acima da placa em mm")

    # Cores
    p.add_argument("--modo", choices=["silhueta", "cores"], default="silhueta")
    p.add_argument("--cores", type=int, default=1,
                   help="numero de cores a separar (modo cores)")
    p.add_argument("--folga", type=float, default=0.08,
                   help="sobreposicao entre cores em mm")

    # Placa
    p.add_argument("--sem-placa", action="store_true",
                   help="nao gerar placa de fundo")
    p.add_argument("--borda", type=float, default=4.0,
                   help="margem da placa ao redor do logo em mm")
    p.add_argument("--formato-placa", choices=["contorno", "retangulo"],
                   default="contorno")
    p.add_argument("--raio-canto", type=float, default=3.0,
                   help="arredondamento do canto da placa retangular")

    # Qualidade / robustez
    p.add_argument("--simplificar", type=float, default=0.15,
                   help="tolerancia de simplificacao em mm")
    p.add_argument("--largura-minima", type=float, default=1.2,
                   help="largura minima de traco aceita em mm")
    p.add_argument("--engordar", type=float, default=0.0,
                   help="dilata o desenho em mm para salvar tracos finos")
    p.add_argument("--suavizar", type=int, default=1,
                   help="intensidade da limpeza de ruido (0 a 5)")
    p.add_argument("--fechar-vaos", type=int, default=2,
                   help="fecha vaos internos do desenho (0 a 12). Suba para "
                        "unir facetas separadas por linha fina")
    p.add_argument("--tolerancia-fundo", type=int, default=32,
                   help="sensibilidade da deteccao de fundo")
    p.add_argument("--ruido-minimo", type=float, default=0.002,
                   help="area minima de um fragmento, fracao da area do desenho")

    # Logos vazados / fundo dificil
    p.add_argument("--cor-alvo", default=None,
                   help="isola o logo por cor, ex: --cor-alvo '#FFE81F'")
    p.add_argument("--tolerancia-cor", type=float, default=40.0,
                   help="tolerancia da cor-alvo em LAB (padrao 40)")
    p.add_argument("--preencher", choices=["nenhum", "tudo", "contorno"],
                   default="nenhum",
                   help="converte desenho de contorno em forma solida")

    args = p.parse_args()
    if args.modo == "cores" and args.cores < 2:
        args.cores = 2
    gerar(args)


if __name__ == "__main__":
    main()
