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
    Response, abort,
    Flask, redirect, render_template, request, send_from_directory, session, url_for,
)

from . import analise, auth, criar, custo, dados, formato, listas, orcamento

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


# O menu, como DADO e num lugar so.
#
# Ate o U1 eram dez links escritos a mao numa barra horizontal que nao sabia
# quebrar: em 420 px ela esticava o corpo da pagina para 920 px, e TODA tela
# rolava de lado. Dez nao cabem, e nao iam caber em doze.
#
# Em grupo, e como dado, tres coisas ficam possiveis: a lateral se desenha
# sozinha, o grupo certo abre no que voce esta usando, e ha um teste que abre
# cada rota do menu -- item que aponta para lugar nenhum passaria despercebido
# numa lista escrita a mao.
MENU = (
    ("Operação", "operacao", (
        ("painel", "Painel", "painel"),
        ("producao", "Produção", "producao"),
        ("lista_pedidos", "Pedidos", "pedidos"),
        ("lista_clientes", "Clientes", "clientes"),
    )),
    ("Cadastros", "cadastros", (
        ("lista_produtos", "Produtos", "produtos"),
        ("lista_compras", "Compras", "compras"),
        ("lista_filamentos", "Filamentos", "filamentos"),
        ("lista_insumos", "Insumos", "insumos"),
        ("editar_empresa", "Empresa", "empresa"),
    )),
    ("Personalização", "personalizacao", (
        ("tela_criar", "Personalizar", "personalizar"),
        ("lista_templates", "Templates", "templates"),
    )),
)


def _grupo_de(endpoint: str | None) -> str:
    """Qual grupo abre. Sem isto, quem chega em Filamentos ve tudo fechado."""
    for _, chave, itens in MENU:
        if any(e == endpoint for e, _, _ in itens):
            return chave
    return MENU[0][1]


