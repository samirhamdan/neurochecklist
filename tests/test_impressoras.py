# -*- coding: utf-8 -*-
"""Sprint P1 — impressoras e custo por maquina.

Ate aqui o custo de maquina era um parametro global: toda peca pagava o mesmo
R$/h, mesmo que uma impressora custasse o triplo da outra. Com o cadastro de
impressoras, cada produto pode apontar para a maquina que o imprime e ter o
custo real daquela maquina.

O fallback e intencional: produto sem impressora vinculada continua usando o
parametro global, sem que nenhum custo existente mude.
"""
from __future__ import annotations

import importlib
import os
import tempfile
import unittest


class Base(unittest.TestCase):
    def setUp(self):
        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-imp-")
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


class TesteMigracao(Base):
    def test_tabela_impressoras_existe(self):
        with self.dados.conectar() as conn:
            tabelas = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'")}
        self.assertIn("impressoras", tabelas)

    def test_produto_tem_impressora_id(self):
        with self.dados.conectar() as conn:
            colunas = {r[1] for r in conn.execute("PRAGMA table_info(produtos)")}
        self.assertIn("impressora_id", colunas)


class TesteCadastroImpressora(Base):
    def test_criar_impressora(self):
        id_ = self.dados.salvar_impressora(
            {"nome": "Bambu A1 Mini", "modelo": "A1 Mini", "custo_hora": "3.50"}, "samir")
        imp = self.dados.impressora(id_)
        self.assertEqual(imp["nome"], "Bambu A1 Mini")
        self.assertEqual(imp["modelo"], "A1 Mini")
        self.assertAlmostEqual(imp["custo_hora"], 3.50)

    def test_editar_impressora(self):
        id_ = self.dados.salvar_impressora({"nome": "Teste"}, "samir")
        self.dados.salvar_impressora(
            {"nome": "Teste Editada", "custo_hora": "5.00"}, "samir", id_)
        imp = self.dados.impressora(id_)
        self.assertEqual(imp["nome"], "Teste Editada")
        self.assertAlmostEqual(imp["custo_hora"], 5.00)

    def test_nome_obrigatorio(self):
        with self.assertRaises(ValueError) as ctx:
            self.dados.salvar_impressora({"nome": ""}, "samir")
        self.assertIn("nome", getattr(ctx.exception, "campo", ""))

    def test_listar_impressoras(self):
        self.dados.salvar_impressora({"nome": "A"}, "samir")
        self.dados.salvar_impressora({"nome": "B", "ativo": "0"}, "samir")
        self.assertEqual(len(self.dados.impressoras(so_ativas=True)), 1)
        self.assertEqual(len(self.dados.impressoras(so_ativas=False)), 2)

    def test_impressora_com_volume(self):
        id_ = self.dados.salvar_impressora(
            {"nome": "A1", "volume_x": "256", "volume_y": "256", "volume_z": "256"}, "samir")
        imp = self.dados.impressora(id_)
        self.assertAlmostEqual(imp["volume_x"], 256.0)
        self.assertAlmostEqual(imp["volume_y"], 256.0)
        self.assertAlmostEqual(imp["volume_z"], 256.0)


class TesteCustoComImpressora(Base):
    def setUp(self):
        super().setUp()
        self.param = self.dados.parametros()
        fil_id = self.dados.salvar_filamento(
            {"nome": "PLA Preto", "cor": "Preto", "preco_kg": "120"}, "samir")
        self.imp_id = self.dados.salvar_impressora(
            {"nome": "A1 Mini", "custo_hora": "5.00"}, "samir")
        self.prod_id = self.dados.salvar_produto(
            {"nome": "Cubo", "gramas": "30", "horas": "2",
             "filamento_id": str(fil_id), "impressora_id": str(self.imp_id)}, "samir")

    def test_produto_com_impressora_usa_custo_dela(self):
        prod = self.dados.produto(self.prod_id)
        conta = self.custo.conta_de_produto(prod, self.param)
        self.assertAlmostEqual(conta.custo_maquina, 2 * 5.00)

    def test_produto_sem_impressora_usa_parametro_global(self):
        prod_id = self.dados.salvar_produto(
            {"nome": "Outro", "gramas": "30", "horas": "2"}, "samir")
        prod = self.dados.produto(prod_id)
        conta = self.custo.conta_de_produto(prod, self.param)
        self.assertAlmostEqual(conta.custo_maquina,
                               2 * self.param["custo_hora_maquina"])

    def test_calcular_com_custo_hora_explicito(self):
        conta = self.custo.calcular(30, 2, 120.0, param=self.param,
                                    custo_hora_maquina=7.50)
        self.assertAlmostEqual(conta.custo_maquina, 2 * 7.50)

    def test_calcular_sem_custo_hora_usa_global(self):
        conta = self.custo.calcular(30, 2, 120.0, param=self.param)
        self.assertAlmostEqual(conta.custo_maquina,
                               2 * self.param["custo_hora_maquina"])


