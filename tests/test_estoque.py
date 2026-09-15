# -*- coding: utf-8 -*-
"""Sprint P6 — gestão completa de estoque de produtos e matéria-prima.

Cobre: colunas estoque/estoque_minimo em produtos, movimentos de estoque,
alertas consolidados, painel de estoque, tela de movimentações,
ajuste manual, coluna na lista de produtos, e seção no formulário.
"""
from __future__ import annotations

import importlib
import os
import re
import tempfile
import unittest


class Base(unittest.TestCase):
    def setUp(self):
        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-p6-")
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
            "preco_kg": str(preco_kg), "estoque_kg": "1000",
        }, "samir")

    def _criar_produto(self, nome="Peça teste", **kw):
        campos = {"nome": nome, "sku": kw.get("sku", ""), "gramas": "50",
                  "horas": "2", "preco": "45.00", "ativo": "1"}
        campos.update(kw)
        return self.dados.salvar_produto(campos, "samir")

    def _criar_insumo(self, nome="Parafuso M3", quantidade=100, minimo=20):
        return self.dados.salvar_insumo({
            "nome": nome, "unidade": "un",
            "quantidade": str(quantidade), "minimo": str(minimo),
            "valor_manual": "0.10", "descricao": "",
        }, "samir")


class TesteColunaEstoqueProduto(Base):
    """Produto ganha colunas estoque e estoque_minimo."""

    def test_produto_novo_tem_estoque_zero(self):
        prod_id = self._criar_produto()
        prod = self.dados.produto(prod_id)
        self.assertEqual(prod["estoque"], 0)
        self.assertEqual(prod["estoque_minimo"], 0)

    def test_salvar_estoque_minimo(self):
        prod_id = self._criar_produto(estoque_minimo="5")
        prod = self.dados.produto(prod_id)
        self.assertEqual(prod["estoque_minimo"], 5)

    def test_atualizar_estoque_minimo(self):
        prod_id = self._criar_produto()
        self.dados.salvar_produto({"nome": "Peça teste", "estoque_minimo": "10"},
                                  "samir", prod_id)
        prod = self.dados.produto(prod_id)
        self.assertEqual(prod["estoque_minimo"], 10)


class TesteMovimentosProduto(Base):
    """Estoque de produto move por ajuste manual."""

    def test_ajustar_estoque_positivo(self):
        prod_id = self._criar_produto()
        self.dados.ajustar_estoque("produto", prod_id, 10, "produção manual", "samir")
        prod = self.dados.produto(prod_id)
        self.assertEqual(prod["estoque"], 10)

    def test_ajustar_estoque_negativo(self):
        prod_id = self._criar_produto()
        self.dados.ajustar_estoque("produto", prod_id, 10, "entrada", "samir")
        self.dados.ajustar_estoque("produto", prod_id, -3, "venda", "samir")
        prod = self.dados.produto(prod_id)
        self.assertEqual(prod["estoque"], 7)

    def test_ajustar_zero_recusa(self):
        prod_id = self._criar_produto()
        with self.assertRaises(self.dados.ErroDeCampo):
            self.dados.ajustar_estoque("produto", prod_id, 0, "", "samir")

    def test_saldo_confere_com_movimentos(self):
        prod_id = self._criar_produto()
        self.dados.ajustar_estoque("produto", prod_id, 15, "entrada", "samir")
        self.dados.ajustar_estoque("produto", prod_id, -5, "saida", "samir")
        saldo = self.dados.saldo_pelos_movimentos("produto", prod_id)
        prod = self.dados.produto(prod_id)
        self.assertEqual(saldo, prod["estoque"])

    def test_movimentos_do_item(self):
        prod_id = self._criar_produto()
        self.dados.ajustar_estoque("produto", prod_id, 10, "lote", "samir")
        movs = self.dados.movimentos_do_item("produto", prod_id)
        ajustes = [m for m in movs if m["motivo"] == "ajuste"]
        self.assertEqual(len(ajustes), 1)
        self.assertEqual(ajustes[0]["quantidade"], 10)


