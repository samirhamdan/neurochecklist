# -*- coding: utf-8 -*-
"""Sprint 3 — o quadro de producao e o estoque que anda com ele.

A decisao de fundo: o estoque NAO e alterado direto. Cada mudanca vira um
MOVIMENTO, e o saldo e a soma deles. A coluna `gramas` do filamento e um
cache disso. Tres coisas vem de graca com isso:

  * voltar a peca uma etapa devolve o material sem precisar adivinhar
    quanto foi tirado -- basta apagar a baixa;
  * o relatorio de filamento gasto (sprint 7) sai da propria tabela;
  * da para PROVAR que o cache nao desandou, em vez de torcer.

E o banco -- nao a ordem em que as telas chamam -- garante que uma peca so
tem uma baixa de producao: e um indice unico parcial.
"""
from __future__ import annotations

import importlib
import os
import tempfile
import unittest


class Base(unittest.TestCase):
    def setUp(self):
        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-prod-")
        from sistema import dados
        importlib.reload(dados)
        self.d = dados
        self.fil = dados.salvar_filamento(
            {"nome": "PLA Rosa", "cor": "Rosa", "gramas": 1000, "preco_kg": 118}, "samir")
        self.ins = dados.salvar_insumo(
            {"nome": "Imã 8mm", "quantidade": 100, "valor_unit": 0.35}, "samir")
        self.prod = dados.salvar_produto(
            {"nome": "Topo ANA", "gramas": 83.7, "horas": 5.77, "filamento_id": self.fil},
            "samir", vinculos=[(self.ins, 2)])
        cli = dados.salvar_cliente({"nome": "Ana", "canal": "Instagram"}, "samir")
        self.ped = dados.salvar_pedido({"cliente_id": cli}, "samir", itens=[{
            "produto_id": self.prod, "descricao": "Topo ANA", "cor": "Rosa",
            "quantidade": 1, "valor_unit": 70, "gramas": 83.7, "horas": 5.77}])
        dados.mudar_situacao(self.ped, "aprovado", "samir")
        self.peca = dados.pedido(self.ped)["itens"][0]["id"]

    def gramas(self):
        return self.d.filamento(self.fil)["gramas"]

    def imas(self):
        return self.d.insumo(self.ins)["quantidade"]

    def conferir_cache(self):
        """O invariante: a coluna e a soma dos movimentos. Sempre."""
        self.assertAlmostEqual(self.gramas(),
                               self.d.saldo_pelos_movimentos("filamento", self.fil), places=3)
        self.assertAlmostEqual(self.imas(),
                               self.d.saldo_pelos_movimentos("insumo", self.ins), places=3)


class TesteBaixaDeEstoque(Base):
    def test_entrar_em_producao_baixa_o_peso_exato(self):
        self.d.mover_peca(self.peca, "imprimindo", "samir")
        self.assertAlmostEqual(self.gramas(), 1000 - 83.7, places=1)
        self.assertEqual(self.imas(), 98)
        self.conferir_cache()

    def test_aguardando_nao_baixa_nada(self):
        self.assertEqual(self.gramas(), 1000)

    def test_mover_duas_vezes_para_producao_nao_baixa_duas_vezes(self):
        """Garantido por indice unico no banco, e nao pela ordem das chamadas."""
        self.d.mover_peca(self.peca, "imprimindo", "samir")
        self.d.mover_peca(self.peca, "montagem", "samir")
        self.d.mover_peca(self.peca, "imprimindo", "samir")
        self.assertAlmostEqual(self.gramas(), 1000 - 83.7, places=1)
        self.conferir_cache()

    def test_avancar_alem_da_producao_nao_baixa_de_novo(self):
        for etapa in ("imprimindo", "montagem", "a entregar", "entregue"):
            self.d.mover_peca(self.peca, etapa, "samir")
        self.assertAlmostEqual(self.gramas(), 1000 - 83.7, places=1)
        self.conferir_cache()

    def test_voltar_para_aguardando_devolve_o_material(self):
        self.d.mover_peca(self.peca, "imprimindo", "samir")
        self.d.mover_peca(self.peca, "aguardando", "samir")
        self.assertEqual(self.gramas(), 1000)
        self.assertEqual(self.imas(), 100)
        self.conferir_cache()

    def test_ida_e_volta_nao_conta_como_consumo(self):
        """Senao o relatorio de filamento gasto acusaria gasto que nao houve."""
        self.d.mover_peca(self.peca, "imprimindo", "samir")
        self.d.mover_peca(self.peca, "aguardando", "samir")
        with self.d.conectar() as conn:
            n = conn.execute("SELECT COUNT(*) c FROM movimentos WHERE motivo = 'producao'"
                             ).fetchone()["c"]
        self.assertEqual(n, 0)

    def test_pular_direto_para_entregue_baixa_uma_vez(self):
        self.d.mover_peca(self.peca, "entregue", "samir")
        self.assertAlmostEqual(self.gramas(), 1000 - 83.7, places=1)
        self.conferir_cache()

    def test_quantidade_multiplica_o_insumo(self):
        """Peso ja vem multiplicado do pedido; o insumo multiplica aqui."""
        cli = self.d.salvar_cliente({"nome": "Buffet"}, "samir")
        ped = self.d.salvar_pedido({"cliente_id": cli}, "samir", itens=[{
            "produto_id": self.prod, "descricao": "Topo", "cor": "Rosa",
            "quantidade": 5, "valor_unit": 70, "gramas": 83.7 * 5, "horas": 28.85}])
        self.d.mudar_situacao(ped, "aprovado", "samir")
        peca = self.d.pedido(ped)["itens"][0]["id"]
        self.d.mover_peca(peca, "imprimindo", "samir")
        self.assertEqual(self.imas(), 100 - 10)

    def test_peca_de_cor_sem_filamento_nao_estoura(self):
        cli = self.d.salvar_cliente({"nome": "X"}, "samir")
        ped = self.d.salvar_pedido({"cliente_id": cli}, "samir", itens=[{
            "descricao": "Peça dourada", "cor": "Dourado", "quantidade": 1,
            "valor_unit": 40, "gramas": 50, "horas": 2}])
        self.d.mudar_situacao(ped, "aprovado", "samir")
        peca = self.d.pedido(ped)["itens"][0]["id"]
        self.d.mover_peca(peca, "imprimindo", "samir")   # nao pode levantar
        self.assertEqual(self.gramas(), 1000)


