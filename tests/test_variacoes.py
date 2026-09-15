# -*- coding: utf-8 -*-
"""Sprint P5 — variações de produto.

Cada produto pode ter variações de cor (filamento diferente), com SKU e
preço opcionais. No catálogo, um produto com variações se expande: cada
variação vira uma entrada separada. Publicar exige filamento e SKU em
todas as variações ativas.
"""
from __future__ import annotations

import importlib
import os
import re
import tempfile
import unittest


class Base(unittest.TestCase):
    def setUp(self):
        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-p5-")
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

    def _criar_filamento(self, nome="PLA Branco", cor="Branco", preco_kg=80):
        return self.dados.salvar_filamento({
            "nome": nome, "cor": cor, "tipo": "PLA",
            "preco_kg": str(preco_kg), "estoque_kg": "1",
        }, "samir")

    def _produto_completo(self, filamento_id, situacao="rascunho"):
        return self.dados.salvar_produto({
            "nome": "Topo ANA", "sku": "TST-001",
            "filamento_id": str(filamento_id),
            "gramas": "50", "horas": "2", "preco": "45.00",
            "ativo": "1", "situacao": situacao,
        }, "samir")


class TesteCrudVariacao(Base):
    """Criar, listar e excluir variações pelo dados.py."""

    def test_salvar_variacao_cria_registro(self):
        fil_id = self._criar_filamento()
        prod_id = self._produto_completo(fil_id)
        var_id = self.dados.salvar_variacao(prod_id, {
            "variacao_filamento_id": str(fil_id),
            "variacao_nome": "Rosa",
            "variacao_sku": "TST-001-RS",
        }, "samir")
        self.assertIsNotNone(var_id)
        variacoes = self.dados.variacoes_do_produto(prod_id)
        self.assertEqual(len(variacoes), 1)
        self.assertEqual(variacoes[0]["nome"], "Rosa")
        self.assertEqual(variacoes[0]["sku"], "TST-001-RS")

    def test_salvar_variacao_sem_filamento_rejeita(self):
        fil_id = self._criar_filamento()
        prod_id = self._produto_completo(fil_id)
        with self.assertRaises(self.dados.ErroDeCampo) as ctx:
            self.dados.salvar_variacao(prod_id, {
                "variacao_nome": "Rosa",
                "variacao_sku": "TST-001-RS",
            }, "samir")
        self.assertEqual(ctx.exception.campo, "variacao_filamento_id")

    def test_excluir_variacao_remove(self):
        fil_id = self._criar_filamento()
        prod_id = self._produto_completo(fil_id)
        var_id = self.dados.salvar_variacao(prod_id, {
            "variacao_filamento_id": str(fil_id),
            "variacao_nome": "Rosa",
            "variacao_sku": "TST-001-RS",
        }, "samir")
        self.dados.excluir_variacao(var_id, prod_id)
        self.assertEqual(len(self.dados.variacoes_do_produto(prod_id)), 0)

    def test_variacao_com_preco_ajustado(self):
        fil_id = self._criar_filamento()
        prod_id = self._produto_completo(fil_id)
        self.dados.salvar_variacao(prod_id, {
            "variacao_filamento_id": str(fil_id),
            "variacao_nome": "Premium",
            "variacao_sku": "TST-001-PM",
            "variacao_preco": "55.00",
        }, "samir")
        variacoes = self.dados.variacoes_do_produto(prod_id)
        self.assertEqual(variacoes[0]["preco_ajuste"], 55.0)

    def test_produto_inclui_variacoes(self):
        fil_id = self._criar_filamento()
        prod_id = self._produto_completo(fil_id)
        self.dados.salvar_variacao(prod_id, {
            "variacao_filamento_id": str(fil_id),
            "variacao_nome": "Rosa",
            "variacao_sku": "TST-001-RS",
        }, "samir")
        prod = self.dados.produto(prod_id)
        self.assertIn("variacoes", prod)
        self.assertEqual(len(prod["variacoes"]), 1)


