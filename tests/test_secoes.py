# -*- coding: utf-8 -*-
"""Sprint P4 — reorganização do cadastro de produto em seções colapsáveis.

O formulário de produto deixa o layout de duas colunas e passa a usar
<details>/<summary> para agrupar campos em seções. Cada seção abre e fecha
pelo teclado sem JavaScript. O script só faz uma coisa: abrir a seção que
contém o campo com erro de validação.
"""
from __future__ import annotations

import importlib
import os
import re
import tempfile
import unittest


class Base(unittest.TestCase):
    def setUp(self):
        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-p4-")
        os.environ["MORUMBI_USUARIO"] = "samir"
        os.environ["MORUMBI_SENHA"] = "segredo"
        os.environ["MORUMBI_BIND"] = "127.0.0.1:5000"
        os.environ["MORUMBI_HTTPS"] = "0"
        from sistema import auth, dados
        importlib.reload(dados)
        importlib.reload(auth)
        from sistema import custo, app as modulo
        importlib.reload(custo)
        importlib.reload(modulo)
        self.dados = dados
        self.custo = custo
        self.app = modulo.criar_app()
        self.app.config["TESTING"] = True
        self.cliente = self.app.test_client()
        self.cliente.post("/entrar", data={"usuario": "samir", "senha": "segredo"})

    def _criar_filamento(self, nome="PLA Branco", preco_kg=80):
        return self.dados.salvar_filamento({
            "nome": nome, "cor": "Branco", "tipo": "PLA",
            "preco_kg": str(preco_kg), "estoque_kg": "1",
        }, "samir")

    def _produto_completo(self, filamento_id, situacao="rascunho"):
        return self.dados.salvar_produto({
            "nome": "Peça teste", "sku": "TST-001",
            "filamento_id": str(filamento_id),
            "gramas": "50", "horas": "2", "preco": "45.00",
            "ativo": "1", "situacao": situacao,
        }, "samir")

    def _html_produto(self, prod_id=None):
        url = f"/produtos/{prod_id}" if prod_id else "/produtos/novo"
        r = self.cliente.get(url)
        self.assertEqual(r.status_code, 200)
        return r.data.decode()


SECOES = [
    ("sec-identificacao", "Identificação"),
    ("sec-medidas", "Medidas e arquivo"),
    ("sec-custo", "Custo e preço"),
    ("sec-volume", "Preço por volume"),
    ("sec-insumos", "Insumos da peça"),
    ("sec-publicacao", "Publicação"),
]


class TesteSecoesPresentes(Base):
    """Cada seção tem um <details> com id e um <summary> com o título."""

    def test_produto_novo_tem_seis_secoes(self):
        html = self._html_produto()
        for sec_id, titulo in SECOES:
            with self.subTest(secao=sec_id):
                self.assertIn(f'id="{sec_id}"', html)
                self.assertIn(titulo, html)

    def test_produto_existente_tem_seis_secoes(self):
        fil_id = self._criar_filamento()
        prod_id = self._produto_completo(fil_id)
        html = self._html_produto(prod_id)
        for sec_id, titulo in SECOES:
            with self.subTest(secao=sec_id):
                self.assertIn(f'id="{sec_id}"', html)
                self.assertIn(titulo, html)

    def test_secoes_sao_details(self):
        html = self._html_produto()
        for sec_id, _ in SECOES:
            with self.subTest(secao=sec_id):
                padrao = rf'<details\s+class="secao-produto"\s+id="{sec_id}"'
                self.assertRegex(html, padrao)


class TesteLayoutSemDuasColunas(Base):
    """O formulário de produto não usa mais .duas-colunas."""

    def test_form_produto_sem_duas_colunas(self):
        html = self._html_produto()
        form_match = re.search(r'<form[^>]*id="form-produto"[^>]*>', html)
        self.assertIsNotNone(form_match)
        self.assertNotIn("duas-colunas", form_match.group(0))

    def test_form_produto_sem_coluna_lado(self):
        html = self._html_produto()
        self.assertNotIn("coluna-lado", html)


