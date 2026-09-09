# -*- coding: utf-8 -*-
"""Sprint 4 -- a compra e o que faz o custo deixar de ser chute.

Ate aqui o preco do kg era digitado a mao: um numero que alguem lembrou.
Agora ele vem da NOTA. Tres coisas precisam ser verdade, e sao o que este
arquivo cobra:

  * lancar uma compra corrige o custo de TODO produto que usa aquele
    filamento -- senao a compra e so papel;
  * a compra continua no historico depois que o preco muda -- o registro do
    que aconteceu nao pode sumir porque o numero de hoje e outro;
  * o estoque somado das compras bate com o saldo do painel -- a entrada
    passa pelo mesmo livro de movimentos da sprint 3, nao por fora dele.

E o caso que so apareceu quando eu apaguei uma compra: o preco ficava o dela.
Um numero de um registro que NAO EXISTE MAIS, com cara de numero conferido.
Por isso sao duas colunas -- o digitado a mao e o efetivo -- e por isso existe
a escada do TesteEscadaDoPreco.
"""
from __future__ import annotations

import importlib
import re
import os
import tempfile
import unittest


class Base(unittest.TestCase):
    def setUp(self):
        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-compras-")
        from sistema import dados
        importlib.reload(dados)
        self.d = dados
        self.fil = dados.salvar_filamento(
            {"nome": "PLA Rosa", "cor": "Rosa", "gramas": 200, "preco_kg": 118}, "samir")
        self.ins = dados.salvar_insumo(
            {"nome": "Ima 8mm", "quantidade": 100, "valor_unit": 0.35}, "samir")

    def comprar(self, **campos):
        itens = campos.pop("itens")
        return self.d.salvar_compra(
            {"data": "2026-09-01", "fornecedor": "3D Fila", **campos}, "samir", itens=itens)

    def rolo(self, gramas=3000, valor=285.0):
        return {"tipo": "filamento", "alvo_id": self.fil,
                "quantidade": gramas, "valor": valor}

    def preco_kg(self):
        return self.d.filamento(self.fil)["preco_kg"]


class TesteOCustoAndaComACompra(Base):
    """A promessa do sprint: a nota entra, o custo do produto se corrige."""

    def setUp(self):
        super().setUp()
        self.prod = self.d.salvar_produto(
            {"nome": "Topo ANA", "gramas": 83.7, "horas": 5.77, "filamento_id": self.fil},
            "samir", vinculos=[(self.ins, 2)])

    def custo(self):
        """Pela mesma porta da tela: o preco vem do filamento ligado ao produto."""
        from sistema import custo as modulo
        p = self.d.produto(self.prod)
        insumos = sum(v["quantidade"] * v["valor_unit"] for v in p["insumos"])
        conta = modulo.calcular(p["gramas"], p["horas"], p["filamento_preco_kg"],
                                insumos, p.get("minutos"), param=self.d.parametros())
        self.assertTrue(conta.completo, "sem preco de kg a conta nem devia fechar")
        return conta.custo

    def test_compra_mais_barata_derruba_o_custo_do_produto(self):
        antes = self.custo()
        self.comprar(itens=[self.rolo()])          # 3 kg por R$ 285 = R$ 95/kg
        depois = self.custo()
        self.assertLess(depois, antes)
        # 83,7 g caindo de R$ 118 para R$ 95 o kg: 23 * 0,0837 = R$ 1,92, mais
        # os 10% de reserva de falha que incidem sobre ela -> R$ 2,11.
        self.assertAlmostEqual(antes - depois, 2.11, delta=0.01)

    def test_compra_mais_cara_sobe_o_custo(self):
        self.comprar(itens=[self.rolo()])
        barato = self.custo()
        self.comprar(data="2026-09-05", itens=[self.rolo(1000, 130.0)])
        self.assertGreater(self.custo(), barato)

    def test_corrige_todo_produto_que_usa_o_filamento(self):
        outro = self.d.salvar_produto(
            {"nome": "Chaveiro", "gramas": 9, "horas": 0.4, "filamento_id": self.fil}, "samir")
        self.comprar(itens=[self.rolo()])
        self.assertAlmostEqual(self.d.produto(outro)["filamento_preco_kg"], 95.0, places=2)

    def test_produto_de_outro_filamento_nao_se_mexe(self):
        verde = self.d.salvar_filamento(
            {"nome": "PLA Verde", "cor": "Verde", "gramas": 500, "preco_kg": 140}, "samir")
        alheio = self.d.salvar_produto(
            {"nome": "Vaso", "gramas": 120, "horas": 6, "filamento_id": verde}, "samir")
        self.comprar(itens=[self.rolo()])
        self.assertAlmostEqual(self.d.produto(alheio)["filamento_preco_kg"], 140.0, places=2)