def _fontes_do_gerador() -> tuple[str, ...]:
    """Le os nomes direto de web/fontes/fontes.js.

    Escrever a lista aqui a mao seria a terceira copia dela -- e a que
    ninguem lembraria de atualizar no dia de trocar uma fonte.
    """
    caminho = os.path.join(RAIZ, "web", "fontes", "fontes.js")
    try:
        with open(caminho, encoding="utf-8") as f:
            for linha in f:
                if "const b64 = {" in linha:
                    dentro = linha.split("{", 1)[1].split("}", 1)[0]
                    return tuple(n.strip() for n in dentro.split(",") if n.strip())
    except OSError:
        pass
    return ("luckiest",)


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

    # Dinheiro e data em portugues, num lugar so. Ha teste que varre os
    # templates atras do padrao antigo -- sem ele a proxima tela nasce com
    # `R$ 1120.00` de novo.
    app.jinja_env.filters.update(formato.FILTROS)

    def _erro(excecao) -> dict:
        """O que a tela precisa para APONTAR o campo, e nao so avisar.

        `ErroDeCampo` sabe de qual campo ele e; um ValueError comum nao sabe,
        e a tela cai no aviso de sempre no topo.
        """
        return {"erro": str(excecao), "campo_erro": getattr(excecao, "campo", "")}

    def url_com(**mudancas):
        """A URL desta tela com um parametro trocado, guardando os outros.

        Ordenar sem perder a busca, e buscar sem perder a aba: sem isto cada
        clique num cabecalho jogaria fora o filtro que a pessoa acabou de por.
        """
        args = {**request.args.to_dict(), **mudancas}
        return url_for(request.endpoint,
                       **{c: v for c, v in args.items() if v not in (None, "")})

    @app.context_processor
    def comuns():
        return {
            "url_com": url_com,
            # Sempre definido: campo com erro so existe depois de um POST que
            # falhou, e comparar com Undefined em vinte lugares e pedir susto.
            "campo_erro": "",
            "com_senha": bool(auth.SENHA),
            "usuario": session.get("usuario", ""),
            "marca_simbolo": arquivo_da_marca("marca-simbolo"),
            "menu": MENU,
            "grupo_aberto": _grupo_de(request.endpoint),
        }

    # ---------------------------------------------------------------- telas
    @app.route("/")
    @auth.exige_login
    def painel():
        # O grafico sai da MESMA conta que a lista de produtos usa. Se o painel
        # fizesse a sua propria, o retorno por hora do painel e o da tela de
        # produtos podiam discordar sem que ninguem soubesse qual valia.
        #
        # So os ATIVOS: produto desativado nao disputa hora de impressora, e
        # deixa-lo no grafico faria a comparacao ser com peca que nao se vende
        # mais. A tela de produtos lista todos, por isso mostra mais linhas.
        retorno = custo.retorno_por_hora(dados.produtos(), dados.parametros())
        return render_template("painel.html", aba="painel", retorno=retorno,
                               modelos=criar.MODELOS, criar_conta=criar.contagem(),
                               **dados.resumo())

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
    @app.route("/filamentos")
    @auth.exige_login
    def lista_filamentos():
        lista = dados.filamentos(False)
        # Ativos apenas: o painel conta o que esta em uso, e rolo desativado
        # nao e dinheiro parado, e dinheiro que ja saiu.
        ativos = [f for f in lista if f["ativo"]]
        return render_template("filamentos.html", aba="filamentos", filamentos=lista,
                               parado=dados.parado_em_filamento(ativos),
                               cores_sem_preco=dados.sem_preco(ativos), cores=dados.CORES)

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
                    "filamento.html", aba="filamentos", cores=dados.CORES, **_erro(erro),
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
                    "insumo.html", aba="insumos", **_erro(erro),
                    atual=dados.campos_insumo(request.form)), 400
            return redirect(url_for("lista_insumos"))
        return render_template("insumo.html", aba="insumos", atual=atual)

    @app.route("/produtos")
    @auth.exige_login
    def lista_produtos():
        param = dados.parametros()
        itens = dados.produtos(False)
        for p in itens:
            # com_preco: quando o produto tem preco digitado, e ele que manda na
            # margem e no retorno por hora. Sem isto a coluna Preco mostrava um
            # numero e a coluna Margem era calculada sobre outro.
            p["conta"] = custo.conta_de_produto(p, param).com_preco(p.get("preco"))
        busca = request.args.get("q", "")
        itens = listas.filtrar(itens, busca, listas.BUSCA_PRODUTOS)
        ordem, invertido = listas.pedido_da_url(request.args, listas.ORDENS_PRODUTOS)
        itens = listas.ordenar(itens, ordem, invertido, listas.ORDENS_PRODUTOS)
        return render_template("produtos.html", aba="produtos", produtos=itens,
                               cores=dados.CORES, ordens=listas.ORDENS_PRODUTOS,
                               ordem=ordem, invertido=invertido, busca=busca)

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
                    "produto.html", aba="produtos", **_erro(erro), param=param,
                    atual=dados.campos_produto(request.form),
                    filamentos=dados.filamentos(), insumos=dados.insumos()), 400
            return redirect(url_for("editar_produto", id_=novo_id))
        conta = custo.conta_de_produto(atual, param) if atual else None
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

    # -------------------------------------------------------------- clientes
    @app.route("/clientes")
    @auth.exige_login
    def lista_clientes():
        return render_template("clientes.html", aba="clientes",
                               clientes=dados.clientes(False))

    @app.route("/clientes/novo", methods=["GET", "POST"])
    @app.route("/clientes/<int:id_>", methods=["GET", "POST"])
    @auth.exige_login
    def editar_cliente(id_=None):
        atual = dados.cliente(id_) if id_ else None
        if id_ and not atual:
            abort(404)
        if request.method == "POST":
            try:
                dados.salvar_cliente(request.form, session.get("usuario", ""), id_)
            except ValueError as erro:
                return render_template("cliente.html", aba="clientes", **_erro(erro),
                                       atual=dados.campos_cliente(request.form),
                                       canais=dados.CANAIS), 400
            return redirect(url_for("lista_clientes"))
        return render_template("cliente.html", aba="clientes", atual=atual,
                               canais=dados.CANAIS)

    # --------------------------------------------------------------- pedidos
    def _itens_do_formulario(form) -> list[dict]:
        """Le as linhas de item. Linha sem descricao nem produto e descartada."""
        catalogo = {p["id"]: p for p in dados.produtos(False)}
        itens = []
        for i, produto_id in enumerate(form.getlist("item_produto")):
            descricao = (form.getlist("item_descricao")[i] or "").strip()
            prod = catalogo.get(int(produto_id)) if produto_id else None
            if not descricao and not prod:
                continue
            qtd = dados._numero(form.getlist("item_qtd")[i], 1) or 1
            itens.append({
                "produto_id": prod["id"] if prod else None,
                "descricao": descricao or (prod["nome"] if prod else ""),
                "cor": (form.getlist("item_cor")[i] or "").strip(),
                "quantidade": qtd,
                "valor_unit": dados._numero(form.getlist("item_valor")[i]),
                # Peso e tempo sao POR PECA no catalogo; a fila precisa do
                # total, senao seis chaveiros ocupam a mesa de um.
                "gramas": (prod["gramas"] or 0) * qtd if prod else None,
                "horas": (prod["horas"] or 0) * qtd if prod else None,
            })
        return itens

    @app.route("/pedidos")
    @auth.exige_login
    def lista_pedidos():
        # "entregues" e o mes CORRENTE, e nao tudo que ja foi entregue: e para
        # onde o numero "entregue em <mes>" do painel aponta, e o rodape desta
        # tela tem que fechar com ele.
        ver = request.args.get("ver", "abertos")
        if ver == "entregues":
            lista = dados.entregues_no_mes()
        else:
            lista = dados.pedidos(dados.SITUACOES if ver == "todos" else dados.ABERTOS)
        busca = request.args.get("q", "")
        lista = listas.filtrar(lista, busca, listas.BUSCA_PEDIDOS)
        ordem, invertido = listas.pedido_da_url(request.args, listas.ORDENS_PEDIDOS)
        lista = listas.ordenar(lista, ordem, invertido, listas.ORDENS_PEDIDOS)
        return render_template("pedidos.html", aba="pedidos", ver=ver, pedidos=lista,
                               total=dados.somar_valor(lista), mes=formato.mes_por_extenso(),
                               ordens=listas.ORDENS_PEDIDOS, ordem=ordem,
                               invertido=invertido, busca=busca)

    @app.route("/pedidos/novo", methods=["GET", "POST"])
    @app.route("/pedidos/<int:id_>", methods=["GET", "POST"])
    @auth.exige_login
    def editar_pedido(id_=None):
        atual = dados.pedido(id_) if id_ else None
        if id_ and not atual:
            abort(404)
        contexto = dict(aba="pedidos", clientes=dados.clientes(), canais=dados.canais(),
                        produtos=dados.produtos(), cores=dados.CORES)
        if request.method == "POST":
            itens = _itens_do_formulario(request.form)
            try:
                novo_id = dados.salvar_pedido(request.form, session.get("usuario", ""),
                                              id_, itens)
            except ValueError as erro:
                return render_template("pedido.html", **_erro(erro),
                                       atual=dict(request.form, itens=itens, id=id_),
                                       **contexto), 400
            return redirect(url_for("editar_pedido", id_=novo_id))
        return render_template("pedido.html", atual=atual, **contexto)

    @app.route("/pedidos/<int:id_>/situacao", methods=["POST"])
    @auth.exige_login
    def mudar_situacao_pedido(id_):
        if not dados.pedido(id_):
            abort(404)
        try:
            dados.mudar_situacao(id_, request.form.get("situacao", ""),
                                 session.get("usuario", ""))
        except ValueError:
            abort(400)
        return redirect(url_for("editar_pedido", id_=id_))

    # ------------------------------------------------------------- orcamento
    def _link_do_aceite(token: str) -> str:
        """O endereço que vai no PDF e no WhatsApp.

        `_external=True` porque quem abre é o cliente, num aparelho que não
        tem ideia de qual é o servidor — um caminho relativo no papel não
        leva a lugar nenhum.
        """
        return url_for("ver_orcamento", token=token, _external=True)

    @app.route("/pedidos/<int:id_>/orcamento.pdf")
    @auth.exige_login
    def pdf_do_orcamento(id_):
        alvo = dados.pedido(id_)
        if not alvo:
            abort(404)
        # Gerar o PDF cria o link, se ainda não houver: o papel e o endereço
        # nascem juntos, senão o cliente recebe um PDF que manda abrir uma
        # página que não existe.
        link = dados.token_do_orcamento(id_)
        alvo["token_expira"] = link["expira"]
        try:
            pdf = orcamento.desenhar(alvo, dados.empresa(), _link_do_aceite(link["token"]))
        except ImportError:
            # O venv da VPS pode estar atrás do requirements.txt.
            abort(503, "O gerador de PDF não está instalado neste servidor.")
        return Response(pdf, mimetype="application/pdf", headers={
            # `inline`: no telefone ele abre na hora, em vez de baixar e
            # sumir na pasta de downloads.
            "Content-Disposition":
                f'inline; filename="{orcamento.nome_do_arquivo(alvo)}"',
        })

    @app.route("/pedidos/<int:id_>/link", methods=["POST"])
    @auth.exige_login
    def renovar_link(id_):
        if not dados.pedido(id_):
            abort(404)
        dados.token_do_orcamento(id_)
        return redirect(url_for("editar_pedido", id_=id_))

    # A ÚNICA rota do sistema sem login. Quem entra é o cliente, com um
    # endereço de 32 caracteres sorteado que só ele recebeu.
    @app.route("/orcamento/<token>")
    def ver_orcamento(token):
        alvo = dados.pedido_por_token(token)
        if not alvo:
            # Não diz se o link nunca existiu ou se venceu: para quem está
            # tentando adivinhar, as duas respostas juntas são uma pista.
            return render_template("orcamento_vencido.html"), 404
        return render_template("orcamento.html", pedido=alvo, token=token,
                               conteudo=orcamento.linhas(alvo, dados.empresa()),
                               empresa=dados.empresa())

    @app.route("/orcamento/<token>/aceitar", methods=["POST"])
    def aceitar_orcamento(token):
        alvo = dados.aceitar_orcamento(token, request.form.get("nome", ""))
        if not alvo:
            return render_template("orcamento_vencido.html"), 404
        return redirect(url_for("ver_orcamento", token=token))

    @app.route("/empresa", methods=["GET", "POST"])
    @auth.exige_login
    def editar_empresa():
        if request.method == "POST":
            try:
                dados.salvar_empresa(request.form, session.get("usuario", ""))
            except ValueError as erro:
                return render_template("empresa.html", aba="pedidos", **_erro(erro),
                                       atual=dados.campos_empresa(request.form)), 400
            return redirect(url_for("editar_empresa"))
        return render_template("empresa.html", aba="pedidos", atual=dados.empresa())

    @app.route("/canais", methods=["GET", "POST"])
    @auth.exige_login
    def editar_canais():
        if request.method == "POST":
            for canal in dados.canais(False):
                enviado = request.form.get(f"comissao_{canal['nome']}")
                if enviado is not None:
                    dados.salvar_comissao(canal["nome"], dados._numero(enviado))
            return redirect(url_for("editar_canais"))
        return render_template("canais.html", aba="pedidos", canais=dados.canais(False))

    # -------------------------------------------------------------- producao
    @app.route("/producao")
    @auth.exige_login
    def producao():
        return render_template("producao.html", aba="producao", **dados.quadro())

    @app.route("/producao/mover", methods=["POST"])
    @auth.exige_login
    def mover_pecas():
        """Uma peca do quadro ou varias da lista -- a mesma rota.

        Devolve JSON para o arrastar, e redireciona para o formulario da
        lista. A tela e uma so; o jeito de mexer nela e que muda.
        """
        para = request.form.get("para", "")
        ids = [int(i) for i in request.form.getlist("peca") if str(i).isdigit()]
        autor = session.get("usuario", "")
        erros = []
        for peca_id in ids:
            try:
                dados.mover_peca(peca_id, para, autor)
            except ValueError as erro:
                erros.append(str(erro))
        if request.form.get("json"):
            return ({"ok": not erros, "erros": erros, "movidas": len(ids) - len(erros)},
                    200 if not erros else 400)
        return redirect(url_for("producao"))

    @app.route("/producao/refugo", methods=["POST"])
    @auth.exige_login
    def refugar_peca():
        try:
            dados.registrar_refugo(int(request.form["peca"]),
                                   session.get("usuario", ""),
                                   request.form.get("motivo", "").strip())
        except (ValueError, KeyError):
            abort(400)
        return redirect(url_for("producao"))

    @app.route("/producao/<int:peca_id>/historico")
    @auth.exige_login
    def historico_peca(peca_id):
        return {"historico": dados.historico_da_peca(peca_id)}, 200

    # --------------------------------------------------------------- compras
    def _itens_da_compra(form) -> list[dict]:
        itens = []
        for i, alvo in enumerate(form.getlist("item_alvo")):
            if not alvo or ":" not in alvo:
                continue
            tipo, _, alvo_id = alvo.partition(":")
            qtd = dados._numero(form.getlist("item_qtd")[i])
            if qtd <= 0:
                continue
            itens.append({"tipo": tipo, "alvo_id": int(alvo_id), "quantidade": qtd,
                          "valor": dados._numero(form.getlist("item_valor")[i])})
        return itens

    @app.route("/compras")
    @auth.exige_login
    def lista_compras():
        return render_template("compras.html", aba="compras", compras=dados.compras())

    @app.route("/compras/nova", methods=["GET", "POST"])
    @app.route("/compras/<int:id_>", methods=["GET", "POST"])
    @auth.exige_login
    def editar_compra(id_=None):
        atual = dados.compra(id_) if id_ else None
        if id_ and not atual:
            abort(404)
        contexto = dict(aba="compras", filamentos=dados.filamentos(),
                        insumos=dados.insumos(), cores=dados.CORES)
        if request.method == "POST":
            itens = _itens_da_compra(request.form)
            try:
                novo_id = dados.salvar_compra(request.form, session.get("usuario", ""),
                                              id_, itens)
            except ValueError as erro:
                return render_template("compra.html", **_erro(erro),
                                       atual=dict(request.form, itens=itens, id=id_),
                                       **contexto), 400
            return redirect(url_for("editar_compra", id_=novo_id))
        return render_template("compra.html", atual=atual, hoje=dados.agora()[:10],
                               **contexto)

    @app.route("/compras/<int:id_>/apagar", methods=["POST"])
    @auth.exige_login
    def apagar_compra_rota(id_):
        if not dados.compra(id_):
            abort(404)
        dados.apagar_compra(id_)
        return redirect(url_for("lista_compras"))

    # As cinco que o gerador carrega. Vem do modulo de fontes, e nao de uma
    # lista escrita a mao: fonte que a tela oferece e o gerador nao tem produz
    # um template que nunca desenha.
    FONTES_DO_GERADOR = _fontes_do_gerador()

    # ------------------------------------------------------------------ criar
    @app.route("/criar")
    @auth.exige_login
    def tela_criar():
        return render_template("criar.html", aba="personalizar", modelos=criar.MODELOS,
                               categorias=criar.categorias(), cores=criar.cores_possiveis(),
                               conta=criar.contagem(), no_ar=criar.NO_AR,
                               em_obra=criar.EM_OBRA)

    # ------------------------------------------------------------ ferramentas
    # As pastas que os geradores carregam por caminho RELATIVO. Sao servidas sob
    # cada gerador porque e assim que o navegador as pede a partir de
    # /letreiros/ ou /topo/ -- e e o mesmo caminho que funciona quando a
    # ferramenta abre a pagina como file://.
    PARTILHADAS = ("nucleo", "fontes", "libs")

    # A barra no fim nao e enfeite: desde o C1 a pagina carrega o nucleo por
    # caminho RELATIVO, e sem ela "nucleo/nucleo.js" cairia na raiz do site.
    # Flask redireciona /letreiros para ca sozinho, entao link antigo continua
    # valendo.
    @app.route("/letreiros/")
    @auth.exige_login
    def letreiros():
        return send_from_directory(os.path.join(RAIZ, "web"), "gerador-letreiros.html")

    # UMA tela para todas as pecas de template. Ate o C3 era /topo/, com a
    # pagina inteira dedicada ao topo de bolo; o chaveiro teria copiado as 400
    # linhas dela. Agora quem muda e o registro em web/nucleo/pecas.js.
    @app.route("/criar/<peca>/")
    @auth.exige_login
    def gerador(peca):
        if peca not in dados.tipos_de_peca():
            abort(404)
        return send_from_directory(os.path.join(RAIZ, "web"), "gerador.html")

    @app.route("/topo/")
    @auth.exige_login
    def topo_de_bolo():
        """O endereco antigo, para link salvo no navegador nao virar 404."""
        return redirect(url_for("gerador", peca="topo"))

    @app.route("/letreiros/<any(nucleo, fontes, libs):pasta>/<path:arquivo>")
    @app.route("/criar/<peca>/<any(nucleo, fontes, libs):pasta>/<path:arquivo>")
    @auth.exige_login
    def partilhado(pasta, arquivo, peca=None):
        return send_from_directory(os.path.join(RAIZ, "web", pasta), arquivo)

    # ------------------------------------------------------------- templates
    @app.route("/templates")
    @auth.exige_login
    def lista_templates():
        busca = request.args.get("q", "")
        # 200 e nao 15: a busca so serve se ela alcancar o historico. O rodape
        # da tabela diz quantas sobraram, para o numero na tela nunca ser um
        # recorte silencioso.
        registros = listas.filtrar(dados.geracoes(limite=200), busca, listas.BUSCA_GERACOES)
        ordem, invertido = listas.pedido_da_url(request.args, listas.ORDENS_GERACOES)
        registros = listas.ordenar(registros, ordem, invertido, listas.ORDENS_GERACOES)
        return render_template("templates.html", aba="templates",
                               templates=dados.templates(so_ativos=False),
                               geracoes=registros, ordens=listas.ORDENS_GERACOES,
                               ordem=ordem, invertido=invertido, busca=busca)

    @app.route("/templates/novo", methods=["GET", "POST"])
    @app.route("/templates/<sku>", methods=["GET", "POST"])
    @auth.exige_login
    def editar_template(sku=None):
        atual = dados.template(sku) if sku else None
        if sku and not atual:
            abort(404)
        contexto = dict(aba="templates", formas=dados.FORMAS, fontes=FONTES_DO_GERADOR,
                        campos=dados.CAMPOS_TEMPLATE)
        if request.method == "POST":
            try:
                novo = dados.salvar_template(request.form, session.get("usuario", ""), sku)
            except ValueError as erro:
                # Tipado, e nao o request.form cru: no formulario cru tudo e
                # texto e campo nao preenchido nem existe, entao o template
                # pedia `round()` de coisa nenhuma e a tela de ERRO quebrava.
                # Mesma razao do campos_filamento, e mesmo remedio.
                campos = dados.campos_template(request.form)
                campos["campos"] = [c for c in campos["campos"].split(",") if c]
                return render_template("template.html", **_erro(erro),
                                       atual=campos, geracoes=[], **contexto), 400
            return redirect(url_for("editar_template", sku=novo))
        return render_template("template.html", atual=atual,
                               geracoes=dados.geracoes(limite=20, sku=sku) if sku else [],
                               **contexto)

    @app.route("/templates/<sku>/publicar", methods=["POST"])
    @auth.exige_login
    def publicar_template_rota(sku):
        if not dados.template(sku):
            abort(404)
        try:
            dados.publicar_template(sku, request.form.get("publicar") == "1",
                                    session.get("usuario", ""))
        except ValueError as erro:
            return render_template("template.html", **_erro(erro), aba="templates",
                                   atual=dados.template(sku), formas=dados.FORMAS,
                                   fontes=FONTES_DO_GERADOR, campos=dados.CAMPOS_TEMPLATE,
                                   geracoes=dados.geracoes(limite=20, sku=sku)), 400
        return redirect(url_for("editar_template", sku=sku))

    @app.route("/templates/<sku>/apagar", methods=["POST"])
    @auth.exige_login
    def apagar_template_rota(sku):
        if not dados.template(sku):
            abort(404)
        dados.apagar_template(sku)
        return redirect(url_for("lista_templates"))

    # Esta rota NAO exige login, e e de proposito: e a porta que a vitrine da
    # sprint 8 vai usar. Sem sessao ela entrega so o que esta PUBLICADO --
    # §10, "separar templates em teste dos publicados". Quem decide e a rota,
    # e nao a tela que chama.
    @app.route("/criar/<peca>/templates")
    def templates_da_peca(peca):
        de_dentro = auth.autenticado()
        tipo = request.args.get("tipo", peca)
        lista = dados.templates(so_publicados=not de_dentro, tipo=tipo)
        return {"templates": lista, "painel": de_dentro}

    @app.route("/criar/<peca>/geracao", methods=["POST"])
    @auth.exige_login
    def registrar_geracao_rota(peca):
        try:
            id_ = dados.registrar_geracao(request.get_json(silent=True) or request.form,
                                          session.get("usuario", ""))
        except ValueError as erro:
            return {"erro": str(erro)}, 400
        return {"id": id_}, 201

    @app.route("/criar/<peca>/marca")
    @auth.exige_login
    def marca_no_nome(peca):
        """§18: termo de marca no nome do CLIENTE, e nao so no template.

        A exposicao maior nao e o template que voce escolhe: e o cliente
        digitando "Homem Aranha" no campo de nome de uma peca que VOCE vende.
        A curadoria ja sabia detectar isso; aqui os dois se encontram.
        """
        from morumbi3d import brands
        achados = brands.detectar(request.args.get("nome", ""))
        return {"termos": [{"termo": t, "categoria": c} for t, c in achados]}

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
