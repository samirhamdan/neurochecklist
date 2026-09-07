# -*- coding: utf-8 -*-
"""Sprint 2 — clientes e pedidos.

O painel para de so ler. O que estes testes protegem:

1. O PEDIDO NASCE SEM SABER DE ONDE VEIO. Canal, numero no canal, comissao e
   valor liquido entram agora porque um pedido antigo nunca mais teria de
   onde tira-los -- e sem valor liquido o relatorio de vendas mente.
2. O MESMO PEDIDO NAO ENTRA DUAS VEZES. Loja e marketplace reenviam aviso
   quando nao tem resposta; e a falha classica.
3. QUANTIDADE MULTIPLICA A FILA. Seis chaveiros ocupam a mesa de seis, nao
   de um.
4. SITUACAO DE PEDIDO NAO E ETAPA DE PECA. Estavam misturadas: o semeador
   gravava pedido com status "imprimindo".
"""
from __future__ import annotations

import importlib
import os
import tempfile
import unittest
from datetime import date, timedelta


class Base(unittest.TestCase):
    def setUp(self):
        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-ped-")
        from sistema import dados
        importlib.reload(dados)
        self.dados = dados

    def cliente(self, nome="Ana Paula Ribeiro", canal="Instagram"):
        return self.dados.salvar_cliente({"nome": nome, "canal": canal}, "samir")

    def item(self, **kw):
        base = {"descricao": "Topo ANA", "cor": "Rosa", "quantidade": 1,
                "valor_unit": 70.0, "gramas": 83.7, "horas": 5.77}
        base.update(kw)
        return base


class TesteCliente(Base):
    def test_exige_nome(self):
        with self.assertRaises(ValueError):
            self.dados.salvar_cliente({"nome": "  "}, "samir")

    def test_grava_o_autor(self):
        c = self.dados.cliente(self.cliente())
        self.assertEqual(c["criado_por"], "samir")
        self.assertTrue(c["criado_em"])


class TestePedido(Base):
    def test_o_pedido_herda_o_canal_do_cliente(self):
        p = self.dados.pedido(self.dados.salvar_pedido(
            {"cliente_id": self.cliente()}, "samir", itens=[self.item()]))
        self.assertEqual(p["canal"], "Instagram")
        self.assertEqual(p["cliente"], "Ana Paula Ribeiro")

    def test_canal_do_pedido_pode_diferir_do_cliente(self):
        """O cliente do Instagram pode comprar uma vez pela Shopee."""
        p = self.dados.pedido(self.dados.salvar_pedido(
            {"cliente_id": self.cliente(), "canal": "Shopee"}, "samir", itens=[self.item()]))
        self.assertEqual(p["canal"], "Shopee")

    def test_valor_liquido_desconta_a_comissao_do_canal(self):
        self.dados.salvar_comissao("Shopee", 20.0)
        p = self.dados.pedido(self.dados.salvar_pedido(
            {"cliente_id": self.cliente(), "canal": "Shopee"}, "samir",
            itens=[self.item(valor_unit=100.0)]))
        self.assertEqual(p["valor"], 100.0)
        self.assertEqual(p["valor_liquido"], 80.0)

    def test_valor_liquido_fica_gravado_e_nao_muda_depois(self):
        """A taxa do canal muda; o que entrou em marco entrou em marco."""
        self.dados.salvar_comissao("Shopee", 20.0)
        pid = self.dados.salvar_pedido(
            {"cliente_id": self.cliente(), "canal": "Shopee"}, "samir",
            itens=[self.item(valor_unit=100.0)])
        self.dados.salvar_comissao("Shopee", 35.0)
        self.assertEqual(self.dados.pedido(pid)["valor_liquido"], 80.0)

    def test_o_mesmo_numero_do_canal_nao_entra_duas_vezes(self):
        dados_ped = {"cliente_id": self.cliente(), "canal": "Shopee", "id_no_canal": "SHP-9911"}
        self.dados.salvar_pedido(dados_ped, "samir", itens=[self.item()])
        with self.assertRaises(ValueError) as ctx:
            self.dados.salvar_pedido(dados_ped, "samir", itens=[self.item()])
        self.assertIn("SHP-9911", str(ctx.exception))

    def test_numero_repetido_em_canal_diferente_pode(self):
        """Shopee e Mercado Livre numeram do zero, cada um por conta."""
        c = self.cliente()
        self.dados.salvar_pedido({"cliente_id": c, "canal": "Shopee", "id_no_canal": "1001"},
                                 "samir", itens=[self.item()])
        self.dados.salvar_pedido({"cliente_id": c, "canal": "Mercado Livre", "id_no_canal": "1001"},
                                 "samir", itens=[self.item()])
        self.assertEqual(len(self.dados.pedidos()), 2)

    def test_regravar_o_proprio_pedido_nao_reclama_do_proprio_numero(self):
        pid = self.dados.salvar_pedido(
            {"cliente_id": self.cliente(), "canal": "Shopee", "id_no_canal": "SHP-1"},
            "samir", itens=[self.item()])
        self.dados.salvar_pedido(
            {"cliente_id": self.cliente(), "canal": "Shopee", "id_no_canal": "SHP-1"},
            "samir", pid, itens=[self.item()])
        self.assertEqual(len(self.dados.pedidos()), 1)

    def test_situacao_desconhecida_e_recusada(self):
        with self.assertRaises(ValueError):
            self.dados.salvar_pedido({"cliente_id": self.cliente(), "status": "imprimindo"},
                                     "samir", itens=[self.item()])