class TesteEntradaDeEstoque(Base):
    """A compra entra pelo mesmo livro da sprint 3 -- nao por fora dele."""

    def test_o_que_entrou_soma_no_saldo(self):
        self.comprar(itens=[self.rolo()])
        self.assertAlmostEqual(self.d.filamento(self.fil)["gramas"], 3200, places=2)

    def test_o_cache_bate_com_os_movimentos(self):
        self.comprar(itens=[self.rolo()])
        self.comprar(data="2026-09-04", itens=[
            self.rolo(1000, 110.0),
            {"tipo": "insumo", "alvo_id": self.ins, "quantidade": 500, "valor": 150.0}])
        self.assertAlmostEqual(self.d.filamento(self.fil)["gramas"],
                               self.d.saldo_pelos_movimentos("filamento", self.fil), places=3)
        self.assertAlmostEqual(self.d.insumo(self.ins)["quantidade"],
                               self.d.saldo_pelos_movimentos("insumo", self.ins), places=3)

    def test_editar_a_compra_nao_soma_duas_vezes(self):
        """O erro classico: a edicao lanca de novo sem estornar o anterior."""
        id_ = self.comprar(itens=[self.rolo()])
        self.d.salvar_compra({"data": "2026-09-01", "fornecedor": "3D Fila"}, "samir",
                             id_=id_, itens=[self.rolo(2000, 190.0)])
        self.assertAlmostEqual(self.d.filamento(self.fil)["gramas"], 2200, places=2)
        self.assertAlmostEqual(self.preco_kg(), 95.0, places=2)

    def test_apagar_tira_do_estoque_o_que_pos(self):
        id_ = self.comprar(itens=[self.rolo()])
        self.d.apagar_compra(id_)
        self.assertAlmostEqual(self.d.filamento(self.fil)["gramas"], 200, places=2)
        self.assertAlmostEqual(self.d.filamento(self.fil)["gramas"],
                               self.d.saldo_pelos_movimentos("filamento", self.fil), places=3)

    def test_insumo_entra_pela_unidade_e_nao_por_kg(self):
        """Filamento se compra por kg; ima se compra por unidade. Dividir
        errado aqui poe o preco do ima mil vezes menor e ninguem estranha."""
        self.comprar(itens=[{"tipo": "insumo", "alvo_id": self.ins,
                             "quantidade": 500, "valor": 150.0}])
        self.assertAlmostEqual(self.d.insumo(self.ins)["valor_unit"], 0.30, places=4)
        self.assertAlmostEqual(self.d.insumo(self.ins)["quantidade"], 600, places=2)


