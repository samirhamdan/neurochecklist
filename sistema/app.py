"""Sistema de gestao da Morumbi 3D — porta de entrada.

Esta entrega tem duas telas: a de entrada e o painel. O painel le do banco e
mostra o estado real da operacao; enquanto nao houver pedido cadastrado, ele
diz isso com todas as letras em vez de fingir movimento.

Rodar local:
    MORUMBI_DADOS=./dados python3 -m sistema.app

Em producao quem sobe e o gunicorn, pelo servico do systemd.
"""

from __future__ import annotations

import os

from flask import (
    abort,
    Flask, redirect, render_template, request, send_from_directory, session, url_for,
)

from . import analise, auth, custo, dados

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# O logotipo entra como arquivo em sistema/static/, gerado por
# ferramentas/preparar_marca.py a partir de marca/morumbi3d-original.png.
#
# Enquanto o arquivo nao estiver la, as telas mostram so o nome escrito,
# em vez do icone de imagem quebrada que <img> exibe para arquivo
# inexistente. Confere a cada pagina, e nao na subida: assim basta soltar
# o arquivo na pasta, sem depender de reiniciar o servico.
FORMATOS = (".svg", ".webp", ".png")
ESTATICOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


def arquivo_da_marca(base: str) -> str:
    for ext in FORMATOS:
        if os.path.exists(os.path.join(ESTATICOS, base + ext)):
            return base + ext
    return ""


