# -*- coding: utf-8 -*-
"""Sprint U1 -- a navegacao cabe no telefone.

O levantamento que abriu esta trilha mediu, em cada tela, num navegador de
420 px: **920 px de largura**. Nao era o menu que saia da tela -- era TUDO,
porque uma barra horizontal de dez links nao sabe quebrar e estica o corpo da
pagina inteira. O conteudo abaixo ficava espremido no lado esquerdo, e a
tabela de pedidos era cortada no meio da coluna de valor.

Dez links nao cabem em 420 px, e nao iam caber em doze. A barra virou lateral
no computador e gaveta no telefone.

O menu agora e DADO (`MENU`, em app.py), e nao dez linhas escritas a mao numa
tela. Tres coisas passaram a ser possiveis por causa disso, e sao o que este
arquivo cobra: cada item leva a uma rota que responde, o grupo certo abre no
que voce esta usando, e nenhum item fica fora de um grupo.

A largura de cada tela e a gaveta em si sao cobradas em tests/test_navegador.py,
num navegador de verdade -- largura de pagina nao se mede lendo HTML.
"""
from __future__ import annotations

import importlib
import os
import re
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Base(unittest.TestCase):
    def setUp(self):
        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-nav-")
        os.environ["MORUMBI_USUARIO"] = "samir"
        os.environ["MORUMBI_SENHA"] = "segredo"
        os.environ["MORUMBI_BIND"] = "127.0.0.1:5000"
        os.environ["MORUMBI_HTTPS"] = "0"
        from sistema import auth, dados
        importlib.reload(dados)
        importlib.reload(auth)
        from sistema import app as modulo
        importlib.reload(modulo)
        self.modulo = modulo
        self.app = modulo.criar_app()
        self.app.config["TESTING"] = True
        self.cliente = self.app.test_client()
        self.cliente.post("/entrar", data={"usuario": "samir", "senha": "segredo"})


class TesteOMenuEDado(Base):
    def test_todo_item_leva_a_uma_rota_que_responde(self):
        """A razao de o menu ter virado dado.

        Numa lista de dez links escritos a mao, um item apontando para o lugar
        errado nao aparece ate alguem clicar. Aqui abre-se todos.
        """
        for _, _, itens in self.modulo.MENU:
            for endereco, rotulo, _ in itens:
                with self.subTest(item=rotulo):
                    with self.app.test_request_context():
                        from flask import url_for
                        rota = url_for(endereco)
                    r = self.cliente.get(rota, follow_redirects=True)
                    self.assertEqual(r.status_code, 200, f"{rotulo} -> {rota}")

    def test_nenhum_item_fica_fora_de_um_grupo(self):
        """Item sem grupo nao aparece na lateral, e ninguem descobre."""
        for _, _, itens in self.modulo.MENU:
            self.assertTrue(itens, "grupo vazio no menu")
        enderecos = [e for _, _, itens in self.modulo.MENU for e, _, _ in itens]
        self.assertEqual(len(enderecos), len(set(enderecos)), "item repetido no menu")

    def test_o_grupo_certo_abre_no_que_voce_esta_usando(self):
        """Sem isto, quem chega em Filamentos ve os tres grupos fechados."""
        casos = {"painel": "operacao", "producao": "operacao",
                 "lista_filamentos": "cadastros", "lista_compras": "cadastros",
                 "tela_criar": "personalizacao", "lista_templates": "personalizacao"}
        for endereco, esperado in casos.items():
            with self.subTest(endereco=endereco):
                self.assertEqual(self.modulo._grupo_de(endereco), esperado)

    def test_rota_de_fora_do_menu_nao_quebra(self):
        """A ficha de um pedido nao esta no menu; a lateral tem que desenhar."""
        self.assertEqual(self.modulo._grupo_de("editar_pedido"), self.modulo.MENU[0][1])
        self.assertEqual(self.modulo._grupo_de(None), self.modulo.MENU[0][1])

    def test_toda_tela_do_menu_marca_onde_voce_esta(self):
        for _, _, itens in self.modulo.MENU:
            for endereco, rotulo, marca in itens:
                with self.app.test_request_context():
                    from flask import url_for
                    rota = url_for(endereco)
                pagina = self.cliente.get(rota, follow_redirects=True).get_data(as_text=True)
                with self.subTest(item=rotulo):
                    self.assertIn('aria-current=page', pagina,
                                  f"{rotulo} nao se marca como a tela atual")


class TesteACascaDeTodaTela(Base):
    """A lateral desenha em toda tela, e nao esconde nada do que ja havia."""

    TELAS = ("/", "/producao", "/pedidos", "/clientes", "/produtos", "/compras",
             "/filamentos", "/insumos", "/criar", "/templates")

    def test_a_lateral_aparece_em_toda_tela(self):
        for rota in self.TELAS:
            with self.subTest(rota=rota):
                pagina = self.cliente.get(rota).get_data(as_text=True)
                self.assertIn('class="lateral"', pagina)
                self.assertIn('id="abrir-menu"', pagina)

    def test_toda_tela_tem_para_onde_pular(self):
        """Quem navega por teclado nao pode atravessar dez links do menu em
        cada tela antes de chegar no conteudo."""
        for rota in self.TELAS:
            with self.subTest(rota=rota):
                pagina = self.cliente.get(rota).get_data(as_text=True)
                self.assertIn('class="pular" href="#conteudo"', pagina)
                self.assertIn('id="conteudo"', pagina, "o alvo do pular nao existe")

    def test_a_barra_do_celular_tem_nome_proprio(self):
        """Chamei a barra do celular de , e  ja era das barras
        de estoque do painel: elas sumiram da tela, sem erro nenhum no
        console. Nome curto e barato ate colidir."""
        with open(os.path.join(RAIZ, "sistema", "static", "sistema.css"),
                  encoding="utf-8") as f:
            folha = f.read()
        self.assertIn(".barra-topo", folha)
        self.assertTrue(".barra{display:none}" not in folha,
                        "a barra do celular voltou a se chamar .barra")

    def test_as_barras_de_estoque_continuam_no_painel(self):
        """O que a colisao de nome tinha apagado."""
        from sistema import dados
        dados.salvar_filamento({"nome": "PLA Rosa", "cor": "Rosa", "gramas": 800,
                                "minimo": 300, "preco_kg": 118}, "samir")
        pagina = self.cliente.get("/").get_data(as_text=True)
        self.assertGreaterEqual(len(re.findall(r'class="barra"', pagina)), 1,
                                "as barras de estoque sumiram do painel")