class TesteRefugo(Base):
    def test_refugo_mantem_a_perda_e_libera_a_reimpressao(self):
        self.d.mover_peca(self.peca, "imprimindo", "samir")
        self.d.registrar_refugo(self.peca, "samir", "entupiu o bico")
        self.assertAlmostEqual(self.gramas(), 1000 - 83.7, places=1,
                               msg="o material perdido nao volta")
        self.d.mover_peca(self.peca, "imprimindo", "samir")
        self.assertAlmostEqual(self.gramas(), 1000 - 83.7 * 2, places=1,
                               msg="a reimpressao consome de novo")
        self.conferir_cache()

    def test_a_peca_volta_para_aguardando(self):
        self.d.mover_peca(self.peca, "imprimindo", "samir")
        self.d.registrar_refugo(self.peca, "samir", "descolou")
        with self.d.conectar() as conn:
            etapa = conn.execute("SELECT status FROM pecas WHERE id = ?",
                                 (self.peca,)).fetchone()["status"]
        self.assertEqual(etapa, "aguardando", "o cliente continua querendo a peca")

    def test_refugo_vira_perda_e_nao_consumo(self):
        """O relatorio de perda de material le por este motivo."""
        self.d.mover_peca(self.peca, "imprimindo", "samir")
        self.d.registrar_refugo(self.peca, "samir", "warp")
        with self.d.conectar() as conn:
            motivos = [r["motivo"] for r in conn.execute(
                "SELECT motivo FROM movimentos WHERE peca_id = ?", (self.peca,))]
        self.assertIn("refugo", motivos)
        self.assertNotIn("producao", motivos)

    def test_refugo_antes_da_producao_tambem_registra_a_perda(self):
        self.d.registrar_refugo(self.peca, "samir", "quebrou ao tirar da mesa")
        self.assertAlmostEqual(self.gramas(), 1000 - 83.7, places=1)
        self.conferir_cache()

    def test_dois_refugos_na_mesma_peca(self):
        for tentativa in ("entupiu", "descolou"):
            self.d.mover_peca(self.peca, "imprimindo", "samir")
            self.d.registrar_refugo(self.peca, "samir", tentativa)
        self.assertAlmostEqual(self.gramas(), 1000 - 83.7 * 2, places=1)
        self.conferir_cache()