class TesteFila(Base):
    def test_orcamento_nao_ocupa_a_mesa(self):
        self.dados.salvar_pedido({"cliente_id": self.cliente()}, "samir", itens=[self.item()])
        self.assertEqual(len(self.dados.resumo()["fila"]), 0)

    def test_aprovar_manda_para_a_fila(self):
        pid = self.dados.salvar_pedido({"cliente_id": self.cliente()}, "samir",
                                       itens=[self.item()])
        self.dados.mudar_situacao(pid, "aprovado", "samir")
        fila = self.dados.resumo()["fila"]
        self.assertEqual(len(fila), 1)
        self.assertEqual(fila[0]["cor"], "Rosa")

    def test_aprovar_duas_vezes_nao_duplica_a_peca(self):
        pid = self.dados.salvar_pedido({"cliente_id": self.cliente()}, "samir",
                                       itens=[self.item()])
        self.dados.mudar_situacao(pid, "aprovado", "samir")
        self.dados.mudar_situacao(pid, "aprovado", "samir")
        self.assertEqual(len(self.dados.resumo()["fila"]), 1)

    def test_cancelar_tira_da_fila(self):
        pid = self.dados.salvar_pedido({"cliente_id": self.cliente()}, "samir",
                                       itens=[self.item()])
        self.dados.mudar_situacao(pid, "aprovado", "samir")
        self.dados.mudar_situacao(pid, "cancelado", "samir")
        self.assertEqual(len(self.dados.resumo()["fila"]), 0)

    def test_a_fila_agrupa_por_cor(self):
        """Cada troca de cor custa 6 g de purga."""
        pid = self.dados.salvar_pedido({"cliente_id": self.cliente()}, "samir", itens=[
            self.item(cor="Rosa"), self.item(cor="Preto"), self.item(cor="Rosa")])
        self.dados.mudar_situacao(pid, "aprovado", "samir")
        r = self.dados.resumo()
        self.assertEqual(sorted(r["fila_por_cor"]), ["Preto", "Rosa"])
        self.assertEqual(r["trocas_de_cor"], 1)
        self.assertEqual(r["purga_g"], 6)

    def test_a_cor_mais_urgente_abre_a_fila(self):
        hoje = date.today()
        longe = self.dados.salvar_pedido(
            {"cliente_id": self.cliente(), "prazo": str(hoje + timedelta(days=9))},
            "samir", itens=[self.item(cor="Branco")])
        perto = self.dados.salvar_pedido(
            {"cliente_id": self.cliente("Buffet Estrela"), "prazo": str(hoje - timedelta(days=1))},
            "samir", itens=[self.item(cor="Preto")])
        for p in (longe, perto):
            self.dados.mudar_situacao(p, "aprovado", "samir")
        r = self.dados.resumo()
        self.assertEqual(list(r["fila_por_cor"])[0], "Preto", "a cor atrasada tem que abrir")
        self.assertEqual(len(r["atrasados"]), 1)


class TesteMigracao(Base):
    def test_situacao_de_pedido_que_era_etapa_de_peca(self):
        """O semeador gravava pedido com status 'imprimindo'. Nao e situacao."""
        with self.dados.conectar() as conn:
            conn.executemany(
                "INSERT INTO pedidos (cliente, canal, valor, status, criado_em)"
                " VALUES (?, '', 0, ?, '2026-01-01')",
                [("Carlos", "novo"), ("Ana", "imprimindo"), ("Zeca", "entregue")])
            conn.commit()
        importlib.reload(self.dados)
        por_nome = {p["cliente"]: p["status"]
                    for p in self.dados.pedidos(self.dados.SITUACOES)}
        self.assertEqual(por_nome["Carlos"], "orcamento")
        self.assertEqual(por_nome["Ana"], "aprovado")
        self.assertEqual(por_nome["Zeca"], "entregue")

    def test_cliente_que_era_texto_solto_vira_cadastro(self):
        with self.dados.conectar() as conn:
            conn.execute("DELETE FROM clientes")
            conn.execute(
                "INSERT INTO pedidos (cliente, canal, valor, status, criado_em)"
                " VALUES ('Escola Girassol', 'WhatsApp', 720, 'orcamento', '2026-01-01')")
            conn.commit()
        importlib.reload(self.dados)
        nomes = {c["nome"]: c for c in self.dados.clientes()}
        self.assertIn("Escola Girassol", nomes)
        self.assertEqual(nomes["Escola Girassol"]["canal"], "WhatsApp")
        self.assertEqual(nomes["Escola Girassol"]["criado_por"], "migracao")

    def test_comissao_dos_marketplaces_nasce_em_zero(self):
        """Taxa chutada vira numero errado no relatorio, que e pior que nenhum."""
        por_nome = {c["nome"]: c["comissao"] for c in self.dados.canais()}
        self.assertEqual(por_nome["Shopee"], 0)
        self.assertEqual(por_nome["Mercado Livre"], 0)