class TesteAlertasEstoque(Base):
    """Alertas consolidados para todos os tipos abaixo do mínimo."""

    def test_produto_abaixo_do_minimo(self):
        prod_id = self._criar_produto(estoque_minimo="5")
        alertas = self.dados.alertas_estoque()
        ids = [p["id"] for p in alertas["produtos"]]
        self.assertIn(prod_id, ids)

    def test_produto_acima_do_minimo_nao_alerta(self):
        prod_id = self._criar_produto(estoque_minimo="5")
        self.dados.ajustar_estoque("produto", prod_id, 10, "", "samir")
        alertas = self.dados.alertas_estoque()
        ids = [p["id"] for p in alertas["produtos"]]
        self.assertNotIn(prod_id, ids)

    def test_filamento_abaixo_do_minimo(self):
        fil_id = self.dados.salvar_filamento({
            "nome": "PLA Teste", "cor": "Preto", "tipo": "PLA",
            "preco_kg": "80", "estoque_kg": "100", "minimo": "500",
        }, "samir")
        alertas = self.dados.alertas_estoque()
        ids = [f["id"] for f in alertas["filamentos"]]
        self.assertIn(fil_id, ids)

    def test_insumo_abaixo_do_minimo(self):
        ins_id = self._criar_insumo(quantidade=5, minimo=20)
        alertas = self.dados.alertas_estoque()
        ids = [i["id"] for i in alertas["insumos"]]
        self.assertIn(ins_id, ids)

    def test_total_conta_todos(self):
        self._criar_produto(estoque_minimo="5")
        self._criar_insumo(quantidade=5, minimo=20)
        alertas = self.dados.alertas_estoque()
        self.assertGreaterEqual(alertas["total"], 2)


class TesteMovimentosRecentes(Base):
    """Movimentos recentes exclui iniciais e traz nome do item."""

    def test_ajuste_aparece_em_recentes(self):
        prod_id = self._criar_produto()
        self.dados.ajustar_estoque("produto", prod_id, 5, "teste", "samir")
        recentes = self.dados.movimentos_recentes(10)
        nomes = [m["nome_item"] for m in recentes]
        self.assertIn("Peça teste", nomes)

    def test_iniciais_nao_aparecem(self):
        self._criar_produto()
        recentes = self.dados.movimentos_recentes(100)
        motivos = [m["motivo"] for m in recentes]
        self.assertNotIn("inicial", motivos)


class TesteRotaEstoque(Base):
    """Rotas do painel de estoque e movimentações."""

    def test_painel_estoque_200(self):
        r = self.cliente.get("/estoque")
        self.assertEqual(r.status_code, 200)

    def test_painel_estoque_mostra_alertas(self):
        self._criar_produto(nome="Widget", estoque_minimo="5")
        r = self.cliente.get("/estoque")
        html = r.data.decode()
        self.assertIn("Widget", html)
        self.assertIn("Abaixo do mínimo", html)

    def test_painel_estoque_vazio_sem_alerta(self):
        r = self.cliente.get("/estoque")
        html = r.data.decode()
        self.assertIn("Tudo acima do mínimo", html)

    def test_movimentos_produto_200(self):
        prod_id = self._criar_produto()
        r = self.cliente.get(f"/estoque/produto/{prod_id}/movimentos")
        self.assertEqual(r.status_code, 200)
        html = r.data.decode()
        self.assertIn("Peça teste", html)

    def test_movimentos_filamento_200(self):
        fil_id = self._criar_filamento()
        r = self.cliente.get(f"/estoque/filamento/{fil_id}/movimentos")
        self.assertEqual(r.status_code, 200)

    def test_movimentos_tipo_invalido_404(self):
        r = self.cliente.get("/estoque/banana/1/movimentos")
        self.assertEqual(r.status_code, 404)

    def test_movimentos_id_inexistente_404(self):
        r = self.cliente.get("/estoque/produto/9999/movimentos")
        self.assertEqual(r.status_code, 404)

    def test_ajustar_estoque_post(self):
        prod_id = self._criar_produto()
        r = self.cliente.post(f"/estoque/produto/{prod_id}/ajustar",
                              data={"quantidade": "10", "observacao": "entrada"})
        self.assertEqual(r.status_code, 302)
        prod = self.dados.produto(prod_id)
        self.assertEqual(prod["estoque"], 10)

    def test_ajustar_estoque_negativo_post(self):
        prod_id = self._criar_produto()
        self.dados.ajustar_estoque("produto", prod_id, 20, "", "samir")
        r = self.cliente.post(f"/estoque/produto/{prod_id}/ajustar",
                              data={"quantidade": "-5", "observacao": "saída"})
        self.assertEqual(r.status_code, 302)
        prod = self.dados.produto(prod_id)
        self.assertEqual(prod["estoque"], 15)