class TesteHistorico(Base):
    def test_cada_movimento_fica_com_autor_e_hora(self):
        self.d.mover_peca(self.peca, "imprimindo", "samir")
        self.d.mover_peca(self.peca, "montagem", "ana")
        h = self.d.historico_da_peca(self.peca)
        self.assertEqual([(x["de"], x["para"], x["criado_por"]) for x in h],
                         [("aguardando", "imprimindo", "samir"),
                          ("imprimindo", "montagem", "ana")])
        self.assertTrue(all(x["criado_em"] for x in h))

    def test_o_refugo_aparece_no_historico_com_o_motivo(self):
        self.d.mover_peca(self.peca, "imprimindo", "samir")
        self.d.registrar_refugo(self.peca, "samir", "entupiu o bico")
        self.assertIn("entupiu o bico", self.d.historico_da_peca(self.peca)[-1]["observacao"])

    def test_mover_para_a_mesma_etapa_nao_polui_o_historico(self):
        self.d.mover_peca(self.peca, "imprimindo", "samir")
        self.d.mover_peca(self.peca, "imprimindo", "samir")
        self.assertEqual(len(self.d.historico_da_peca(self.peca)), 1)

    def test_etapa_desconhecida_e_recusada(self):
        with self.assertRaises(ValueError):
            self.d.mover_peca(self.peca, "pintando", "samir")


class TesteAjusteManual(Base):
    def test_mexer_no_estoque_pela_tela_vira_movimento(self):
        """Senao o saldo deixa de ser a soma e o relatorio mente em silencio."""
        self.d.salvar_filamento(
            {"nome": "PLA Rosa", "cor": "Rosa", "gramas": 1500, "preco_kg": 118},
            "samir", self.fil)
        self.assertEqual(self.gramas(), 1500)
        self.conferir_cache()


class TesteTela(unittest.TestCase):
    def setUp(self):
        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-prod-tela-")
        os.environ["MORUMBI_USUARIO"] = "samir"
        os.environ["MORUMBI_SENHA"] = "segredo"
        os.environ["MORUMBI_BIND"] = "127.0.0.1:5000"
        os.environ["MORUMBI_HTTPS"] = "0"
        from sistema import auth, dados
        importlib.reload(dados); importlib.reload(auth)
        from sistema import app as modulo
        importlib.reload(modulo)
        self.d = dados
        self.app = modulo.criar_app()
        self.app.config["TESTING"] = True
        self.cliente = self.app.test_client()
        self.cliente.post("/entrar", data={"usuario": "samir", "senha": "segredo"})
        self.fil = dados.salvar_filamento(
            {"nome": "PLA Rosa", "cor": "Rosa", "gramas": 1000, "preco_kg": 118}, "samir")
        cli = dados.salvar_cliente({"nome": "Ana"}, "samir")
        ped = dados.salvar_pedido({"cliente_id": cli}, "samir", itens=[
            {"descricao": "Topo ANA", "cor": "Rosa", "quantidade": 1, "valor_unit": 70,
             "gramas": 83.7, "horas": 5.77},
            {"descricao": "Chaveiro", "cor": "Rosa", "quantidade": 6, "valor_unit": 25,
             "gramas": 54, "horas": 2.4}])
        dados.mudar_situacao(ped, "aprovado", "samir")
        self.pecas = [i["id"] for i in dados.pedido(ped)["itens"]]

    def test_a_tela_abre_com_as_cinco_etapas(self):
        corpo = self.cliente.get("/producao").get_data(as_text=True)
        self.assertEqual(self.cliente.get("/producao").status_code, 200)
        for rotulo in ("Aguardando", "Em produção", "Montagem", "À entregar", "Entregue"):
            self.assertIn(rotulo, corpo)

    def test_sem_sessao_nao_abre_nem_move(self):
        anonimo = self.app.test_client()
        self.assertEqual(anonimo.get("/producao").status_code, 302)
        r = anonimo.post("/producao/mover", data={"peca": "1", "para": "imprimindo"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.d.filamento(self.fil)["gramas"], 1000)

    def test_mover_varias_de_uma_vez_pela_lista(self):
        r = self.cliente.post("/producao/mover", data={
            "peca": [str(p) for p in self.pecas], "para": "imprimindo"})
        self.assertEqual(r.status_code, 302)
        self.assertAlmostEqual(self.d.filamento(self.fil)["gramas"], 1000 - 83.7 - 54,
                               places=1)

    def test_arrastar_devolve_json(self):
        r = self.cliente.post("/producao/mover", data={
            "peca": str(self.pecas[0]), "para": "imprimindo", "json": "1"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["movidas"], 1)

    def test_refugo_pela_tela(self):
        self.cliente.post("/producao/mover", data={"peca": str(self.pecas[0]),
                                                   "para": "imprimindo"})
        r = self.cliente.post("/producao/refugo", data={"peca": str(self.pecas[0]),
                                                       "motivo": "entupiu"})
        self.assertEqual(r.status_code, 302)
        self.assertIn("entupiu", self.d.historico_da_peca(self.pecas[0])[-1]["observacao"])