class TesteValidacaoPublicacao(Base):
    """Variações sem filamento ou SKU impedem a publicação."""

    def test_publicar_com_variacao_sem_sku_rejeita(self):
        fil_id = self._criar_filamento()
        prod_id = self._produto_completo(fil_id)
        self.dados.salvar_variacao(prod_id, {
            "variacao_filamento_id": str(fil_id),
            "variacao_nome": "Rosa",
        }, "samir")
        with self.assertRaises(self.dados.ErroDeCampo) as ctx:
            self.dados.salvar_produto({
                "nome": "Topo ANA", "sku": "TST-001",
                "filamento_id": str(fil_id),
                "gramas": "50", "horas": "2", "preco": "45.00",
                "ativo": "1", "situacao": "publicado",
            }, "samir", prod_id)
        self.assertIn("SKU", str(ctx.exception))

    def test_publicar_com_skus_duplicados_rejeita(self):
        fil_id = self._criar_filamento()
        fil2_id = self._criar_filamento("PLA Rosa", "Rosa")
        prod_id = self._produto_completo(fil_id)
        self.dados.salvar_variacao(prod_id, {
            "variacao_filamento_id": str(fil_id),
            "variacao_nome": "Branco",
            "variacao_sku": "TST-001-A",
        }, "samir")
        self.dados.salvar_variacao(prod_id, {
            "variacao_filamento_id": str(fil2_id),
            "variacao_nome": "Rosa",
            "variacao_sku": "TST-001-A",
        }, "samir")
        with self.assertRaises(self.dados.ErroDeCampo) as ctx:
            self.dados.salvar_produto({
                "nome": "Topo ANA", "sku": "TST-001",
                "filamento_id": str(fil_id),
                "gramas": "50", "horas": "2", "preco": "45.00",
                "ativo": "1", "situacao": "publicado",
            }, "samir", prod_id)
        self.assertIn("duplicado", str(ctx.exception).lower())

    def test_publicar_sem_variacoes_funciona(self):
        fil_id = self._criar_filamento()
        prod_id = self.dados.salvar_produto({
            "nome": "Topo ANA", "sku": "TST-001",
            "filamento_id": str(fil_id),
            "gramas": "50", "horas": "2", "preco": "45.00",
            "ativo": "1", "situacao": "publicado",
        }, "samir")
        prod = self.dados.produto(prod_id)
        self.assertEqual(prod["situacao"], "publicado")


class TesteCatalogoExpandido(Base):
    """No catálogo, variações viram entradas separadas."""

    def test_produto_sem_variacao_aparece_normal(self):
        fil_id = self._criar_filamento()
        self._produto_completo(fil_id, "publicado")
        catalogo = self.dados.produtos_catalogo()
        self.assertEqual(len(catalogo), 1)
        self.assertEqual(catalogo[0]["nome"], "Topo ANA")

    def test_produto_com_variacoes_expande(self):
        fil_id = self._criar_filamento()
        fil2_id = self._criar_filamento("PLA Rosa", "Rosa", 85)
        prod_id = self._produto_completo(fil_id, "publicado")
        self.dados.salvar_variacao(prod_id, {
            "variacao_filamento_id": str(fil_id),
            "variacao_nome": "Branco",
            "variacao_sku": "TST-001-BR",
        }, "samir")
        self.dados.salvar_variacao(prod_id, {
            "variacao_filamento_id": str(fil2_id),
            "variacao_nome": "Rosa",
            "variacao_sku": "TST-001-RS",
        }, "samir")
        catalogo = self.dados.produtos_catalogo()
        self.assertEqual(len(catalogo), 2)
        nomes = [c["nome"] for c in catalogo]
        self.assertIn("Topo ANA — Branco", nomes)
        self.assertIn("Topo ANA — Rosa", nomes)

    def test_variacao_com_preco_ajustado_no_catalogo(self):
        fil_id = self._criar_filamento()
        prod_id = self._produto_completo(fil_id, "publicado")
        self.dados.salvar_variacao(prod_id, {
            "variacao_filamento_id": str(fil_id),
            "variacao_nome": "Premium",
            "variacao_sku": "TST-001-PM",
            "variacao_preco": "65.00",
        }, "samir")
        catalogo = self.dados.produtos_catalogo()
        self.assertEqual(len(catalogo), 1)
        self.assertEqual(catalogo[0]["preco"], 65.0)

    def test_variacao_herda_sku_do_produto_quando_vazio(self):
        fil_id = self._criar_filamento()
        prod_id = self._produto_completo(fil_id, "publicado")
        self.dados.salvar_variacao(prod_id, {
            "variacao_filamento_id": str(fil_id),
            "variacao_nome": "Branco",
            "variacao_sku": "TST-001-BR",
        }, "samir")
        catalogo = self.dados.produtos_catalogo()
        self.assertEqual(catalogo[0]["sku"], "TST-001-BR")


class TesteDuplicacaoComVariacoes(Base):
    """Duplicar um produto copia as variações sem o SKU."""

    def test_duplicar_copia_variacoes(self):
        fil_id = self._criar_filamento()
        prod_id = self._produto_completo(fil_id)
        self.dados.salvar_variacao(prod_id, {
            "variacao_filamento_id": str(fil_id),
            "variacao_nome": "Rosa",
            "variacao_sku": "TST-001-RS",
        }, "samir")
        novo_id = self.dados.duplicar_produto(prod_id, "samir")
        variacoes = self.dados.variacoes_do_produto(novo_id)
        self.assertEqual(len(variacoes), 1)
        self.assertEqual(variacoes[0]["nome"], "Rosa")

    def test_duplicar_nao_copia_sku(self):
        fil_id = self._criar_filamento()
        prod_id = self._produto_completo(fil_id)
        self.dados.salvar_variacao(prod_id, {
            "variacao_filamento_id": str(fil_id),
            "variacao_nome": "Rosa",
            "variacao_sku": "TST-001-RS",
        }, "samir")
        novo_id = self.dados.duplicar_produto(prod_id, "samir")
        variacoes = self.dados.variacoes_do_produto(novo_id)
        self.assertIsNone(variacoes[0]["sku"])