def criar_app() -> Flask:
    auth.verificar_configuracao()

    app = Flask(__name__)
    app.secret_key = auth.chave_de_sessao()
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        # O Caddy termina o HTTPS e conversa com o app em HTTP puro, entao
        # request.is_secure e falso aqui dentro. Quem sabe se o visitante veio
        # por HTTPS e o cabecalho que o Caddy manda.
        SESSION_COOKIE_SECURE=os.environ.get("MORUMBI_HTTPS", "1") == "1",
        MAX_CONTENT_LENGTH=25 * 1024 * 1024,
    )

    @app.context_processor
    def comuns():
        return {
            "com_senha": bool(auth.SENHA),
            "usuario": session.get("usuario", ""),
            "marca_simbolo": arquivo_da_marca("marca-simbolo"),
        }

    # ---------------------------------------------------------------- telas
    @app.route("/")
    @auth.exige_login
    def painel():
        return render_template("painel.html", aba="painel", **dados.resumo())

    @app.route("/entrar", methods=["GET", "POST"])
    def entrar():
        if auth.autenticado():
            return redirect(url_for("painel"))

        destino = request.values.get("destino") or url_for("painel")
        # Destino so pode ser caminho interno: "//outro.site" e um jeito
        # classico de usar a tela de login para levar embora quem entrou.
        if not destino.startswith("/") or destino.startswith("//"):
            destino = url_for("painel")

        if request.method == "GET":
            return render_template("entrar.html", destino=destino)

        ip = auth.endereco_do_pedido()
        if auth.bloqueado(ip):
            return render_template(
                "entrar.html", destino=destino, bloqueado=True,
                erro=f"Tentativas demais. Espere {auth.JANELA_MINUTOS} minutos "
                     "e tente de novo.",
            ), 429

        usuario = request.form.get("usuario", "")
        senha = request.form.get("senha", "")
        if auth.confere(usuario, senha):
            session.clear()
            session["usuario"] = auth.USUARIO
            session.permanent = False
            auth.limpar_tentativas(ip)
            return redirect(destino)

        restam = auth.registrar_erro(ip)
        # Mensagem unica de proposito: dizer "usuario nao existe" entregaria
        # quais nomes existem para quem esta tentando adivinhar.
        return render_template(
            "entrar.html", destino=destino,
            erro="Usuário ou senha não conferem."
                 + (f" Restam {restam} tentativas." if restam <= 2 else ""),
        ), 401

    @app.route("/sair", methods=["POST"])
    def sair():
        session.clear()
        return redirect(url_for("entrar"))

    # ------------------------------------------------------------- cadastros
    def _conta_do_produto(prod: dict, param: dict) -> custo.Conta:
        insumos = sum(v["quantidade"] * v["valor_unit"] for v in prod.get("insumos", []))
        return custo.calcular(prod.get("gramas") or 0, prod.get("horas") or 0,
                              prod.get("filamento_preco_kg"), insumos,
                              prod.get("minutos"), param=param)

    @app.route("/filamentos")
    @auth.exige_login
    def lista_filamentos():
        return render_template("filamentos.html", aba="filamentos",
                               filamentos=dados.filamentos(False), cores=dados.CORES)

    @app.route("/filamentos/novo", methods=["GET", "POST"])
    @app.route("/filamentos/<int:id_>", methods=["GET", "POST"])
    @auth.exige_login
    def editar_filamento(id_=None):
        atual = dados.filamento(id_) if id_ else None
        if id_ and not atual:
            abort(404)
        if request.method == "POST":
            try:
                dados.salvar_filamento(request.form, session.get("usuario", ""), id_)
            except ValueError as erro:
                return render_template(
                    "filamento.html", aba="filamentos", cores=dados.CORES, erro=str(erro),
                    atual=dados.campos_filamento(request.form)), 400
            return redirect(url_for("lista_filamentos"))
        return render_template("filamento.html", aba="filamentos", atual=atual,
                               cores=dados.CORES)

    @app.route("/insumos")
    @auth.exige_login
    def lista_insumos():
        return render_template("insumos.html", aba="insumos", insumos=dados.insumos(False))

    @app.route("/insumos/novo", methods=["GET", "POST"])
    @app.route("/insumos/<int:id_>", methods=["GET", "POST"])
    @auth.exige_login
    def editar_insumo(id_=None):
        atual = dados.insumo(id_) if id_ else None
        if id_ and not atual:
            abort(404)
        if request.method == "POST":
            try:
                dados.salvar_insumo(request.form, session.get("usuario", ""), id_)
            except ValueError as erro:
                return render_template(
                    "insumo.html", aba="insumos", erro=str(erro),
                    atual=dados.campos_insumo(request.form)), 400
            return redirect(url_for("lista_insumos"))
        return render_template("insumo.html", aba="insumos", atual=atual)

    @app.route("/produtos")
    @auth.exige_login
    def lista_produtos():
        param = dados.parametros()
        itens = dados.produtos(False)
        for p in itens:
            p["conta"] = custo.calcular(p.get("gramas") or 0, p.get("horas") or 0,
                                        p.get("filamento_preco_kg"),
                                        minutos=p.get("minutos"), param=param)
        return render_template("produtos.html", aba="produtos", produtos=itens,
                               cores=dados.CORES)

    @app.route("/produtos/novo", methods=["GET", "POST"])
    @app.route("/produtos/<int:id_>", methods=["GET", "POST"])
    @auth.exige_login
    def editar_produto(id_=None):
        atual = dados.produto(id_) if id_ else None
        if id_ and not atual:
            abort(404)
        param = dados.parametros()
        if request.method == "POST":
            vinculos = [(int(i), dados._numero(request.form.get(f"insumo_{i}")))
                        for i in request.form.getlist("insumo_id")]
            try:
                novo_id = dados.salvar_produto(request.form, session.get("usuario", ""),
                                               id_, vinculos)
            except ValueError as erro:
                return render_template(
                    "produto.html", aba="produtos", erro=str(erro), param=param,
                    atual=dados.campos_produto(request.form),
                    filamentos=dados.filamentos(), insumos=dados.insumos()), 400
            return redirect(url_for("editar_produto", id_=novo_id))
        conta = _conta_do_produto(atual, param) if atual else None
        return render_template("produto.html", aba="produtos", atual=atual, conta=conta,
                               param=param, filamentos=dados.filamentos(),
                               insumos=dados.insumos())

    @app.route("/produtos/medir", methods=["POST"])
    @auth.exige_login
    def medir_arquivo():
        """Le o STL e devolve peso, tempo e caixa para o formulario preencher.

        E o passo que tira o chute do cadastro: o peso vem do arquivo que vai
        ser impresso, e nao da lembranca de quanto pesou da ultima vez.
        """
        enviado = request.files.get("modelo")
        if not enviado or not enviado.filename:
            return {"erro": "Nenhum arquivo enviado."}, 400
        try:
            caminho = analise.guardar(enviado, dados.PASTA)
            medida = analise.medir(caminho)
        except analise.ArquivoRecusado as erro:
            return {"erro": str(erro)}, 400
        param = dados.parametros()
        preco_kg = None
        if request.form.get("filamento_id"):
            fil = dados.filamento(int(request.form["filamento_id"]))
            preco_kg = fil["preco_kg"] if fil else None
        minutos = request.form.get("minutos")
        conta = custo.calcular(medida["gramas"], medida["horas"], preco_kg,
                               minutos=float(minutos) if minutos else None, param=param)
        return {"medida": medida, "conta": conta.como_dict()}, 200

    # ------------------------------------------------------------ ferramentas
    @app.route("/letreiros")
    @auth.exige_login
    def letreiros():
        return send_from_directory(os.path.join(RAIZ, "web"), "gerador-letreiros.html")

    @app.route("/saude")
    def saude():
        """Sem senha de proposito: e o que o atualizar.sh consulta no deploy."""
        return {"ok": True}, 200

    return app


app = criar_app() if os.environ.get("MORUMBI_SEM_APP") != "1" else None


if __name__ == "__main__":
    bind = os.environ.get("MORUMBI_BIND", "127.0.0.1:5000")
    host, _, porta = bind.rpartition(":")
    app.run(host=host or "127.0.0.1", port=int(porta or 5000), debug=False)
