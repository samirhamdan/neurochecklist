#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
====================================================================
 GERADOR DE LOGO 3D  -  Servidor local
====================================================================
Interface web para o gerar_logo_3d.py. Roda na sua maquina, nada
sobe para a internet.

COMO USAR
---------
  pip install flask trimesh shapely mapbox_earcut opencv-python pillow numpy matplotlib
  python3 app.py

  Depois abra:  http://localhost:5000

ESTRUTURA ESPERADA
------------------
  morumbi3d_web/
      app.py
      gerar_logo_3d.py      <- o gerador (mesma pasta)
      static/index.html
"""

import base64
import functools
import hmac
import io
import json
import os
import shutil
import sys
import tempfile
import time
import traceback
import uuid
from contextlib import redirect_stdout
from types import SimpleNamespace

import cv2
import numpy as np
from PIL import Image
from flask import Flask, jsonify, request, send_file, send_from_directory

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gerar_logo_3d as G


app = Flask(__name__, static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024   # 25 MB

PASTA = os.environ.get("MORUMBI_DADOS",
                       os.path.join(tempfile.gettempdir(), "morumbi3d"))
os.makedirs(PASTA, exist_ok=True)

# Senha. Sem ela o app recusa subir fora do modo local.
USUARIO = os.environ.get("MORUMBI_USUARIO", "")
SENHA = os.environ.get("MORUMBI_SENHA", "")

# Quanto tempo um upload sobrevive antes da faxina (horas)
VALIDADE_H = float(os.environ.get("MORUMBI_VALIDADE_H", "12"))

# O estado vive em DISCO, nao em memoria. Com varios workers do
# gunicorn, cache em memoria faz o upload cair num processo e a
# previa noutro, que entao nao acha a sessao. Reler do disco custa
# uns 60ms e elimina a classe inteira de bug -- alem do vazamento
# de memoria, que num VPS pequeno derruba o servico em pouco tempo.


def e_sessao(nome):
    """Id de sessao tem forma fixa: 12 digitos hexadecimais."""
    return bool(nome) and len(nome) == 12 and all(c in "0123456789abcdef" for c in nome)


def caminho_sessao(sid):
    """Valida o id e devolve a pasta. Barra travessia de diretorio."""
    if not e_sessao(sid):
        return None
    destino = os.path.join(PASTA, sid)
    return destino if os.path.isdir(destino) else None


def ler_sessao(sid):
    destino = caminho_sessao(sid)
    if not destino:
        return None
    ficha = os.path.join(destino, "ficha.json")
    if not os.path.exists(ficha):
        return None
    with open(ficha, encoding="utf-8") as f:
        dados = json.load(f)
    if not os.path.exists(dados["caminho"]):
        return None
    dados["pasta"] = destino
    return dados


def faxina():
    """Apaga uploads velhos. Sem isso o disco do VPS enche sozinho.

    So apaga pasta com NOME DE SESSAO. Apagar qualquer pasta era seguro
    enquanto este app era dono sozinho do MORUMBI_DADOS; depois da juncao
    ele divide a pasta com o painel, e faxina cega levaria junto o que nao
    e dela. O banco e a chave de sessao sao arquivos e ja escapavam, mas
    depender disso e frageil demais para uma rotina que apaga em silencio.
    """
    limite = time.time() - VALIDADE_H * 3600
    try:
        for nome in os.listdir(PASTA):
            if not e_sessao(nome):
                continue
            alvo = os.path.join(PASTA, nome)
            if os.path.isdir(alvo) and os.path.getmtime(alvo) < limite:
                shutil.rmtree(alvo, ignore_errors=True)
    except Exception:
        pass


def exige_senha(rota):
    """Basic auth. Ligada sempre que MORUMBI_SENHA estiver definida."""
    @functools.wraps(rota)
    def envelope(*a, **kw):
        if not SENHA:
            return rota(*a, **kw)
        cred = request.authorization
        ok = (cred and cred.username and cred.password
              and hmac.compare_digest(cred.username, USUARIO)
              and hmac.compare_digest(cred.password, SENHA))
        if not ok:
            return ("Acesso restrito.", 401,
                    {"WWW-Authenticate": 'Basic realm="Morumbi 3D"'})
        return rota(*a, **kw)
    return envelope

COR_MASCARA = np.array([226, 58, 69], dtype=np.float32)   # rubilith


# ====================================================================
# Utilidades
# ====================================================================

def png_base64(array_rgb):
    buf = io.BytesIO()
    Image.fromarray(array_rgb).save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def ler_parametros(dados):
    """Converte o JSON da interface no formato que o gerador espera."""
    def f(chave, padrao):
        v = dados.get(chave, padrao)
        return padrao if v in (None, "") else float(v)

    def i(chave, padrao):
        return int(f(chave, padrao))

    cor = dados.get("cor_alvo") or None
    if cor and not str(cor).startswith("#"):
        cor = "#" + str(cor)

    return SimpleNamespace(
        imagem=None,
        saida=None,
        largura=f("largura", 150),
        altura_mm=None,
        altura_base=f("altura_base", 3.0),
        altura_relevo=f("altura_relevo", 2.0),
        modo=dados.get("modo", "silhueta"),
        cores=i("cores", 1),
        folga=f("folga", 0.08),
        sem_placa=bool(dados.get("sem_placa", False)),
        borda=f("borda", 4.0),
        formato_placa=dados.get("formato_placa", "contorno"),
        raio_canto=f("raio_canto", 3.0),
        simplificar=f("simplificar", 0.15),
        largura_minima=f("largura_minima", 1.2),
        engordar=f("engordar", 0.0),
        suavizar=i("suavizar", 1),
        fechar_vaos=i("fechar_vaos", 2),
        tolerancia_fundo=i("tolerancia_fundo", 32),
        ruido_minimo=f("ruido_minimo", 0.002),
        cor_alvo=cor,
        tolerancia_cor=f("tolerancia_cor", 40.0),
        preencher=dados.get("preencher", "nenhum"),
    )


def construir_mascara(rgb, alpha, a):
    """Etapas 2 e 3 do gerador, isoladas para a previa."""
    if a.cor_alvo:
        mask = G.mascara_por_cor(rgb, a.cor_alvo, a.tolerancia_cor)
    else:
        mask = G.mascara_do_objeto(rgb, alpha, a.tolerancia_fundo)

    mask = G.limpar_mascara(mask, a.suavizar, a.fechar_vaos,
                            area_minima_pct=a.ruido_minimo)

    if a.preencher != "nenhum":
        mask = G.preencher_mascara(mask, a.preencher)

    return mask


def pintar_sobreposicao(rgb, mask):
    """Imagem original com a mascara em rubilith, mais o contorno marcado."""
    saida = rgb.astype(np.float32).copy()
    sel = mask > 0
    saida[sel] = saida[sel] * 0.35 + COR_MASCARA * 0.65

    contornos, _ = cv2.findContours((mask > 0).astype(np.uint8),
                                    cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    saida = saida.astype(np.uint8)
    espessura = max(1, int(round(max(rgb.shape[:2]) / 500)))
    cv2.drawContours(saida, contornos, -1, (255, 214, 218), espessura)
    return saida


# ====================================================================
# Rotas
# ====================================================================

@app.route("/")
@exige_senha
def inicio():
    return send_from_directory("static", "index.html")


@app.route("/api/enviar", methods=["POST"])
@exige_senha
def enviar():
    faxina()
    arquivo = request.files.get("imagem")
    if not arquivo or not arquivo.filename:
        return jsonify(erro="Nenhuma imagem recebida."), 400

    ext = os.path.splitext(arquivo.filename)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
        return jsonify(erro=f"Formato {ext} nao suportado. "
                            f"Use PNG ou JPG."), 400

    sid = uuid.uuid4().hex[:12]
    destino = os.path.join(PASTA, sid)
    os.makedirs(destino, exist_ok=True)

    # Preserva o nome original: e dele que saem os nomes dos STL
    base = os.path.splitext(os.path.basename(arquivo.filename))[0]
    base = "".join(c if c.isalnum() or c in "-_" else "_" for c in base) or "logo"
    caminho = os.path.join(destino, base + ext)
    arquivo.save(caminho)

    try:
        with redirect_stdout(io.StringIO()):
            rgb, alpha = G.carregar_imagem(caminho)
    except Exception as e:
        return jsonify(erro=f"Nao foi possivel ler a imagem: {e}"), 400

    with open(os.path.join(destino, "ficha.json"), "w", encoding="utf-8") as f:
        json.dump({"caminho": caminho, "nome": arquivo.filename}, f)

    return jsonify(
        id=sid,
        nome=arquivo.filename,
        largura_px=int(rgb.shape[1]),
        altura_px=int(rgb.shape[0]),
        transparencia=alpha is not None,
        imagem=png_base64(rgb),
    )


@app.route("/api/previa", methods=["POST"])
@exige_senha
def previa():
    dados = request.get_json(force=True)
    sessao = ler_sessao(dados.get("id"))
    if not sessao:
        return jsonify(erro="Imagem expirou. Envie o arquivo de novo."), 404

    a = ler_parametros(dados)
    registro = io.StringIO()
    with redirect_stdout(io.StringIO()):
        rgb, alpha = G.carregar_imagem(sessao["caminho"])

    try:
        with redirect_stdout(registro):
            mask = construir_mascara(rgb, alpha, a)

            if (mask > 0).sum() == 0:
                return jsonify(
                    vazio=True,
                    imagem=png_base64(rgb),
                    log=registro.getvalue(),
                    alertas=["Nada foi detectado. Baixe a tolerancia, "
                             "troque a cor-alvo ou desligue o preenchimento."],
                )

            ys, xs = np.where(mask > 0)
            larg_px = xs.max() - xs.min() + 1
            alt_px = ys.max() - ys.min() + 1
            escala = a.largura / larg_px

            trabalho = mask.copy()
            if a.engordar > 0:
                k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
                passos = max(1, int(round(a.engordar / escala / 2)))
                trabalho = cv2.dilate(trabalho, k, iterations=passos)

            geo = G.mascara_para_poligonos(trabalho, escala, a.simplificar)
            if geo is None:
                return jsonify(vazio=True, imagem=png_base64(rgb),
                               log=registro.getvalue(),
                               alertas=["Contorno vetorizado ficou vazio."])

            alertas = G.auditar_geometria(geo, a.largura_minima, "previa")
            corpos = len(G.como_lista(geo))
            sobreposto = pintar_sobreposicao(rgb, trabalho)

        altura_total = (0 if a.sem_placa else a.altura_base) + a.altura_relevo

        return jsonify(
            vazio=False,
            imagem=png_base64(sobreposto),
            mascara=png_base64(np.dstack([trabalho] * 3)),
            largura_mm=round(larg_px * escala, 1),
            altura_mm=round(alt_px * escala, 1),
            espessura_mm=round(altura_total, 1),
            area_mm2=round(geo.area, 0),
            corpos=corpos,
            alertas=alertas,
            log=registro.getvalue(),
        )

    except Exception:
        return jsonify(erro="Falha ao calcular a previa.",
                       log=registro.getvalue() + "\n" + traceback.format_exc()), 500


@app.route("/api/gerar", methods=["POST"])
@exige_senha
def gerar():
    dados = request.get_json(force=True)
    sessao = ler_sessao(dados.get("id"))
    if not sessao:
        return jsonify(erro="Imagem expirou. Envie o arquivo de novo."), 404

    a = ler_parametros(dados)
    a.imagem = sessao["caminho"]

    base = os.path.splitext(os.path.basename(sessao["nome"]))[0].upper()
    base = "".join(c if c.isalnum() or c in "-_" else "_" for c in base) or "LOGO"

    destino = os.path.join(sessao["pasta"], "stl")
    shutil.rmtree(destino, ignore_errors=True)
    a.saida = destino

    registro = io.StringIO()
    try:
        with redirect_stdout(registro):
            G.gerar(a)
    except SystemExit as e:
        return jsonify(erro=str(e), log=registro.getvalue()), 400
    except Exception:
        return jsonify(erro="A geracao falhou.",
                       log=registro.getvalue() + "\n" + traceback.format_exc()), 500

    zip_base = os.path.join(sessao["pasta"], base + "_STL")
    caminho_zip = shutil.make_archive(zip_base, "zip", destino)

    arquivos = sorted(os.listdir(destino))
    tamanho = os.path.getsize(caminho_zip) / 1024.0

    return jsonify(
        ok=True,
        arquivos=arquivos,
        pacote=os.path.basename(caminho_zip),
        tamanho_kb=round(tamanho, 1),
        log=registro.getvalue(),
    )


@app.route("/api/baixar/<sid>")
@exige_senha
def baixar(sid):
    sessao = ler_sessao(sid)
    if not sessao:
        return "Sessao expirada.", 404
    zips = [f for f in os.listdir(sessao["pasta"]) if f.endswith(".zip")]
    if not zips:
        return "Nada gerado ainda.", 404
    return send_file(os.path.join(sessao["pasta"], zips[0]), as_attachment=True)


if __name__ == "__main__":
    endereco = os.environ.get("MORUMBI_HOST", "127.0.0.1")
    porta = int(os.environ.get("MORUMBI_PORTA", "5000"))
    print("=" * 58)
    print(" Gerador de Logo 3D  -  Morumbi 3D")
    print(f" Abra no navegador:  http://localhost:{porta}")
    print(f" Senha: {'ligada' if SENHA else 'DESLIGADA (so use assim na sua maquina)'}")
    print(" Para parar: Ctrl+C")
    print("=" * 58)
    app.run(host=endereco, port=porta, debug=False)
