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

    def test_filtrar_por_uma_cor_esconde_os_de_duas(self):
        """A pergunta real: o que dá para fazer sem trocar filamento?"""
        self.chip("cores", "1")
        self.assertEqual(sorted(self.nomes_visiveis()), ["Letreiro Clássico", "Logo 3D"])

    def test_filtrar_por_categoria(self):
        self.chip("categoria", "Identidade")
        self.assertEqual(self.nomes_visiveis(), ["Logo 3D"])

    def test_filtrar_por_situacao_mostra_so_o_que_da_para_gerar(self):
        from sistema import criar
        self.chip("status", criar.NO_AR)
        self.assertNotIn("Topo de bolo", self.nomes_visiveis())
        self.assertEqual(len(self.nomes_visiveis()), criar.contagem()["no_ar"])

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
        self.assertEqual(self.nomes_visiveis(), ["Letreiro Clássico"])

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