class TesteEscadaDoPreco(Base):
    """O preco em uso e o da ULTIMA compra; sem compra, o digitado a mao.

    Cada degrau desta escada foi um jeito de a tela mentir. O ultimo -- apagar
    e o preco continuar sendo o da compra apagada -- e o que originou as duas
    colunas.
    """

    def test_a_escada_inteira(self):
        self.assertAlmostEqual(self.preco_kg(), 118.0, places=2)          # digitado
        antiga = self.comprar(itens=[self.rolo()])
        self.assertAlmostEqual(self.preco_kg(), 95.0, places=2)           # 1a compra
        recente = self.comprar(data="2026-09-06", itens=[self.rolo(1000, 110.0)])
        self.assertAlmostEqual(self.preco_kg(), 110.0, places=2)          # mais recente
        self.d.apagar_compra(recente)
        self.assertAlmostEqual(self.preco_kg(), 95.0, places=2)           # volta a anterior
        self.d.apagar_compra(antiga)
        self.assertAlmostEqual(self.preco_kg(), 118.0, places=2)          # volta ao digitado

    def test_data_manda_e_nao_a_ordem_de_digitacao(self):
        """Lancar hoje a nota do mes passado nao pode virar o preco de hoje."""
        self.comprar(data="2026-09-06", itens=[self.rolo(1000, 110.0)])
        self.comprar(data="2026-08-01", itens=[self.rolo(1000, 60.0)])
        self.assertAlmostEqual(self.preco_kg(), 110.0, places=2)

    def test_mexer_no_preco_a_mao_nao_apaga_a_compra_do_historico(self):
        id_ = self.comprar(itens=[self.rolo()])
        self.d.salvar_filamento({"nome": "PLA Rosa", "cor": "Rosa", "gramas": 3200,
                                 "preco_kg": 999}, "samir", id_=self.fil)
        self.assertIsNotNone(self.d.compra(id_))
        self.assertEqual(len(self.d.compras()), 1)

    def test_compra_sem_item_e_recusada(self):
        with self.assertRaises(ValueError):
            self.comprar(itens=[])


class TesteFichaNaoRoubaOPrecoDaCompra(Base):
    """O campo da ficha e dono do preco DIGITADO -- e so dele.

    O campo mostrava o preco em uso. Com uma compra lancada, quem abrisse o
    filamento para trocar a cor e salvasse gravava o valor da compra como se
    fosse o digitado: o numero que a pessoa tinha escolhido sumia sem aviso,
    e apagar a compra depois nao trazia ele de volta.
    """

    def salvar_ficha(self, preco="118"):
        return self.d.salvar_filamento(
            {"nome": "PLA Rosa", "cor": "Rosa", "gramas": 200, "preco_kg": preco},
            "samir", id_=self.fil)

    def test_salvar_a_ficha_nao_derruba_o_preco_da_compra(self):
        self.comprar(itens=[self.rolo()])
        self.salvar_ficha()
        self.assertAlmostEqual(self.preco_kg(), 95.0, places=2)

    def test_o_digitado_sobrevive_a_compra_e_volta_quando_ela_sai(self):
        id_ = self.comprar(itens=[self.rolo()])
        self.salvar_ficha()
        self.d.apagar_compra(id_)
        self.assertAlmostEqual(self.preco_kg(), 118.0, places=2)

    def test_apagar_o_preco_da_ficha_nao_apaga_o_da_compra(self):
        self.comprar(itens=[self.rolo()])
        self.salvar_ficha(preco="")
        self.assertAlmostEqual(self.preco_kg(), 95.0, places=2)

    def test_sem_compra_o_digitado_e_o_preco_em_uso(self):
        self.salvar_ficha(preco="140")
        self.assertAlmostEqual(self.preco_kg(), 140.0, places=2)

    def editar_insumo(self, valor):
        self.d.salvar_insumo({"nome": "Ima 8mm", "quantidade": self.d.insumo(self.ins)["quantidade"],
                              "valor_unit": valor}, "samir", id_=self.ins)
        return self.d.insumo(self.ins)["valor_unit"]

    def test_mesma_regra_para_insumo(self):
        id_ = self.comprar(itens=[{"tipo": "insumo", "alvo_id": self.ins,
                                   "quantidade": 500, "valor": 150.0}])
        self.assertAlmostEqual(self.editar_insumo("0.35"), 0.30, places=4)
        self.d.apagar_compra(id_)
        self.assertAlmostEqual(self.d.insumo(self.ins)["valor_unit"], 0.35, places=4)

    def test_insumo_sem_compra_segue_o_que_foi_digitado(self):
        """Sem isso, mudar o valor na ficha nao mudava nada na tela."""
        self.assertAlmostEqual(self.editar_insumo("0.50"), 0.50, places=4)

    def test_a_lista_diz_de_onde_veio_o_numero(self):
        self.assertFalse(self.d.filamentos()[0]["veio_de_compra"])
        self.comprar(itens=[self.rolo()])
        self.assertTrue(self.d.filamentos()[0]["veio_de_compra"])
        self.assertTrue(self.d.filamento(self.fil)["veio_de_compra"])