class TesteListaProdutosEstoque(Base):
    """Lista de produtos mostra coluna Estoque."""

    def test_coluna_estoque_presente(self):
        fil_id = self._criar_filamento()
        self._criar_produto(filamento_id=str(fil_id))
        r = self.cliente.get("/produtos")
        html = r.data.decode()
        self.assertIn('Estoque', html)
        self.assertIn('0 un', html)

    def test_estoque_com_alerta(self):
        fil_id = self._criar_filamento()
        prod_id = self._criar_produto(filamento_id=str(fil_id), estoque_minimo="5")
        r = self.cliente.get("/produtos")
        html = r.data.decode()
        self.assertIn('alerta', html)


class TesteSecaoEstoqueNoProduto(Base):
    """Formulário de produto tem seção de estoque."""

    def test_secao_estoque_existe(self):
        r = self.cliente.get("/produtos/novo")
        html = r.data.decode()
        self.assertIn('id="sec-estoque"', html)

    def test_secao_estoque_eh_details(self):
        r = self.cliente.get("/produtos/novo")
        html = r.data.decode()
        padrao = r'<details\s+class="secao-produto"\s+id="sec-estoque"'
        self.assertRegex(html, padrao)

    def test_oito_secoes(self):
        r = self.cliente.get("/produtos/novo")
        html = r.data.decode()
        secoes = re.findall(r'class="secao-produto"', html)
        self.assertEqual(len(secoes), 8)

    def test_campo_estoque_minimo(self):
        r = self.cliente.get("/produtos/novo")
        html = r.data.decode()
        self.assertIn('name="estoque_minimo"', html)

    def test_produto_existente_mostra_saldo(self):
        prod_id = self._criar_produto()
        self.dados.ajustar_estoque("produto", prod_id, 12, "", "samir")
        r = self.cliente.get(f"/produtos/{prod_id}")
        html = r.data.decode()
        self.assertIn("12 un", html)

    def test_link_movimentacoes(self):
        prod_id = self._criar_produto()
        r = self.cliente.get(f"/produtos/{prod_id}")
        html = r.data.decode()
        self.assertIn(f"/estoque/produto/{prod_id}/movimentos", html)


class TesteMenuEstoque(Base):
    """Item Estoque aparece no menu."""

    def test_menu_tem_estoque(self):
        r = self.cliente.get("/estoque")
        html = r.data.decode()
        self.assertIn("Estoque", html)


class TesteNomeDoItem(Base):
    """nome_do_item retorna o nome correto para cada tipo."""

    def test_nome_filamento(self):
        fil_id = self._criar_filamento("PLA Azul")
        self.assertEqual(self.dados.nome_do_item("filamento", fil_id), "PLA Azul")

    def test_nome_produto(self):
        prod_id = self._criar_produto("Cubo")
        self.assertEqual(self.dados.nome_do_item("produto", prod_id), "Cubo")

    def test_nome_insumo(self):
        ins_id = self._criar_insumo("Imã 5mm")
        self.assertEqual(self.dados.nome_do_item("insumo", ins_id), "Imã 5mm")

    def test_tipo_invalido(self):
        self.assertIsNone(self.dados.nome_do_item("banana", 1))


if __name__ == "__main__":
    unittest.main()
