# -*- coding: utf-8 -*-
"""O que so o navegador prova: a tela escondeu mesmo o que disse que escondeu.

Este arquivo nasceu de um bug que passou por 341 testes e por uma conferencia
minha no proprio navegador. A tela Criar marcava `hidden` nos cartoes certos,
e eu conferi com `.modelo:not([hidden])` -- que le o ATRIBUTO. Estava certo, e
na tela os oito cartoes continuavam la: `.modelo{display:flex}` ganha do
`[hidden]{display:none}` que vem do navegador.

O mesmo `display` de classe quebrava, ha um sprint inteiro, o botao
Quadro/Lista da producao: clicar em "Lista" nunca escondia o quadro.

Entao a regra deste arquivo: **nunca pergunte pelo atributo**. Pergunte se o
elemento tem caixa na tela (`offsetParent`), que e o que a pessoa ve.

Sem playwright ou sem o Chromium instalado, os testes sao PULADOS -- a suite
continua util para quem so tem o painel.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import threading
import time
import unittest

CHROMIUM = os.environ.get("MORUMBI_CHROMIUM", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")


def _navegador_disponivel() -> bool:
    try:
        import playwright.sync_api  # noqa: F401
    except Exception:
        return False
    return bool(shutil.which(CHROMIUM) or os.path.exists(CHROMIUM))


TEM_NAVEGADOR = _navegador_disponivel()
SEM_NAVEGADOR = "playwright ou Chromium nao instalados"
def _token_de_teste() -> str:
    return TOKEN


def _porta_livre() -> int:
    """Porta que o sistema operacional garante estar livre.

    Numero fixo colide com uma segunda rodada da suite -- e o erro que sai e
    "connection refused", que parece bug da tela e nao do teste.
    """
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


PORTA = 0
SITE = ""
TOKEN = ""
_navegador = None
_pw = None


def setUpModule():
    """Servidor E navegador uma vez para o arquivo todo.

    Abrir um Chromium por teste custava 30 s cada -- doze testes viravam seis
    minutos, e teste que demora assim para de ser rodado.
    """
    if not TEM_NAVEGADOR:
        return
    global PORTA, SITE, _navegador, _pw
    PORTA = _porta_livre()
    SITE = f"http://127.0.0.1:{PORTA}"
    os.environ.update(MORUMBI_DADOS=tempfile.mkdtemp(prefix="morumbi-nav-"),
                      MORUMBI_USUARIO="samir", MORUMBI_SENHA="segredo",
                      MORUMBI_BIND=f"127.0.0.1:{PORTA}", MORUMBI_HTTPS="0")
    import importlib

    from sistema import auth, dados
    importlib.reload(dados)
    importlib.reload(auth)
    from sistema import app as modulo
    importlib.reload(modulo)

    fil = dados.salvar_filamento(
        {"nome": "PLA Rosa", "cor": "Rosa", "gramas": 1000, "preco_kg": 118}, "samir")
    prod = dados.salvar_produto(
        {"nome": "Topo ANA", "gramas": 83.7, "horas": 5.77, "filamento_id": fil}, "samir")
    # Segundo produto para o grafico do U2 ter o que comparar -- e e a
    # comparacao que motivou o grafico: o chaveiro paga a hora melhor.
    dados.salvar_produto(
        {"nome": "Chaveiro", "gramas": 9, "horas": 0.4, "minutos": 5,
         "filamento_id": fil}, "samir")
    # Insumo, compra e geracao para as telas de tabela nao chegarem vazias --
    # tabela sem linha nao prova nada sobre cartao nem sobre largura.
    ins = dados.salvar_insumo({"nome": "Ímã 8 mm", "quantidade": 140, "minimo": 50,
                               "valor_unit": 0.35}, "samir")
    dados.salvar_compra({"data": "2026-09-01", "fornecedor": "3D Fila MS", "nota": "NF 4471"},
                        "samir", itens=[{"tipo": "insumo", "alvo_id": ins,
                                         "quantidade": 100, "valor": 35}])
    cli = dados.salvar_cliente({"nome": "Ana", "canal": "Instagram"}, "samir")
    ped = dados.salvar_pedido({"cliente_id": cli}, "samir", itens=[{
        "produto_id": prod, "descricao": "Topo ANA", "cor": "Rosa", "quantidade": 1,
        "valor_unit": 70, "gramas": 83.7, "horas": 5.77}])
    dados.mudar_situacao(ped, "aprovado", "samir")
    # Um orcamento com link, para a folha publica ter o que abrir.
    global TOKEN
    TOKEN = dados.token_do_orcamento(ped)["token"]

    import logging
    logging.getLogger("werkzeug").setLevel(logging.ERROR)   # uma linha por GET polui a suite

    import wsgi
    importlib.reload(wsgi)
    threading.Thread(target=lambda: wsgi.sistema.run(port=PORTA, threaded=True),
                     daemon=True).start()
    for _ in range(100):                     # espera a porta abrir
        try:
            import urllib.request
            urllib.request.urlopen(f"{SITE}/saude", timeout=1)
            break
        except Exception:
            time.sleep(0.1)
    else:
        raise RuntimeError(f"o servidor de teste nao subiu em {SITE}")

    from playwright.sync_api import sync_playwright
    _pw = sync_playwright().start()
    _navegador = _pw.chromium.launch(executable_path=CHROMIUM)


def tearDownModule():
    if _navegador:
        _navegador.close()
    if _pw:
        _pw.stop()


@unittest.skipUnless(TEM_NAVEGADOR, SEM_NAVEGADOR)
class NoNavegador(unittest.TestCase):
    def setUp(self):
        # Contexto novo por teste (cookie limpo), navegador o mesmo: e o
        # isolamento que interessa sem o preco de abrir o Chromium de novo.
        self.ctx = _navegador.new_context(viewport={"width": 1280, "height": 1000})
        self.addCleanup(self.ctx.close)
        # Fora do ar do 127.0.0.1 nada e carregado: a fonte do Google e o
        # autofill deixam a pagina "carregando" ate estourar o tempo, e o
        # teste passa a medir a internet em vez de medir a tela.
        self.ctx.route("**/*", lambda rota: rota.continue_()
                       if "127.0.0.1" in rota.request.url else rota.abort())
        self.pg = self.ctx.new_page()
        self.abrir("/entrar")
        self.pg.fill("[name=usuario]", "samir")
        self.pg.fill("[name=senha]", "segredo")
        self.pg.click("button[type=submit]")
        self.pg.wait_for_selector("nav")

    def abrir(self, caminho: str):
        self.pg.goto(f"{SITE}{caminho}", wait_until="domcontentloaded")

    def visivel(self, seletor: str) -> bool:
        """Tem caixa na tela? Nao "tem o atributo hidden" -- tem CAIXA."""
        return self.pg.eval_on_selector(seletor, "e => e.offsetParent !== null")

    def nomes_visiveis(self) -> list[str]:
        return self.pg.eval_on_selector_all(
            ".modelo", "e => e.filter(x => x.offsetParent !== null)"
                       "        .map(x => x.querySelector('h3').textContent.trim())")


class TesteFiltroDeCriar(NoNavegador):
    def setUp(self):
        super().setUp()
        self.abrir("/criar")
        self.pg.wait_for_selector(".modelo")

    def chip(self, filtro, valor):
        self.pg.click(f'.grupo-chip[data-filtro="{filtro}"] .chip[data-v="{valor}"]')
        self.pg.wait_for_timeout(120)

    def test_sem_filtro_aparecem_todos_e_o_vazio_fica_escondido(self):
        from sistema import criar
        self.assertEqual(len(self.nomes_visiveis()), len(criar.MODELOS))
        self.assertFalse(self.visivel("#nada"), "o cartao de vazio apareceu com a lista cheia")

    def esperado(self, prova):
        """O que o catalogo diz que deveria sobrar. Assim o teste cobra o
        FILTRO, e nao a lista de modelos do dia -- que cresce a cada sprint."""
        from sistema import criar
        return sorted(m.nome for m in criar.MODELOS if prova(m))

    def test_filtrar_por_uma_cor_esconde_os_de_duas(self):
        """A pergunta real: o que dá para fazer sem trocar filamento?"""
        self.chip("cores", "1")
        esperado = self.esperado(lambda m: 1 in m.cores)
        self.assertEqual(sorted(self.nomes_visiveis()), esperado)
        self.assertTrue(esperado, "nenhum modelo de uma cor: o teste perdeu o sentido")
        self.assertNotIn("Letreiro Terror", esperado)

    def test_filtrar_por_categoria(self):
        self.chip("categoria", "Identidade")
        self.assertEqual(sorted(self.nomes_visiveis()),
                         self.esperado(lambda m: m.categoria == "Identidade"))

    def test_filtrar_por_situacao_mostra_so_o_que_da_para_gerar(self):
        from sistema import criar
        self.chip("status", criar.NO_AR)
        self.assertEqual(sorted(self.nomes_visiveis()),
                         self.esperado(lambda m: m.status == criar.NO_AR))
        for m in criar.MODELOS:
            if m.status != criar.NO_AR:
                self.assertNotIn(m.nome, self.nomes_visiveis())

    def test_a_busca_acha_pelo_tema(self):
        self.pg.fill("#busca", "halloween")
        self.pg.wait_for_timeout(120)
        self.assertEqual(self.nomes_visiveis(), ["Letreiro Terror"])

    def test_busca_sem_resultado_mostra_o_recado_e_esconde_a_lista(self):
        self.pg.fill("#busca", "xilofone")
        self.pg.wait_for_timeout(120)
        self.assertEqual(self.nomes_visiveis(), [])
        self.assertTrue(self.visivel("#nada"), "sumiu tudo e a tela nao explicou nada")

    def test_os_filtros_se_somam(self):
        self.chip("categoria", "Festa")
        self.chip("cores", "1")
        self.assertEqual(sorted(self.nomes_visiveis()),
                         self.esperado(lambda m: m.categoria == "Festa" and 1 in m.cores))

    def test_o_cartao_abre_o_gerador_no_modelo_certo(self):
        """O cartao promete um modelo; o gerador tem que abrir NELE."""
        alvo = self.pg.query_selector_all(".modelo")[5]        # Letreiro Terror
        self.assertEqual(alvo.query_selector("h3").text_content().strip(), "Letreiro Terror")
        alvo.query_selector(".botao").click()
        self.pg.wait_for_selector("#prod")
        # o gerador so escolhe o modelo depois de carregar as cinco fontes
        self.pg.wait_for_function(
            "() => document.querySelector('#prod .opt[aria-pressed=true]')"
            "        .textContent !== 'Clássico'", timeout=15000)
        marcado = self.pg.eval_on_selector('#prod .opt[aria-pressed="true"]', "e => e.textContent")
        self.assertEqual(marcado, "Terror")

    def test_do_gerador_da_para_voltar(self):
        self.abrir("/letreiros?modelo=magia")
        self.pg.click(".volta")
        self.pg.wait_for_selector(".modelo")
        self.assertTrue(self.pg.url.endswith("/criar"), self.pg.url)


class TesteNadaSaiDaTela(NoNavegador):
    """A promessa do U1, medida onde ela vale: num navegador.

    O levantamento achou 920 px de largura em cada tela de um aparelho de
    420 -- 500 px de conteudo empurrado para fora, e a pagina inteira rolando
    de lado. A causa era a barra de menu horizontal, que nao sabe quebrar e
    estica o corpo da pagina.

    Este teste roda em tres larguras porque a ultima sobra que restou nao era
    do menu: era um cartao de 594 px dentro de uma coluna de 372, porque item
    de grid nasce com `min-width:auto` -- "no minimo a largura do conteudo".
    Isso so aparece em tela estreita.
    """

    TELAS = ("/", "/producao", "/pedidos", "/pedidos/1", "/clientes", "/produtos",
             "/compras", "/filamentos", "/insumos", "/criar", "/templates")

    def larguras(self, largura):
        self.pg.set_viewport_size({"width": largura, "height": 900})
        fora = []
        for rota in self.TELAS:
            self.abrir(rota)
            self.pg.wait_for_timeout(120)
            sobra = self.pg.evaluate("() => document.documentElement.scrollWidth") - largura
            if sobra > 0:
                fora.append(f"{rota}: +{sobra}px")
        return fora

    def test_nenhuma_tela_sai_da_tela_no_telefone(self):
        for largura in (360, 420):
            with self.subTest(largura=largura):
                self.assertEqual(self.larguras(largura), [],
                                 f"telas rolando de lado em {largura}px")

    def test_nem_no_tablet_nem_no_computador(self):
        for largura in (768, 1280):
            with self.subTest(largura=largura):
                self.assertEqual(self.larguras(largura), [])


class TesteAFolhaDoCliente(NoNavegador):
    """A única tela sem menu, e a única que abre sem senha.

    O que só o navegador prova: que ela cabe no telefone como as outras, e que
    o botão de aceitar é um alvo de dedo.
    """

    def abrir_folha(self):
        self.pg.set_viewport_size({"width": 420, "height": 800})
        self.abrir(f"/orcamento/{_token_de_teste()}")
        self.pg.wait_for_selector(".folha-publica")

    def test_cabe_no_telefone(self):
        self.abrir_folha()
        sobra = self.pg.evaluate("() => document.documentElement.scrollWidth") - 420
        self.assertEqual(sobra, 0, "a folha do cliente rola de lado")

    def test_a_linha_do_item_virou_cartao_aqui_tambem(self):
        """A folha do cliente herda o U3 de graça, porque é o mesmo CSS."""
        self.abrir_folha()
        estilo = self.pg.eval_on_selector("table.tabela tbody tr",
                                          "e => getComputedStyle(e).display")
        self.assertEqual(estilo, "flex")

    def test_aceitar_e_um_alvo_de_dedo(self):
        self.abrir_folha()
        alto = self.pg.eval_on_selector(".aceitar button",
                                        "e => e.getBoundingClientRect().height")
        self.assertGreaterEqual(alto, 44)

    def test_nao_ha_como_entrar_no_sistema_por_aqui(self):
        """O cliente recebeu um link. Ele não pode virar uma porta."""
        self.abrir_folha()
        self.assertFalse(self.visivel("nav") if self.pg.query_selector("nav") else False)
        destinos = self.pg.eval_on_selector_all(
            "a", "e => e.map(x => x.getAttribute('href'))")
        for destino in destinos:
            self.assertFalse((destino or "").startswith("/pedidos"), destino)

    def test_aceitar_muda_a_tela_e_some_com_o_botao(self):
        """Aceitar duas vezes não é um segundo acordo.

        Com orçamento PRÓPRIO: aceitar tranca a edição, e o servidor e o banco
        são um só para o arquivo inteiro. Já derrubei o teste seguinte assim
        uma vez, no U5.
        """
        from sistema import dados
        cli = dados.salvar_cliente({"nome": "Buffet Estrela"}, "samir")
        ped = dados.salvar_pedido({"cliente_id": cli}, "samir", itens=[
            {"descricao": "Topo", "quantidade": 1, "valor_unit": 70}])
        token = dados.token_do_orcamento(ped)["token"]
        self.pg.set_viewport_size({"width": 420, "height": 800})
        self.abrir(f"/orcamento/{token}")
        self.pg.wait_for_selector(".aceitar")
        self.pg.fill(".aceitar [name=nome]", "Buffet Estrela")
        self.pg.click(".aceitar button")
        self.pg.wait_for_selector(".aceito")
        self.assertIn("Orçamento aceito", self.pg.inner_text(".aceito"))
        self.assertIsNone(self.pg.query_selector(".aceitar button"),
                          "o botão de aceitar continuou na tela")


class TesteNenhumCampoNasceIlegivel(NoNavegador):
    """`.campo input` NASCE escuro.

    A regra base foi escrita para o palco do gerador de logo -- fundo #101215,
    letra clara. A versão da bancada estava presa a `.formulario` e
    `.coluna-lado`, e a folha do orçamento, que não é nenhum dos dois, ganhou
    um campo **preto dentro de um cartão branco**. Vi na foto.

    Isto não se lê no HTML: depende de qual regra ganhou, e a resposta está no
    estilo COMPUTADO. Por isso o teste mede a cor que o navegador aplicou.
    """

    TELAS = ("/pedidos/novo", "/produtos/novo", "/filamentos/novo", "/insumos/novo",
             "/clientes/novo", "/compras/nova", "/templates/novo", "/empresa")

    def claros(self, seletor="body"):
        """Luminância de cada campo visível, e a do fundo atrás dele."""
        return self.pg.evaluate("""() => {
            const luz = c => {
                const [r, g, b] = c.match(/\\d+/g).map(Number);
                return (0.2126*r + 0.7152*g + 0.0722*b) / 255;
            };
            return [...document.querySelectorAll('input, select, textarea')]
              .filter(e => e.getClientRects().length > 0 && e.type !== 'color'
                           && e.type !== 'checkbox' && e.type !== 'file')
              .map(e => ({nome: e.name || e.type,
                          campo: luz(getComputedStyle(e).backgroundColor),
                          letra: luz(getComputedStyle(e).color)}));
        }""")

    def test_campo_claro_com_letra_escura_em_toda_tela_da_bancada(self):
        for rota in self.TELAS:
            self.abrir(rota)
            self.pg.wait_for_timeout(120)
            campos = self.claros()
            self.assertTrue(campos, f"{rota}: nenhum campo para medir")
            for c in campos:
                self.assertGreater(c["campo"], 0.5,
                                   f"{rota}: campo {c['nome']} nasceu escuro")
                self.assertLess(c["letra"], 0.5,
                                f"{rota}: letra clara em campo claro ({c['nome']})")

    def test_na_folha_do_cliente_tambem(self):
        """Ela não é `.formulario` nem `.coluna-lado` -- foi onde apareceu."""
        self.abrir(f"/orcamento/{_token_de_teste()}")
        self.pg.wait_for_selector(".aceitar input[name=nome]")
        campos = self.claros()
        self.assertTrue(campos)
        for c in campos:
            self.assertGreater(c["campo"], 0.5, f"campo {c['nome']} preto na folha branca")

    def test_o_palco_do_gerador_continua_escuro(self):
        """O conserto não pode ter clareado a tela que É escura de propósito."""
        self.abrir("/logo/")
        self.pg.wait_for_timeout(200)
        if not self.pg.query_selector("body.palco"):
            self.skipTest("o gerador de logo não está disponível neste servidor")
        for c in self.claros():
            self.assertLess(c["campo"], 0.5, "o palco clareou")


class TesteAEsperaFala(NoNavegador):
    """O gerador ficava 1,9 s com a tela branca na primeira carga.

    A linha de 14 px embaixo de um retângulo vazio de 700 px não alcança o
    olho, e nesse tempo a página parece travada. Nada disso se mede lendo
    HTML: o que a tela mostra depende de quando o desenho fica pronto.
    """

    def abrir_gerador(self, devagar=False):
        if devagar:
            # Segura o arquivo de fontes: é a primeira carga de verdade, no
            # telefone dele. Com o cache quente a cobertura nem pisca.
            self.pg.route("**/fontes/fontes.js",
                          lambda rota: (time.sleep(1.0), rota.continue_()) and None)
        self.pg.goto(f"{SITE}/criar/topo/", wait_until="commit")

    def cobrindo(self):
        return self.pg.evaluate(
            "() => !!document.querySelector('.estado.cobrindo')")

    def test_enquanto_carrega_a_previa_diz_o_que_esta_fazendo(self):
        self.abrir_gerador(devagar=True)
        # Medir DENTRO da espera, e não depois: entre achar o seletor e medir,
        # o desenho pode ter ficado pronto e a cobertura ter saído -- foi o que
        # aconteceu na primeira versão deste teste, que mediu altura zero.
        foto = self.pg.wait_for_function("""() => {
            const e = document.querySelector('.estado.cobrindo');
            if (!e) return null;
            const r = e.getBoundingClientRect();
            return {texto: e.innerText.trim(), alto: Math.round(r.height)};
        }""", timeout=8000).json_value()
        self.assertTrue(foto["texto"], "a cobertura apareceu sem dizer nada")
        # E cobre MESMO a área da prévia, e não uma linha de 14 px embaixo dela.
        self.assertGreater(foto["alto"], 200, f"a cobertura não cobre a prévia: {foto}")

    def test_quando_o_desenho_fica_pronto_a_cobertura_sai(self):
        self.abrir_gerador()
        self.pg.wait_for_selector("#medidas dd", timeout=15000)
        self.assertFalse(self.cobrindo(), "a cobertura ficou por cima da peça")

    def test_redesenhar_NAO_cobre_a_peca_que_ja_esta_na_tela(self):
        """Com peça na tela, "Desenhando…" é uma linha embaixo.

        Cobrir o desenho por 273 ms a cada tecla piscaria pior do que deixar
        o desenho anterior no lugar até o novo ficar pronto.
        """
        self.abrir_gerador()
        self.pg.wait_for_selector("#medidas dd", timeout=15000)
        # Vigia a cobertura DURANTE o redesenho inteiro, e não só no instante
        # seguinte à tecla: o redesenho não é imediato, e amostrar uma vez
        # passava com a cobertura ligada -- foi o que a mutação mostrou.
        self.pg.evaluate("""() => {
            window.__cobriu = false;
            window.__vigia = new MutationObserver(() => {
                if (document.querySelector('.estado.cobrindo')) window.__cobriu = true;
            });
            window.__vigia.observe(document.getElementById('estado'),
                                   {attributes: true, attributeFilter: ['class']});
        }""")
        self.pg.fill("#nome", "ANA")
        self.pg.wait_for_timeout(900)
        self.assertFalse(self.pg.evaluate("() => window.__cobriu"),
                         "a cobertura tapou a peça durante o redesenho")
        self.assertFalse(self.cobrindo())

    def test_sem_modelo_nenhum_a_previa_ensina_e_da_a_saida(self):
        """Ficava branco para sempre, sem uma palavra.

        A rota devolve lista vazia AQUI, e nao um DELETE no banco: o servidor
        e o banco sao um so para o arquivo inteiro, e a primeira versao deste
        teste apagou os templates que os testes seguintes usavam.
        """
        self.pg.route("**/templates?tipo=*", lambda rota: rota.fulfill(
            status=200, content_type="application/json", body='{"templates": []}'))
        self.abrir_gerador()
        self.pg.wait_for_selector(".estado.cobrindo", timeout=10000)
        texto = self.pg.eval_on_selector("#estado", "e => e.innerText")
        self.assertIn("Nenhum modelo", texto)
        self.assertTrue(self.visivel('#estado a[href="/templates"]'),
                        "a tela vazia precisa oferecer uma saída")

    def test_a_roda_para_quem_pediu_menos_movimento(self):
        """`prefers-reduced-motion` não é enfeite: é acessibilidade.

        A primeira versão procurava a palavra na folha de estilo -- e passava
        com a regra apagada, porque `sistema.css` também tem a palavra. Aqui
        se mede a animação da própria roda, num navegador que pediu calma.
        """
        ctx = _navegador.new_context(viewport={"width": 1280, "height": 900},
                                     reduced_motion="reduce")
        self.addCleanup(ctx.close)
        ctx.route("**/*", lambda rota: rota.continue_()
                  if "127.0.0.1" in rota.request.url else rota.abort())
        pg = ctx.new_page()
        pg.goto(f"{SITE}/entrar", wait_until="domcontentloaded")
        pg.fill("[name=usuario]", "samir"); pg.fill("[name=senha]", "segredo")
        pg.click("form.entrada button[type=submit]"); pg.wait_for_selector("nav")
        pg.route("**/fontes/fontes.js",
                 lambda rota: (time.sleep(1.0), rota.continue_()) and None)
        pg.goto(f"{SITE}/criar/topo/", wait_until="commit")
        pg.wait_for_selector(".estado.cobrindo .girando", timeout=8000)
        animacao = pg.eval_on_selector(".estado .girando",
                                       "e => getComputedStyle(e).animationName")
        self.assertEqual(animacao, "none", "a roda gira para quem pediu menos movimento")


class TesteFormularioQuePerdoa(NoNavegador):
    """O U4 medido onde ele vale.

    Antes: para chegar em Salvar era preciso rolar 1.665 px no cadastro de
    produto. E nenhum dos oito formulários avisava antes de perder o que foi
    digitado -- os dois só se medem num navegador.
    """

    FORMULARIOS = ("/clientes/novo", "/pedidos/novo", "/produtos/novo",
                   "/filamentos/novo", "/insumos/novo", "/compras/nova",
                   "/templates/novo")

    def no_telefone(self):
        self.pg.set_viewport_size({"width": 420, "height": 780})

    def test_salvar_esta_na_tela_sem_rolar_nada(self):
        """A barra gruda no pé enquanto o formulário é maior que a tela."""
        self.no_telefone()
        for rota in self.FORMULARIOS:
            self.abrir(rota)
            self.pg.wait_for_timeout(150)
            visivel = self.pg.evaluate("""() => {
                const b = document.querySelector('main form button[type=submit]');
                if (!b) return 'sem botão';
                const r = b.getBoundingClientRect();
                return (r.bottom <= window.innerHeight + 1 && r.top >= 0) ? '' :
                       Math.round(r.top) + 'px de rolagem';
            }""")
            self.assertEqual(visivel, "", f"{rota}: Salvar fora da tela")

    def test_num_formulario_curto_a_barra_fica_no_fim_dele(self):
        """`sticky` e `fixed` são iguais num formulário comprido -- as duas põem
        a barra no pé da tela. A diferença aparece no CURTO: `sticky` deixa a
        barra em fluxo, no fim do formulário, e `fixed` a descola dali e a
        pendura no pé da tela, sobre o fundo da página.

        Este teste é o que separa as duas. A primeira versão dele media
        sobreposição num formulário comprido e passava com as duas.
        """
        self.no_telefone()
        self.abrir("/clientes/novo")
        self.pg.wait_for_selector(".acoes.principal")
        fora = self.pg.evaluate("""() => {
            const b = document.querySelector('.acoes.principal').getBoundingClientRect();
            const f = document.querySelector('main form').getBoundingClientRect();
            return Math.round(b.bottom - f.bottom);
        }""")
        self.assertLessEqual(fora, 2, "a barra descolou do fim do formulário")

    def test_no_fim_do_formulario_ela_solta_o_ultimo_campo(self):
        self.no_telefone()
        self.abrir("/produtos/novo")
        self.pg.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        self.pg.wait_for_timeout(200)
        tapado = self.pg.evaluate("""() => {
            const barra = document.querySelector('.acoes.principal').getBoundingClientRect();
            return [...document.querySelectorAll('main form .campo input')]
              .filter(e => e.getClientRects().length > 0)
              .some(e => { const r = e.getBoundingClientRect();
                           return r.bottom > barra.top && r.top < barra.bottom; });
        }""")
        self.assertFalse(tapado, "a barra tapou um campo no fim do formulário")

    def avisaria(self):
        """Dispara um beforeunload de mentira e vê se alguém o impediu.

        Melhor do que esperar a caixa do navegador: a caixa depende de
        interação prévia com a página (regra do navegador contra armadilha de
        saída), e o que interessa é se o nosso código pediu para segurar.
        """
        return self.pg.evaluate("""() => {
            const ev = new Event('beforeunload', {cancelable: true});
            window.dispatchEvent(ev);
            return ev.defaultPrevented;
        }""")

    def test_sem_mexer_em_nada_nao_pergunta(self):
        """Abrir e fechar não é perder trabalho."""
        self.abrir("/clientes/novo")
        self.pg.wait_for_selector("form[data-avisar]")
        self.assertFalse(self.avisaria())

    def test_escrever_e_sair_pergunta(self):
        """A promessa: escreva o nome do cliente e tente sair."""
        self.abrir("/clientes/novo")
        self.pg.wait_for_selector("form[data-avisar]")
        self.pg.fill("[name=nome]", "Ana Paula Ribeiro")
        self.assertTrue(self.avisaria(), "o trabalho ia embora em silêncio")

    def test_voltar_ao_valor_de_antes_desarma_o_aviso(self):
        """Digitar e apagar não é alteração -- perguntar ali só irrita."""
        self.abrir("/clientes/novo")
        self.pg.wait_for_selector("form[data-avisar]")
        self.pg.fill("[name=nome]", "Ana")
        self.pg.fill("[name=nome]", "")
        self.assertFalse(self.avisaria())

    def test_cancelar_nao_pergunta(self):
        """Quem clica em Cancelar já disse que desiste.

        Sem isto o aviso aparecia justamente no botão de desistir, que é onde
        ele mais irrita.
        """
        self.abrir("/clientes/novo")
        self.pg.wait_for_selector("form[data-avisar]")
        self.pg.fill("[name=nome]", "Ana Paula Ribeiro")
        self.pg.eval_on_selector("form[data-avisar] a.botao",
                                 "e => e.dispatchEvent(new Event('click', {bubbles: true}))")
        self.assertFalse(self.avisaria(), "Cancelar não pode perguntar")

    def test_salvar_nao_pergunta(self):
        self.abrir("/clientes/novo")
        self.pg.wait_for_selector("form[data-avisar]")
        self.pg.fill("[name=nome]", "Ana Paula Ribeiro")
        self.pg.eval_on_selector("form[data-avisar]",
                                 "e => e.dispatchEvent(new Event('submit', {bubbles: true,"
                                 " cancelable: true}))")
        self.assertFalse(self.avisaria(), "salvar É a saída")

    def test_a_rodinha_do_mouse_nao_muda_o_peso(self):
        """Com o campo focado, rolar a página trocava 83,7 g por 82,7 g.

        É comportamento padrão do navegador em `<input type=number>`. O peso
        vem do arquivo 3D justamente para não ser chute -- e um chute entrava
        assim, sem toque em tecla nenhuma.
        """
        self.abrir("/filamentos/novo")
        self.pg.wait_for_selector("[name=gramas]")
        self.pg.fill("[name=gramas]", "837")
        # A roda precisa passar EM CIMA do campo: o navegador só mexe no valor
        # quando o ponteiro está sobre o campo focado. A primeira versão deste
        # teste rolava a 200,300 -- longe do campo -- e passava sem a guarda.
        caixa = self.pg.eval_on_selector("[name=gramas]",
                                         "e => e.getBoundingClientRect().toJSON()")
        self.pg.focus("[name=gramas]")
        self.pg.mouse.move(caixa["x"] + caixa["width"] / 2,
                           caixa["y"] + caixa["height"] / 2)
        self.pg.mouse.wheel(0, 120)
        self.pg.wait_for_timeout(150)
        self.assertEqual(self.pg.input_value("[name=gramas]"), "837")
        # O que prova a guarda: ela tira o foco do campo antes de o navegador
        # ter para quem mandar a rolagem.
        self.assertIsNone(
            self.pg.evaluate("() => document.activeElement.name || null"),
            "o campo continuou focado: a rodinha ainda pode mexer nele")

    def test_o_erro_leva_ate_o_campo(self):
        """O atalho do topo é um link para o campo -- e ele tem que chegar lá."""
        self.no_telefone()
        self.abrir("/produtos/novo")
        self.pg.wait_for_selector("main form button[type=submit]")
        # Espaco em branco passa pelo `required` do navegador e e recusado pelo
        # servidor -- e e o caminho do servidor que este teste quer exercitar.
        # Com o campo vazio, quem barra e a bolha do proprio navegador, que ja
        # e a primeira linha de defesa e nao chega a fazer a viagem.
        self.pg.fill("[name=nome]", "   ")
        self.pg.click("main form button[type=submit]")
        self.pg.wait_for_selector(".recado.erro")
        self.pg.click('.recado.erro a')
        self.pg.wait_for_timeout(300)
        # O endereço, e não só o resultado: o campo com erro deste formulário
        # fica no alto, então "ficou na tela" passaria até com href="#".
        self.assertEqual(self.pg.evaluate("() => location.hash"), "#campo-nome")
        dentro = self.pg.evaluate("""() => {
            const c = document.querySelector('.campo.com-erro');
            const r = c.getBoundingClientRect();
            return r.top >= 0 && r.bottom <= window.innerHeight;
        }""")
        self.assertTrue(dentro, "o atalho não trouxe o campo para a tela")


class TesteACoisaCabeNaMao(NoNavegador):
    """A promessa do U3, medida onde ela vale: num navegador de 420 px.

    Antes deste sprint eram 75 alvos de toque abaixo de 44 px e oito das nove
    telas com tabela pedindo mais largura do que a caixa tinha. As duas coisas
    so aparecem em tela estreita, e nenhuma se mede lendo HTML.
    """

    TELAS = ("/", "/producao", "/pedidos", "/clientes", "/produtos", "/compras",
             "/filamentos", "/insumos", "/templates")

    def no_telefone(self):
        self.pg.set_viewport_size({"width": 420, "height": 900})

    def test_nenhum_alvo_de_toque_abaixo_de_44_px(self):
        """44 px e o que um dedo acerta. Medido, e nao no olho."""
        self.no_telefone()
        for rota in self.TELAS:
            self.abrir(rota)
            self.pg.wait_for_timeout(120)
            pequenos = self.pg.evaluate("""() => [...document.querySelectorAll(
                  'a,button,input,select,summary,[role=button]')]
                .filter(e => e.getClientRects().length > 0)
                .filter(e => e.getBoundingClientRect().height < 44)
                .map(e => (e.tagName + '.' + e.className).slice(0, 40)
                          + ' "' + (e.textContent || '').trim().slice(0, 20) + '"')""")
            self.assertEqual(pequenos, [], f"{rota}: alvo pequeno demais")

    def test_nenhuma_tabela_precisa_rolar_de_lado(self):
        """A coluna que importa era sempre a que ficava de fora."""
        self.no_telefone()
        for rota in self.TELAS:
            self.abrir(rota)
            self.pg.wait_for_timeout(120)
            sobra = self.pg.evaluate("""() => {
                let pior = 0;
                document.querySelectorAll('table.tabela, table.lista').forEach(t => {
                  const caixa = t.closest('.rolagem') || t.parentElement;
                  pior = Math.max(pior, Math.round(caixa.scrollWidth - caixa.clientWidth));
                });
                return pior;
            }""")
            self.assertEqual(sobra, 0, f"{rota}: tabela pedindo {sobra}px a mais")

    def textos_das_linhas(self):
        """O que a pessoa LE em cada linha -- innerText respeita display:none."""
        return self.pg.eval_on_selector_all(
            "table.tabela tbody tr",
            "e => e.map(l => l.innerText.replace(/\s+/g, ' ').trim())")

    def test_o_cartao_mostra_o_MESMO_que_a_linha(self):
        """A promessa que o DOM unico existe para poder cumprir.

        Se alguem esconder uma coluna no telefone com `display:none` -- que e
        o atalho obvio para "nao cabe" -- o texto dos dois some de um lado so,
        e este teste fica vermelho. E o unico jeito de provar que nada some.
        """
        for rota in ("/pedidos", "/produtos", "/filamentos", "/clientes", "/compras"):
            self.pg.set_viewport_size({"width": 1280, "height": 1000})
            self.abrir(rota)
            self.pg.wait_for_timeout(150)
            largo = self.textos_das_linhas()
            self.pg.set_viewport_size({"width": 420, "height": 900})
            self.pg.wait_for_timeout(150)
            estreito = self.textos_das_linhas()
            self.assertTrue(largo, f"{rota} sem linhas: o teste perdeu o sentido")
            self.assertEqual(largo, estreito, f"{rota}: o cartão e a linha divergem")

    def test_no_computador_continua_sendo_tabela(self):
        """O cartao e para o telefone. Em 1280 px a tabela e melhor: sete
        colunas lado a lado se comparam com o olho, e o cartao nao."""
        self.pg.set_viewport_size({"width": 1280, "height": 1000})
        self.abrir("/pedidos")
        self.pg.wait_for_timeout(150)
        self.assertTrue(self.visivel("table.tabela thead"), "o cabeçalho sumiu no computador")
        estilo = self.pg.eval_on_selector("table.tabela tbody tr",
                                          "e => getComputedStyle(e).display")
        self.assertEqual(estilo, "table-row")

    def test_no_telefone_a_linha_vira_cartao(self):
        self.no_telefone()
        self.abrir("/pedidos")
        self.pg.wait_for_timeout(150)
        self.assertFalse(self.visivel("table.tabela thead"), "cabeçalho de tabela num cartão")
        estilo = self.pg.eval_on_selector("table.tabela tbody tr",
                                          "e => getComputedStyle(e).display")
        self.assertEqual(estilo, "flex")

    def test_o_rotulo_da_coluna_aparece_no_cartao(self):
        """Sem o rotulo o cartao vira uma pilha de numeros sem nome."""
        self.no_telefone()
        self.abrir("/pedidos")
        self.pg.wait_for_timeout(150)
        rotulo = self.pg.eval_on_selector(
            'td[data-rotulo="Canal"]',
            "e => getComputedStyle(e, '::before').content")
        self.assertIn("Canal", rotulo)

    def test_o_titulo_do_cartao_NAO_ganha_rotulo(self):
        """"Cliente" escrito em cima do nome do cliente e ruido."""
        self.no_telefone()
        self.abrir("/pedidos")
        self.pg.wait_for_timeout(150)
        for seletor in ("td.chave", "td.estado", "td.acao"):
            conteudo = self.pg.eval_on_selector(
                seletor, "e => getComputedStyle(e, '::before').content")
            self.assertIn(conteudo, ("none", "normal", '""'), f"{seletor} com rótulo")

    def test_ordenar_pelo_telefone_existe_e_funciona(self):
        """No telefone nao ha cabecalho para clicar: a ordem sai da caixa."""
        self.no_telefone()
        self.abrir("/produtos")
        self.pg.wait_for_selector(".peneira select")
        self.assertTrue(self.visivel(".peneira select"), "a caixa de ordem não aparece")
        self.pg.select_option(".peneira select", "hora")
        self.pg.wait_for_timeout(250)
        self.assertIn("ordem=hora", self.pg.url)

    def test_no_computador_a_caixa_de_ordem_sai_da_frente(self):
        """La o cabecalho clicavel faz o mesmo, e melhor."""
        self.pg.set_viewport_size({"width": 1280, "height": 1000})
        self.abrir("/produtos")
        self.pg.wait_for_timeout(150)
        self.assertFalse(self.visivel(".peneira select"))
        self.assertTrue(self.visivel("th a.ordenar"))


class TesteOPlacarEOGrafico(NoNavegador):
    """O U2 medido onde ele vale: numa tela de verdade.

    O grafico e feito de `left` e `width` em porcentagem. Porcentagem errada
    nao da erro em lugar nenhum: a barra passa por cima do numero, ou fica em
    zero e some. O HTML servido nao denuncia nem um nem outro.
    """

    def setUp(self):
        super().setUp()
        self.abrir("/")
        self.pg.wait_for_selector(".placar")

    def caixa(self, seletor):
        return self.pg.eval_on_selector(seletor, "e => e.getBoundingClientRect().toJSON()")

    def test_os_quatro_numeros_estao_na_tela(self):
        for ident in ("v-a-receber", "v-na-mesa", "v-parado", "v-entregue"):
            self.assertTrue(self.visivel(f"#{ident}"), f"{ident} sem caixa na tela")

    def test_cada_numero_e_um_alvo_de_toque(self):
        """44 px e o minimo que um dedo acerta -- a regra que o U1 estabeleceu."""
        self.pg.set_viewport_size({"width": 420, "height": 900})
        self.pg.wait_for_timeout(120)
        alturas = self.pg.eval_on_selector_all(
            ".placar a", "e => e.map(x => x.getBoundingClientRect().height)")
        self.assertEqual(len(alturas), 4)
        for h in alturas:
            self.assertGreaterEqual(h, 44)

    def test_a_barra_nao_passa_do_trilho(self):
        """Barra que vaza do trilho passa por cima do numero ao lado."""
        for largura in (420, 1280):
            self.pg.set_viewport_size({"width": largura, "height": 900})
            self.pg.wait_for_timeout(120)
            sobras = self.pg.eval_on_selector_all(".linha-h", """e => e.map(l => {
                const t = l.querySelector('.trilho').getBoundingClientRect();
                const b = l.querySelector('i').getBoundingClientRect();
                return Math.max(t.left - b.left, b.right - t.right);
            })""")
            self.assertTrue(sobras, "nenhuma barra desenhada")
            for sobra in sobras:
                self.assertLessEqual(sobra, 0.5, f"barra fora do trilho em {largura}px")

    def test_nenhuma_barra_nasce_invisivel(self):
        """Retorno pequeno da barra curta -- curta nao pode virar nenhuma."""
        larguras = self.pg.eval_on_selector_all(
            ".linha-h i", "e => e.map(x => x.getBoundingClientRect().width)")
        self.assertTrue(larguras)
        for w in larguras:
            self.assertGreaterEqual(w, 2)

    def test_a_barra_maior_e_a_do_produto_que_paga_melhor(self):
        """O grafico so serve se o comprimento seguir o numero."""
        pares = self.pg.eval_on_selector_all(".linha-h", """e => e.map(l => [
            l.querySelector('.nome').textContent.trim(),
            l.querySelector('i').getBoundingClientRect().width])""")
        pares.sort(key=lambda x: -x[1])
        self.assertEqual(pares[0][0], "Chaveiro")

    def test_a_tabela_do_leitor_de_tela_nao_ocupa_espaco(self):
        """Fora da tela, e nao display:none -- leitor de tela pula o que some."""
        caixa = self.caixa("div.so-leitor")
        self.assertLessEqual(caixa["width"], 2)
        self.assertLessEqual(caixa["height"], 2)


class TesteAGaveta(NoNavegador):
    """A lateral no telefone: abre, fecha, e devolve o foco de onde saiu."""

    def setUp(self):
        super().setUp()
        self.pg.set_viewport_size({"width": 420, "height": 900})
        self.abrir("/filamentos")
        self.pg.wait_for_selector("#abrir-menu")

    def esquerda(self):
        return self.pg.eval_on_selector(
            ".lateral", "e => Math.round(e.getBoundingClientRect().left)")

    def test_comeca_fora_da_tela(self):
        self.assertLess(self.esquerda(), 0, "a gaveta comeca aberta")
        self.assertEqual(self.pg.get_attribute("#abrir-menu", "aria-expanded"), "false")

    def test_abre_e_cobre_a_pagina(self):
        self.pg.click("#abrir-menu")
        self.pg.wait_for_timeout(320)
        self.assertEqual(self.esquerda(), 0)
        self.assertEqual(self.pg.get_attribute("#abrir-menu", "aria-expanded"), "true")
        # o veu tem que estar POR CIMA do conteudo, e nao so existir
        self.assertEqual(self.pg.evaluate(
            "() => { const e = document.elementFromPoint(390, 500); return e && e.id; }"),
            "veu", "o veu nao esta cobrindo a pagina")

    def test_ao_abrir_o_foco_entra_na_gaveta(self):
        """Senao quem navega por teclado abre o menu e continua fora dele.

        A primeira versao mirava o primeiro `a` da lateral -- que no telefone
        e o link da marca, escondido por CSS. `focus()` em elemento escondido
        nao faz nada e nao da erro: o foco ficava no botao, e o teste que so
        olhava o Escape passava, porque voltar para o botao era um no-op.
        """
        self.pg.click("#abrir-menu")
        self.pg.wait_for_timeout(320)
        dentro = self.pg.evaluate(
            "() => document.getElementById('lateral').contains(document.activeElement)")
        self.assertTrue(dentro, "o foco nao entrou na gaveta")

    def test_o_escape_fecha_e_devolve_o_foco(self):
        self.pg.click("#abrir-menu")
        self.pg.wait_for_timeout(320)
        self.assertTrue(self.pg.evaluate(
            "() => document.getElementById('lateral').contains(document.activeElement)"),
            "o foco precisa estar DENTRO da gaveta para o retorno ser observavel")
        self.pg.keyboard.press("Escape")
        self.pg.wait_for_timeout(320)
        self.assertLess(self.esquerda(), 0)
        self.assertEqual(self.pg.evaluate("() => document.activeElement.id"), "abrir-menu",
                         "o foco nao voltou para o botao que abriu")

    def test_o_veu_fecha(self):
        self.pg.click("#abrir-menu")
        self.pg.wait_for_timeout(320)
        self.pg.click("#veu", position={"x": 390, "y": 500})
        self.pg.wait_for_timeout(320)
        self.assertLess(self.esquerda(), 0)

    def test_o_grupo_da_tela_atual_abre_sozinho(self):
        self.pg.click("#abrir-menu")
        self.pg.wait_for_timeout(320)
        abertos = self.pg.eval_on_selector_all(
            ".grupo[open] > summary", "e => e.map(x => x.textContent.trim())")
        self.assertEqual(abertos, ["Cadastros"], "abriu o grupo errado em Filamentos")

    def test_os_grupos_funcionam_sem_javascript(self):
        """Sao <details>: abrem pelo teclado sozinhos. Se um dia isso virar
        JavaScript, o menu para de funcionar quando o script nao carregar."""
        self.assertEqual(self.pg.eval_on_selector_all(".grupo", "e => e.map(x => x.tagName)"),
                         ["DETAILS", "DETAILS", "DETAILS"])

    def test_no_computador_a_lateral_fica_a_vista(self):
        self.pg.set_viewport_size({"width": 1280, "height": 900})
        self.abrir("/filamentos")
        self.pg.wait_for_timeout(200)
        self.assertEqual(self.esquerda(), 0, "a lateral sumiu no computador")
        self.assertFalse(self.pg.eval_on_selector("#veu", "e => !e.hidden"),
                         "o veu aparece no computador")

    def test_todo_item_do_menu_alcanca_o_dedo(self):
        self.pg.click("#abrir-menu")
        self.pg.wait_for_timeout(320)
        pequenos = self.pg.eval_on_selector_all(
            ".lateral .itens a, .lateral summary, #abrir-menu",
            "e => e.filter(x => x.getBoundingClientRect().height < 44).length")
        self.assertEqual(pequenos, 0, "item de menu abaixo de 44 px")


class TesteATravaDoDownload(NoNavegador):
    """Peca reprovada nao gera arquivo. Nunca.

    Ate o C1 havia dois caminhos: um AVISAVA que a peca tinha saido em partes
    soltas, o outro -- o que liga o botao -- olhava so se cabia na mesa. O
    aviso rolava para fora da tela e o STL ia para a impressora.

    Achar uma peca de verdade que saia em partes soltas e dificil, e isso e
    bom: o gerador trabalha para que nao aconteca. O que da para provar aqui e
    a COSTURA -- que a tela obedece a vistoria -- e e isso que se quebra numa
    mudanca futura. A decisao em si tem teste proprio em test_nucleo.py.
    """

    def setUp(self):
        super().setUp()
        self.abrir("/letreiros/?modelo=classico")
        self.pg.wait_for_selector("#baixar", state="attached")
        self.pg.wait_for_function(
            "() => document.querySelector('#baixar').children.length > 0", timeout=30000)

    def botoes(self):
        return self.pg.eval_on_selector_all(
            "#baixar .btn", "e => e.map(b => ({off: b.disabled, why: b.title}))")

    def redesenhar(self, nome):
        self.pg.fill("#nome", nome)
        self.pg.wait_for_function(
            "() => document.querySelector('#baixar').children.length > 0", timeout=30000)
        self.pg.wait_for_timeout(700)

    def test_peca_boa_pode_baixar(self):
        self.redesenhar("MORUMBI")
        botoes = self.botoes()
        self.assertTrue(botoes, "nenhum botao de baixar apareceu")
        for b in botoes:
            self.assertFalse(b["off"], f"peca boa com download travado: {b}")

    def test_peca_reprovada_nao_pode_baixar(self):
        """A vistoria diz nao; a tela tem que obedecer, e dizer por que."""
        self.pg.evaluate("""() => {
          const antes = MorumbiOficina.vistoriar;
          MorumbiOficina.vistoriar = p => Object.assign(antes(p), {
            ok: false, motivos: ["A peça saiu em 3 partes soltas em vez de 1."] });
        }""")
        self.redesenhar("MORUMBI ")
        botoes = self.botoes()
        self.assertTrue(botoes, "nenhum botao de baixar apareceu")
        for b in botoes:
            self.assertTrue(b["off"], f"peca reprovada continuou baixavel: {b}")
            self.assertIn("partes soltas", b["why"])
        avisos = self.pg.eval_on_selector_all(
            ".aviso.mal", "e => e.map(x => x.textContent)")
        self.assertTrue(any("partes soltas" in a for a in avisos),
                        f"a tela travou o botao mas nao disse por que: {avisos}")


class TesteConfiguracaoGuardada(NoNavegador):
    """Reimprimir e regerar -- nao caçar o arquivo antigo e adivinhar o tamanho."""

    def abrir_gerador(self, busca=""):
        self.abrir(f"/letreiros/{busca}")
        self.pg.wait_for_selector("#baixar", state="attached")
        self.pg.wait_for_function(
            "() => document.querySelector('#baixar').children.length > 0", timeout=30000)
        self.pg.wait_for_timeout(400)

    def marcado(self, caixa):
        return self.pg.eval_on_selector(f'#{caixa} .opt[aria-pressed="true"]', "e => e.dataset.v")

    def test_o_que_voce_deixou_volta_na_proxima_visita(self):
        self.abrir_gerador()
        self.pg.fill("#nome", "BEATRIZ")
        self.pg.click('#prod .opt[data-v="cinema"]')
        self.pg.click('#tam .opt[data-v="280"]')
        self.pg.wait_for_timeout(600)

        self.abrir_gerador()
        self.assertEqual(self.pg.input_value("#nome"), "BEATRIZ")
        self.assertEqual(self.marcado("prod"), "cinema")
        self.assertEqual(self.marcado("tam"), "280")

    def test_o_cartao_do_catalogo_ganha_do_que_estava_guardado(self):
        """Quem clicou em Terror quer Terror, nao o que gerou semana passada."""
        self.abrir_gerador()
        self.pg.click('#prod .opt[data-v="cinema"]')
        self.pg.wait_for_timeout(600)

        self.abrir_gerador("?modelo=terror")
        self.assertEqual(self.marcado("prod"), "terror")

    def test_lixo_guardado_nao_derruba_a_tela(self):
        """localStorage e do navegador da pessoa: pode ter qualquer coisa."""
        self.abrir_gerador()
        self.pg.evaluate("() => localStorage.setItem('morumbi3d.letreiro', '{isso nao e json')")
        self.abrir_gerador()
        self.assertEqual(self.marcado("prod"), "classico")

    def test_chave_desconhecida_nao_vira_parametro(self):
        """Versao antiga, ou alguem editando a mao: so entra o que o gerador entende."""
        self.abrir_gerador()
        self.pg.evaluate("""() => localStorage.setItem('morumbi3d.letreiro',
            JSON.stringify({produto: 'magia', inventado: 'xis', esp: 999}))""")
        self.abrir_gerador()
        self.assertEqual(self.marcado("prod"), "magia")
        self.assertEqual(self.pg.input_value("#esp"), "12")
        # O que importa nao e o menu: e o numero com que a peca foi GERADA.
        # Com so o filtro de chaves, a tela mostrava 12 mm e o gerador recebia
        # 999 -- e o STL saia com uma espessura que nao esta em lugar nenhum.
        self.assertIn("12mm", self.pg.inner_text("#dados"),
                      "a peca foi gerada com uma espessura que a tela nao oferece")

    def test_tamanho_invalido_guardado_tambem_e_descartado(self):
        """O mesmo, pelo caminho dos botoes -- que e outro codigo."""
        self.abrir_gerador()
        self.pg.evaluate("""() => localStorage.setItem('morumbi3d.letreiro',
            JSON.stringify({nome: 'LUA', largura: 999, produto: 'classico'}))""")
        self.abrir_gerador()
        self.assertEqual(self.marcado("tam"), "220")
        # A largura nao denuncia sozinha: o gerador apara a peca para caber na
        # mesa, entao 999 vira ~243 e passa por "grande, mas plausivel". Quem
        # denuncia e a ALTURA DA LETRA -- ela nao pode passar de 60 mm, que e o
        # tamanho do glifo. Com o 999 valendo, sai 272 mm por linha.
        altura = int(self.pg.evaluate(
            "() => document.querySelector('#dados').textContent.match(/(\\d+)mm por linha/)[1]"))
        self.assertLessEqual(altura, 60,
                             f"letra de {altura}mm: o tamanho guardado passou por cima do botao")

    def test_o_que_a_tela_guarda_e_so_o_que_ela_entende(self):
        """Sem isto, chave estranha entra, e `guardar()` a devolve para sempre."""
        self.abrir_gerador()
        self.pg.evaluate("""() => localStorage.setItem('morumbi3d.letreiro',
            JSON.stringify({produto: 'magia', inventado: 'xis'}))""")
        self.abrir_gerador()
        self.pg.fill("#nome", "ZOE")
        self.pg.wait_for_timeout(600)
        chaves = self.pg.evaluate(
            "() => Object.keys(JSON.parse(localStorage.getItem('morumbi3d.letreiro')))")
        self.assertNotIn("inventado", chaves, f"chave estranha ficou guardada: {chaves}")


class TesteImpressaoDigital(unittest.TestCase):
    """A prova do C1: o que sai do gerador nao mudou.

    Vinte casos, um sha256 por peca, guardados em docs/impressao-digital.txt.
    E o unico jeito honesto de mexer em geometria: um teste que so olha "malha
    fechada" passa feliz com a peca virada do avesso; um hash nao passa.

    Demora ~75 s, quase tudo em abrir o Chromium e ler as cinco fontes. Vale:
    e a diferenca entre refatorar e torcer.
    """

    @unittest.skipUnless(TEM_NAVEGADOR, SEM_NAVEGADOR)
    def test_a_matriz_inteira_sai_igual(self):
        import subprocess
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        node = shutil.which("node") or "/opt/node22/bin/node"
        if not os.path.exists(node):
            self.skipTest("node nao instalado")
        r = subprocess.run(
            [node, os.path.join(raiz, "ferramentas", "impressao_digital.js"),
             "--conferir", os.path.join(raiz, "docs", "impressao-digital.txt")],
            capture_output=True, text=True, timeout=600, cwd=raiz,
            env={**os.environ, "CHROME_BIN": CHROMIUM})
        self.assertEqual(r.returncode, 0,
                         "a geometria mudou:\n" + (r.stderr or r.stdout)[:4000])


class TesteTemplatesNoGerador(NoNavegador):
    """O percurso do C3: o que esta no banco e o que a tela do topo oferece.

    Ate o C2 os modelos eram uma constante no JavaScript. Agora a pagina busca
    em /topo/templates, e e so no navegador que da para ver se ela realmente
    busca -- um teste de rota veria a API responder e nao veria a tela usar.
    """

    def abrir_topo(self, busca=""):
        self.abrir(f"/criar/topo/{busca}")
        self.pg.wait_for_selector("#modelos", state="attached")
        self.pg.wait_for_timeout(600)

    def modelos(self):
        return self.pg.eval_on_selector_all(
            "#modelos .modelo", "e => e.map(x => x.dataset.sku)")

    def test_a_tela_mostra_os_modelos_da_peca_dela(self):
        """Nao TODOS os templates: os do topo. Desde o C4 ha chaveiro tambem,
        e um gerador mostrando o template do outro seria uma tela mentindo."""
        from sistema import dados
        self.abrir_topo()
        self.assertEqual(sorted(self.modelos()),
                         sorted(t["sku"] for t in dados.templates(tipo="topo")))
        self.assertTrue(dados.templates(tipo="chaveiro"), "nao ha chaveiro para comparar")
        for t in dados.templates(tipo="chaveiro"):
            self.assertNotIn(t["sku"], self.modelos())

    def test_o_selo_de_em_teste_aparece_no_painel(self):
        """Voce precisa VER quais ainda nao foram impressos, gerando por eles."""
        self.abrir_topo()
        selos = self.pg.eval_on_selector_all(".modelo .teste", "e => e.length")
        self.assertEqual(selos, len(self.modelos()),
                         "os modelos em teste nao estao marcados")

    def test_cadastrar_um_template_o_faz_aparecer_no_gerador(self):
        """A promessa inteira do sprint, de ponta a ponta e sem tocar em codigo."""
        self.abrir("/templates/novo")
        self.pg.fill("[name=sku]", "M3D-TB-500")
        self.pg.fill("[name=modelo]", "Nome com estrela nova")
        self.pg.fill("[name=licenca]", "própria")
        self.pg.select_option("[name=forma]", "estrela")
        # `button[type=submit]` sozinho pega o "Sair" do menu, que tambem e um
        # submit -- e o teste ia parar na tela de login achando que o cadastro
        # falhou. O botao e o do formulario.
        self.pg.click("form.formulario button[type=submit]")
        self.pg.wait_for_url("**/templates/M3D-TB-500")

        self.abrir_topo()
        self.assertIn("M3D-TB-500", self.modelos())

    def test_a_geracao_vai_para_o_painel(self):
        from sistema import dados
        self.abrir_topo("?modelo=M3D-TB-002")
        self.pg.wait_for_selector("#modelos .modelo")
        self.pg.fill("#nome", "CLARA")
        self.pg.wait_for_function(
            "() => document.querySelector('#medidas').children.length > 0", timeout=40000)
        self.pg.wait_for_timeout(500)
        self.pg.click("#gerar")
        self.pg.wait_for_timeout(1200)
        g = dados.geracoes(sku="M3D-TB-002")
        self.assertTrue(g, "a geracao nao chegou ao painel")
        self.assertEqual(g[0]["nome"], "CLARA")
        self.assertGreater(g[0]["gramas"], 0, "o peso nao foi registrado")
        self.assertGreater(g[0]["preco"], 0, "o preco nao foi registrado")


class TesteMalhaDasPecas(unittest.TestCase):
    """§16 do documento: "o modelo fatia sem erros".

    Gera os topos num navegador de verdade e passa cada STL pelo analisador de
    malha do pacote -- o mesmo criterio do fatiador. E o unico teste do sprint
    que fala a lingua da impressora.

    Foi ele que achou o pior bug do C2: oito pecas APROVADAS pelo gerador com
    aresta nao-manifold, porque o coracao saia no sentido horario e o Clipper
    o tratava como furo. Na tela o desenho parecia certo -- canvas nao liga
    para sentido de poligono.

    Roda a matriz curta: os nomes e tamanhos extremos das DUAS pecas, que e
    onde quebra. A matriz inteira e `node ferramentas/conferir_pecas.js`.
    """

    @unittest.skipUnless(TEM_NAVEGADOR, SEM_NAVEGADOR)
    def test_toda_peca_gerada_tem_malha_que_o_fatiador_aceita(self):
        import subprocess
        import tempfile
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        node = shutil.which("node") or "/opt/node22/bin/node"
        if not os.path.exists(node):
            self.skipTest("node nao instalado")
        pasta = tempfile.mkdtemp(prefix="topos-")
        r = subprocess.run(
            [node, os.path.join(raiz, "ferramentas", "conferir_pecas.js"), pasta, "--rapido"],
            capture_output=True, text=True, timeout=600, cwd=raiz,
            env={**os.environ, "CHROME_BIN": CHROMIUM})
        self.assertEqual(r.returncode, 0, (r.stderr or r.stdout)[:3000])
        self.assertNotIn("REPROVADA", r.stdout,
                         "o gerador aprovou peca que nao passa na propria vistoria")

        import sys
        sys.path.insert(0, raiz)
        from morumbi3d.config import carregar_config
        from morumbi3d.mesh import analisar_arquivo
        import pathlib

        cfg = carregar_config()
        arquivos = sorted(pathlib.Path(pasta).glob("*.stl"))
        self.assertGreaterEqual(len(arquivos), 12, "quase nada foi gerado")
        ruins = []
        for a in arquivos:
            m = analisar_arquivo(a, cfg)
            if not m.fechada or m.partes_soltas > 1:
                ruins.append(f"{a.name}: abertas={m.arestas_abertas} "
                             f"nao-manifold={m.arestas_nao_manifold} "
                             f"partes={m.partes_soltas}")
        self.assertEqual(ruins, [], f"{len(ruins)} de {len(arquivos)} nao imprimem:\n"
                                    + "\n".join(ruins[:8]))


class TesteQuadroELista(NoNavegador):
    """A tela da producao alterna entre duas vistas. Uma de cada vez.

    Passou um sprint inteiro mostrando as duas empilhadas quando se clicava em
    "Lista", pela mesma razao do filtro: `.quadro{display:grid}` ganhava do
    `[hidden]`. Nenhum teste de rota via isso -- os dois estavam no HTML.
    """

    def setUp(self):
        super().setUp()
        self.abrir("/producao")
        self.pg.wait_for_selector(".quadro")

    def test_comeca_no_quadro(self):
        self.assertTrue(self.visivel(".quadro"))
        self.assertFalse(self.visivel("#lista"))

    def test_lista_esconde_o_quadro(self):
        self.pg.click('#modos [data-modo="lista"]')
        self.pg.wait_for_timeout(120)
        self.assertTrue(self.visivel("#lista"))
        self.assertFalse(self.visivel(".quadro"), "o quadro continuou na tela junto da lista")

    def test_e_da_para_voltar_para_o_quadro(self):
        self.pg.click('#modos [data-modo="lista"]')
        self.pg.click('#modos [data-modo="quadro"]')
        self.pg.wait_for_timeout(120)
        self.assertTrue(self.visivel(".quadro"))
        self.assertFalse(self.visivel("#lista"))