class TesteBancoQueJaEstavaRodando(Base):
    """O banco da VPS ja tem preco digitado. Ele nao pode sumir na atualizacao.

    A sprint partiu uma coluna em duas. Se a migracao nao copiar o valor
    antigo para a nova coluna, o primeiro salvamento de ficha depois do
    deploy zera o preco de todo filamento -- e com ele o custo de tudo.
    """

    def envelhecer(self):
        """Devolve o banco a forma anterior a esta sprint."""
        with self.d.conectar() as conn:
            conn.execute("ALTER TABLE filamentos DROP COLUMN preco_manual")
            conn.execute("ALTER TABLE insumos DROP COLUMN valor_manual")
            conn.commit()
        importlib.reload(self.d)

    def test_o_preco_digitado_sobrevive_a_atualizacao(self):
        self.envelhecer()
        self.assertAlmostEqual(self.d.filamento(self.fil)["preco_manual"], 118.0, places=2)
        self.assertAlmostEqual(self.d.insumo(self.ins)["valor_manual"], 0.35, places=4)

    def test_e_a_ficha_salva_depois_do_deploy_nao_zera_nada(self):
        self.envelhecer()
        self.d.salvar_filamento({"nome": "PLA Rosa", "cor": "Rosa", "gramas": 200,
                                 "preco_kg": "118"}, "samir", id_=self.fil)
        self.assertAlmostEqual(self.d.filamento(self.fil)["preco_kg"], 118.0, places=2)