class TesteTelas(unittest.TestCase):
    """As telas, e a multiplicacao por quantidade, que mora na rota."""

    def setUp(self):
        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-ped-tela-")
        os.environ["MORUMBI_USUARIO"] = "samir"
        os.environ["MORUMBI_SENHA"] = "segredo"
        os.environ["MORUMBI_BIND"] = "127.0.0.1:5000"
        os.environ["MORUMBI_HTTPS"] = "0"
        from sistema import auth, dados
        importlib.reload(dados); importlib.reload(auth)
        from sistema import app as modulo
        importlib.reload(modulo)
        self.dados = dados
        self.app = modulo.criar_app()
        self.app.config["TESTING"] = True
        self.cliente = self.app.test_client()
        self.cliente.post("/entrar", data={"usuario": "samir", "senha": "segredo"})

        self.cid = dados.salvar_cliente({"nome": "Ana Paula", "canal": "Instagram"}, "samir")
        fil = dados.salvar_filamento({"nome": "PLA Rosa", "cor": "Rosa", "preco_kg": 118}, "samir")
        self.pid = dados.salvar_produto(
            {"nome": "Topo ANA 18cm", "gramas": 83.7, "horas": 5.77, "preco": 70,
             "filamento_id": fil}, "samir")

    def test_todas_as_telas_abrem(self):
        for rota in ("/pedidos", "/pedidos/novo", "/clientes", "/clientes/novo", "/canais"):
            with self.subTest(rota=rota):
                self.assertEqual(self.cliente.get(rota).status_code, 200)

    def test_sem_sessao_nenhuma_abre(self):
        anonimo = self.app.test_client()
        for rota in ("/pedidos", "/clientes", "/canais"):
            with self.subTest(rota=rota):
                self.assertEqual(anonimo.get(rota).status_code, 302)

    def _criar(self, qtd):
        return self.cliente.post("/pedidos/novo", data={
            "cliente_id": str(self.cid), "status": "orcamento",
            "item_produto": str(self.pid), "item_descricao": "Topo ANA 18cm",
            "item_cor": "Rosa", "item_qtd": str(qtd), "item_valor": "70",
        }, follow_redirects=False)

    def test_quantidade_multiplica_peso_e_tempo(self):
        """Seis chaveiros ocupam a mesa de seis, nao de um."""
        self.assertEqual(self._criar(6).status_code, 302)
        item = self.dados.pedido(1)["itens"][0]
        self.assertAlmostEqual(item["gramas_est"], 83.7 * 6, places=1)
        self.assertAlmostEqual(item["horas_est"], 5.77 * 6, places=2)

    def test_o_produto_traz_o_valor_para_a_fila_do_painel(self):
        self._criar(2)
        self.cliente.post("/pedidos/1/situacao", data={"situacao": "aprovado"})
        corpo = self.cliente.get("/").get_data(as_text=True)
        self.assertNotIn("Ainda não há nada", corpo)
        self.assertIn("Ana Paula", corpo)
        self.assertIn("11.5 h", corpo)          # 2 x 5,77

    def test_linha_de_item_vazia_e_descartada(self):
        """O formulario sempre tem uma linha em branco no fim."""
        self.cliente.post("/pedidos/novo", data={
            "cliente_id": str(self.cid), "status": "orcamento",
            "item_produto": ["", ""], "item_descricao": ["Topo", ""],
            "item_cor": ["Rosa", ""], "item_qtd": ["1", "1"], "item_valor": ["70", ""],
        })
        self.assertEqual(len(self.dados.pedido(1)["itens"]), 1)

    def test_pedido_repetido_do_canal_volta_o_formulario_com_o_motivo(self):
        base = {"cliente_id": str(self.cid), "status": "orcamento", "canal": "Shopee",
                "id_no_canal": "SHP-77", "item_produto": str(self.pid),
                "item_descricao": "Topo", "item_cor": "Rosa", "item_qtd": "1",
                "item_valor": "70"}
        self.cliente.post("/pedidos/novo", data=base)
        r = self.cliente.post("/pedidos/novo", data=base)
        self.assertEqual(r.status_code, 400)
        self.assertIn("SHP-77", r.get_data(as_text=True))

    def test_comissao_e_salva_pela_tela_de_canais(self):
        self.cliente.post("/canais", data={"comissao_Shopee": "14.5"})
        por_nome = {c["nome"]: c["comissao"] for c in self.dados.canais()}
        self.assertEqual(por_nome["Shopee"], 14.5)