class TesteRotas(Base):
    def test_lista_impressoras(self):
        r = self.cliente.get("/impressoras")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Impressoras", r.get_data(as_text=True))

    def test_nova_impressora_formulario(self):
        r = self.cliente.get("/impressoras/nova")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Nova impressora", r.get_data(as_text=True))

    def test_criar_por_formulario(self):
        r = self.cliente.post("/impressoras/nova",
                              data={"nome": "Bambu A1", "custo_hora": "3.50"},
                              follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn("Bambu A1", r.get_data(as_text=True))

    def test_editar_por_formulario(self):
        id_ = self.dados.salvar_impressora({"nome": "Teste"}, "samir")
        r = self.cliente.get(f"/impressoras/{id_}")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Teste", r.get_data(as_text=True))

    def test_404_impressora_inexistente(self):
        r = self.cliente.get("/impressoras/9999")
        self.assertEqual(r.status_code, 404)

    def test_lista_vazia(self):
        corpo = self.cliente.get("/impressoras").get_data(as_text=True)
        self.assertIn("Nenhuma impressora cadastrada", corpo)

    def test_nome_vazio_retorna_400(self):
        r = self.cliente.post("/impressoras/nova", data={"nome": ""})
        self.assertEqual(r.status_code, 400)


class TesteProdutoComImpressora(Base):
    def test_produto_exibe_impressora_na_ficha(self):
        imp_id = self.dados.salvar_impressora(
            {"nome": "A1 Mini", "custo_hora": "3.50"}, "samir")
        prod_id = self.dados.salvar_produto(
            {"nome": "Cubo", "impressora_id": str(imp_id)}, "samir")
        corpo = self.cliente.get(f"/produtos/{prod_id}").get_data(as_text=True)
        self.assertIn("A1 Mini", corpo)

    def test_editar_produto_mostra_impressora(self):
        imp_id = self.dados.salvar_impressora(
            {"nome": "A1 Mini", "custo_hora": "3.50"}, "samir")
        prod_id = self.dados.salvar_produto(
            {"nome": "Cubo", "impressora_id": str(imp_id)}, "samir")
        corpo = self.cliente.get(f"/produtos/{prod_id}").get_data(as_text=True)
        self.assertIn("A1 Mini", corpo)

    def test_salvar_produto_com_impressora(self):
        imp_id = self.dados.salvar_impressora({"nome": "A1"}, "samir")
        prod_id = self.dados.salvar_produto(
            {"nome": "Peça", "impressora_id": str(imp_id)}, "samir")
        prod = self.dados.produto(prod_id)
        self.assertEqual(prod["impressora_id"], imp_id)
        self.assertEqual(prod["impressora_nome"], "A1")

    def test_produto_sem_impressora(self):
        prod_id = self.dados.salvar_produto({"nome": "Peça"}, "samir")
        prod = self.dados.produto(prod_id)
        self.assertIsNone(prod["impressora_id"])
        self.assertIsNone(prod["impressora_nome"])


class TesteMenuImpressoras(Base):
    def test_menu_tem_impressoras(self):
        corpo = self.cliente.get("/").get_data(as_text=True)
        self.assertIn("Impressoras", corpo)
        self.assertIn("impressoras", corpo)


if __name__ == "__main__":
    unittest.main()