class TesteTelaDeCompras(unittest.TestCase):
    """Erro de template so aparece quando a pagina e renderizada de verdade."""

    def setUp(self):
        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-tela-compras-")
        os.environ["MORUMBI_USUARIO"] = "samir"
        os.environ["MORUMBI_SENHA"] = "segredo"
        os.environ["MORUMBI_BIND"] = "127.0.0.1:5000"
        os.environ["MORUMBI_HTTPS"] = "0"
        from sistema import auth, dados
        importlib.reload(dados)
        importlib.reload(auth)
        from sistema import app as modulo
        importlib.reload(modulo)
        self.d = dados
        self.fil = dados.salvar_filamento(
            {"nome": "PLA Rosa", "cor": "Rosa", "gramas": 200, "preco_kg": 118}, "samir")
        self.app = modulo.criar_app()
        self.app.config["TESTING"] = True
        self.cliente = self.app.test_client()
        self.cliente.post("/entrar", data={"usuario": "samir", "senha": "segredo"})

    def test_as_telas_abrem(self):
        for rota in ("/compras", "/compras/nova"):
            with self.subTest(rota=rota):
                self.assertEqual(self.cliente.get(rota).status_code, 200)

    def test_sem_sessao_nao_abre(self):
        r = self.app.test_client().get("/compras")
        self.assertEqual(r.status_code, 302)
        self.assertTrue("/entrar" in r.headers["Location"], r.headers["Location"])

    def test_lancar_pelo_formulario_muda_o_preco(self):
        r = self.cliente.post("/compras/nova", data={
            "data": "2026-09-01", "fornecedor": "3D Fila", "nota": "1234",
            "item_alvo": [f"filamento:{self.fil}"],
            "item_qtd": ["3000"], "item_valor": ["285,00"]})
        self.assertEqual(r.status_code, 302)
        self.assertAlmostEqual(self.d.filamento(self.fil)["preco_kg"], 95.0, places=2)
        self.assertEqual(self.cliente.get(r.headers["Location"]).status_code, 200)

    def test_linha_em_branco_do_formulario_e_ignorada(self):
        """A tela sempre manda uma linha vazia sobrando; ela nao pode virar item."""
        self.cliente.post("/compras/nova", data={
            "data": "2026-09-01",
            "item_alvo": [f"filamento:{self.fil}", ""],
            "item_qtd": ["3000", ""], "item_valor": ["285", ""]})
        self.assertEqual(len(self.d.compra(1)["itens"]), 1)

    def test_compra_vazia_devolve_erro_na_tela_e_nao_500(self):
        r = self.cliente.post("/compras/nova", data={"data": "2026-09-01",
                                                     "item_alvo": [""], "item_qtd": [""]})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.d.compras(), [])

    def test_compra_que_nao_existe_da_404(self):
        self.assertEqual(self.cliente.get("/compras/99").status_code, 404)
        self.assertEqual(self.cliente.post("/compras/99/apagar").status_code, 404)

    def test_apagar_pelo_formulario(self):
        id_ = self.d.salvar_compra({"data": "2026-09-01"}, "samir", itens=[
            {"tipo": "filamento", "alvo_id": self.fil, "quantidade": 3000, "valor": 285}])
        r = self.cliente.post(f"/compras/{id_}/apagar")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.d.compras(), [])
        self.assertAlmostEqual(self.d.filamento(self.fil)["preco_kg"], 118.0, places=2)

    def campo(self, pagina, nome):
        achado = re.search(r'name="%s"[^>]*?value="([^"]*)"' % nome, pagina, re.S)
        self.assertIsNotNone(achado, f"campo {nome} sumiu do formulario")
        return achado.group(1)

    def test_a_ficha_mostra_o_preco_digitado_e_nao_o_da_compra(self):
        """O teste que faltava: o BUG morava no template, nao no banco.

        O campo exibia o preco em uso. Com uma compra lancada, o navegador
        devolvia o valor DELA ao salvar -- e o numero digitado morria ali,
        sem ninguem ter mexido nele.
        """
        self.d.salvar_compra({"data": "2026-09-01"}, "samir", itens=[
            {"tipo": "filamento", "alvo_id": self.fil, "quantidade": 3000, "valor": 285}])
        pagina = self.cliente.get(f"/filamentos/{self.fil}").get_data(as_text=True)
        self.assertEqual(self.campo(pagina, "preco_kg"), "118.00")
        self.assertNotEqual(self.campo(pagina, "preco_kg"), "95.00")
        self.assertTrue("R$ 95,00/kg" in pagina,
                        "a ficha precisa dizer qual preco esta valendo hoje")

    def test_salvar_a_ficha_como_o_navegador_manda_nao_mexe_no_preco(self):
        """O caminho inteiro: abrir a ficha, salvar sem tocar em nada."""
        compra = self.d.salvar_compra({"data": "2026-09-01"}, "samir", itens=[
            {"tipo": "filamento", "alvo_id": self.fil, "quantidade": 3000, "valor": 285}])
        pagina = self.cliente.get(f"/filamentos/{self.fil}").get_data(as_text=True)
        self.cliente.post(f"/filamentos/{self.fil}", data={
            "nome": "PLA Rosa", "tipo": "PLA", "cor": "Rosa", "ativo": "1",
            "gramas": self.campo(pagina, "gramas"), "minimo": self.campo(pagina, "minimo"),
            "preco_kg": self.campo(pagina, "preco_kg")})
        self.assertAlmostEqual(self.d.filamento(self.fil)["preco_kg"], 95.0, places=2)
        self.d.apagar_compra(compra)
        self.assertAlmostEqual(self.d.filamento(self.fil)["preco_kg"], 118.0, places=2)

    def test_o_menu_leva_para_compras(self):
        pagina = self.cliente.get("/filamentos").get_data(as_text=True)
        self.assertTrue('href="/compras"' in pagina, "o link de Compras sumiu do menu")