class TesteRotasVariacao(Base):
    """Rotas POST para adicionar e excluir variações."""

    def test_adicionar_variacao_via_rota(self):
        fil_id = self._criar_filamento()
        prod_id = self._produto_completo(fil_id)
        r = self.cliente.post(f"/produtos/{prod_id}/variacoes", data={
            "variacao_filamento_id": str(fil_id),
            "variacao_nome": "Rosa",
            "variacao_sku": "TST-001-RS",
        })
        self.assertEqual(r.status_code, 302)
        variacoes = self.dados.variacoes_do_produto(prod_id)
        self.assertEqual(len(variacoes), 1)

    def test_adicionar_variacao_sem_filamento_retorna_400(self):
        fil_id = self._criar_filamento()
        prod_id = self._produto_completo(fil_id)
        r = self.cliente.post(f"/produtos/{prod_id}/variacoes", data={
            "variacao_nome": "Rosa",
        })
        self.assertEqual(r.status_code, 400)
        html = r.data.decode()
        self.assertIn("campo-variacao_filamento_id", html)
        self.assertIn("com-erro", html)

    def test_excluir_variacao_via_rota(self):
        fil_id = self._criar_filamento()
        prod_id = self._produto_completo(fil_id)
        var_id = self.dados.salvar_variacao(prod_id, {
            "variacao_filamento_id": str(fil_id),
            "variacao_nome": "Rosa",
            "variacao_sku": "TST-001-RS",
        }, "samir")
        r = self.cliente.post(f"/produtos/{prod_id}/variacoes/{var_id}/excluir")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(self.dados.variacoes_do_produto(prod_id)), 0)

    def test_adicionar_variacao_produto_inexistente_404(self):
        r = self.cliente.post("/produtos/9999/variacoes", data={
            "variacao_filamento_id": "1",
            "variacao_nome": "Rosa",
        })
        self.assertEqual(r.status_code, 404)

    def test_excluir_variacao_produto_inexistente_404(self):
        r = self.cliente.post("/produtos/9999/variacoes/1/excluir")
        self.assertEqual(r.status_code, 404)


class TesteSecaoNoTemplate(Base):
    """A seção Variações aparece no formulário de produto."""

    def test_produto_novo_tem_secao_variacoes(self):
        html = self._html_produto()
        self.assertIn('id="sec-variacoes"', html)
        self.assertIn("Variações", html)

    def test_produto_novo_mostra_salve_primeiro(self):
        html = self._html_produto()
        self.assertIn("Salve o produto primeiro", html)

    def test_produto_existente_tem_form_variacao(self):
        fil_id = self._criar_filamento()
        prod_id = self._produto_completo(fil_id)
        html = self._html_produto(prod_id)
        self.assertIn("Adicionar variação", html)
        self.assertIn("variacao_filamento_id", html)

    def test_variacao_existente_aparece_na_secao(self):
        fil_id = self._criar_filamento()
        prod_id = self._produto_completo(fil_id)
        self.dados.salvar_variacao(prod_id, {
            "variacao_filamento_id": str(fil_id),
            "variacao_nome": "Rosa",
            "variacao_sku": "TST-001-RS",
        }, "samir")
        html = self._html_produto(prod_id)
        self.assertIn("Rosa", html)
        self.assertIn("TST-001-RS", html)

    def test_secao_variacoes_e_details(self):
        html = self._html_produto()
        padrao = r'<details\s+class="secao-produto"\s+id="sec-variacoes"'
        self.assertRegex(html, padrao)

    def test_oito_secoes_no_produto(self):
        html = self._html_produto()
        secoes = re.findall(r'class="secao-produto"', html)
        self.assertEqual(len(secoes), 8)

    def _html_produto(self, prod_id=None):
        url = f"/produtos/{prod_id}" if prod_id else "/produtos/novo"
        r = self.cliente.get(url)
        self.assertEqual(r.status_code, 200)
        return r.data.decode()


class TesteListaProdutosComVariacoes(Base):
    """A lista de produtos mostra a contagem de variações."""

    def test_produto_com_variacao_mostra_badge(self):
        fil_id = self._criar_filamento()
        prod_id = self._produto_completo(fil_id)
        self.dados.salvar_variacao(prod_id, {
            "variacao_filamento_id": str(fil_id),
            "variacao_nome": "Rosa",
            "variacao_sku": "TST-001-RS",
        }, "samir")
        r = self.cliente.get("/produtos")
        html = r.data.decode()
        self.assertIn("1 var.", html)

    def test_produto_sem_variacao_sem_badge(self):
        fil_id = self._criar_filamento()
        self._produto_completo(fil_id)
        r = self.cliente.get("/produtos")
        html = r.data.decode()
        self.assertNotIn("0 var.", html)
        import re
        self.assertIsNone(re.search(r'\d+ var\.', html))


if __name__ == "__main__":
    unittest.main()
