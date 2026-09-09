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
    cli = dados.salvar_cliente({"nome": "Ana", "canal": "Instagram"}, "samir")
    ped = dados.salvar_pedido({"cliente_id": cli}, "samir", itens=[{
        "produto_id": prod, "descricao": "Topo ANA", "cor": "Rosa", "quantidade": 1,
        "valor_unit": 70, "gramas": 83.7, "horas": 5.77}])
    dados.mudar_situacao(ped, "aprovado", "samir")

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