class TesteSecaoAbertaPorPadrao(Base):
    """Produto novo abre Identificação e Medidas; existente abre Custo e Publicação."""

    def test_novo_abre_identificacao(self):
        html = self._html_produto()
        trecho = re.search(r'id="sec-identificacao"[^>]*>', html)
        self.assertIn("open", trecho.group(0))

    def test_novo_abre_medidas(self):
        html = self._html_produto()
        trecho = re.search(r'id="sec-medidas"[^>]*>', html)
        self.assertIn("open", trecho.group(0))

    def test_existente_abre_custo(self):
        fil_id = self._criar_filamento()
        prod_id = self._produto_completo(fil_id)
        html = self._html_produto(prod_id)
        trecho = re.search(r'id="sec-custo"[^>]*>', html)
        self.assertIn("open", trecho.group(0))

    def test_existente_abre_publicacao(self):
        fil_id = self._criar_filamento()
        prod_id = self._produto_completo(fil_id)
        html = self._html_produto(prod_id)
        trecho = re.search(r'id="sec-publicacao"[^>]*>', html)
        self.assertIn("open", trecho.group(0))


class TesteSecaoErroValida(Base):
    """Tentar publicar sem dados retorna erro dentro da seção certa."""

    def test_erro_publicar_sem_sku_aparece(self):
        fil_id = self._criar_filamento()
        prod_id = self.dados.salvar_produto({"nome": "Teste"}, "samir")
        r = self.cliente.post(f"/produtos/{prod_id}", data={
            "nome": "Teste",
            "filamento_id": str(fil_id),
            "gramas": "50", "horas": "2", "preco": "45.00",
            "situacao": "publicado",
        })
        self.assertEqual(r.status_code, 400)
        html = r.data.decode()
        self.assertIn('id="campo-sku"', html)
        self.assertIn("com-erro", html)

    def test_erro_publicar_sem_filamento_aparece(self):
        prod_id = self.dados.salvar_produto({"nome": "Teste"}, "samir")
        r = self.cliente.post(f"/produtos/{prod_id}", data={
            "nome": "Teste", "sku": "TST-X",
            "gramas": "50", "horas": "2", "preco": "45.00",
            "situacao": "publicado",
        })
        self.assertEqual(r.status_code, 400)
        html = r.data.decode()
        self.assertIn('id="campo-filamento_id"', html)
        self.assertIn("com-erro", html)


class TesteScriptAbreSecao(Base):
    """O JavaScript de auto-abertura de seção com erro está presente."""

    def test_script_abre_secao_com_erro(self):
        html = self._html_produto()
        self.assertIn('closest("details.secao-produto")', html)

    def test_script_procura_campo_com_erro(self):
        html = self._html_produto()
        self.assertIn('.com-erro', html)


class TesteBotaoSalvarForaDasSecoes(Base):
    """O botão Salvar fica fora das seções, dentro do form, sticky no fundo."""

    def test_botao_salvar_presente(self):
        html = self._html_produto()
        self.assertIn('class="acoes principal"', html)
        self.assertIn("Salvar", html)

    def test_botao_voltar_presente(self):
        html = self._html_produto()
        self.assertIn("Voltar", html)


class TesteCamposPresentes(Base):
    """Todos os campos que existiam antes continuam acessíveis."""

    CAMPOS_ESPERADOS = [
        "campo-nome", "campo-sku", "campo-categoria",
        "campo-filamento_id", "campo-impressora_id",
        "campo-minutos", "campo-gramas", "campo-horas",
        "campo-caixa_x", "campo-caixa_y", "campo-caixa_z",
        "campo-preco", "campo-situacao",
    ]

    def test_todos_os_campos_existem(self):
        html = self._html_produto()
        for campo_id in self.CAMPOS_ESPERADOS:
            with self.subTest(campo=campo_id):
                self.assertIn(f'id="{campo_id}"', html)

    def test_campos_existem_em_produto_existente(self):
        fil_id = self._criar_filamento()
        prod_id = self._produto_completo(fil_id)
        html = self._html_produto(prod_id)
        for campo_id in self.CAMPOS_ESPERADOS:
            with self.subTest(campo=campo_id):
                self.assertIn(f'id="{campo_id}"', html)


class TesteDuplicarForaDoForm(Base):
    """O botão Duplicar continua fora do form principal."""

    def test_duplicar_aparece_em_produto_existente(self):
        fil_id = self._criar_filamento()
        prod_id = self._produto_completo(fil_id)
        html = self._html_produto(prod_id)
        self.assertIn("Duplicar produto", html)

    def test_duplicar_nao_aparece_em_novo(self):
        html = self._html_produto()
        self.assertNotIn("Duplicar produto", html)


if __name__ == "__main__":
    unittest.main()
