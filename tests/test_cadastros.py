# -*- coding: utf-8 -*-
"""Sprint 1 — filamento, insumo, produto, e o peso vindo do arquivo.

O que estes testes protegem, em ordem de quanto doeria errar:

1. O PRECO. Existiam duas formulas no projeto: a do gerador de letreiros
   (piso + gramas x valor, para cima de 5 em 5) e a do pricing.py (custo x
   margem, arredondado a .90). A mesma peca saia com dois precos. Agora o
   preco e um so, e este arquivo trava a formula contra a do JavaScript.
2. O PESO. Ele vem do analisador de malha, e nao de digitacao. Se a ponte
   divergir do analisador, todo custo do catalogo fica errado junto.
3. A MIGRACAO. O estoque era uma linha por cor e virou uma linha por rolo.
   Perder grama nessa troca e perder dinheiro no inventario.
"""
from __future__ import annotations

import importlib
import math
import os
import struct
import tempfile
import unittest
from pathlib import Path


def cubo_stl(destino: Path, lado: float = 20.0) -> Path:
    """Um cubo fechado, para medir contra numero conhecido."""
    v = [(0, 0, 0), (lado, 0, 0), (lado, lado, 0), (0, lado, 0),
         (0, 0, lado), (lado, 0, lado), (lado, lado, lado), (0, lado, lado)]
    faces = [(0, 3, 2), (0, 2, 1), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
             (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    tris = [(v[a], v[b], v[c]) for a, b, c in faces]
    with open(destino, "wb") as f:
        f.write(b"\0" * 80)
        f.write(struct.pack("<I", len(tris)))
        for t in tris:
            f.write(struct.pack("<3f", 0, 0, 0))
            for q in t:
                f.write(struct.pack("<3f", *q))
            f.write(b"\0\0")
    return destino


class TestePreco(unittest.TestCase):
    """A formula comercial e a do balcao, e ela e uma so no sistema inteiro."""

    def setUp(self):
        from sistema import custo
        self.custo = custo

    def test_bate_com_a_formula_do_gerador_de_letreiros(self):
        """No gerador:  Math.ceil((piso + gTotal * pg) / 5) * 5

        Se esta linha divergir daquela, a mesma peca passa a ter dois precos
        -- um na tela do gerador e outro no cadastro.
        """
        piso, pg = 18.0, 0.60
        for gramas in (1, 12.5, 34, 85, 120, 333.3, 1000):
            js = math.ceil((piso + gramas * pg) / 5) * 5
            self.assertEqual(self.custo.preco_comercial(gramas, piso, pg), float(js),
                             f"divergiu em {gramas} g")

    def test_peca_sem_peso_nao_tem_preco(self):
        self.assertEqual(self.custo.preco_comercial(0, 18, 0.6), 0.0)

    def test_sem_preco_do_filamento_a_conta_se_declara_incompleta(self):
        """A hora de mesa sozinha nao e o custo -- falta o material.

        Sem esta marca, uma peca de 9 g aparecia com 93,8% de margem.
        """
        from sistema.dados import PADROES
        c = self.custo.calcular(85, 3.4, None, param=PADROES)
        self.assertFalse(c.completo)
        self.assertEqual(c.custo_filamento, 0.0)
        self.assertEqual(c.margem_pct, 0.0, "margem sobre custo incompleto e mentira")
        self.assertEqual(c.por_hora, 0.0)
        self.assertGreater(c.preco, 0, "o preco nao depende de saber o custo")

    def test_com_preco_do_filamento_a_conta_e_completa(self):
        from sistema.dados import PADROES
        c = self.custo.calcular(85, 3.4, 120.0, param=PADROES)
        self.assertTrue(c.completo)
        self.assertGreater(c.margem_pct, 0)

    def test_reserva_de_falha_nao_incide_sobre_insumo(self):
        """Peca refugada perde filamento e hora de mesa; o ima costuma sobrar."""
        from sistema.dados import PADROES
        sem = self.custo.calcular(100, 2, 120.0, insumos=0, param=PADROES)
        com = self.custo.calcular(100, 2, 120.0, insumos=10, param=PADROES)
        self.assertEqual(sem.custo_falha, com.custo_falha)
        self.assertAlmostEqual(com.custo - sem.custo, 10.0, places=2)

    def test_margem_e_retorno_por_hora(self):
        from sistema.dados import PADROES
        c = self.custo.calcular(100, 4, 120.0, param=PADROES)
        self.assertAlmostEqual(c.margem, round(c.preco - c.custo, 2), places=2)
        self.assertAlmostEqual(c.por_hora, round((c.preco - c.custo) / 4, 2), places=2)


class TestePrecoVolume(unittest.TestCase):
    """Tabela de precos por volume usando a bandeja da A2L (330x320 mm)."""

    def setUp(self):
        from sistema import custo
        from sistema.dados import PADROES
        self.custo = custo
        self.param = PADROES

    def _produto(self, **extra):
        base = dict(gramas=85, horas=3.4, filamento_preco_kg=120.0,
                    dimensao_x=100, dimensao_y=100,
                    usa_preco_volume=1, margem_volume=150, taxa_setup=5.0)
        base.update(extra)
        return base

    def test_sem_flag_retorna_none(self):
        p = self._produto(usa_preco_volume=0)
        self.assertIsNone(self.custo.preco_por_volume(p, self.param))

    def test_retorna_quatro_faixas(self):
        r = self.custo.preco_por_volume(self._produto(), self.param)
        self.assertIsNotNone(r)
        self.assertEqual(len(r["tabela"]), 4)
        self.assertGreater(r["quantidade_por_bandeja"], 1)

    def test_preco_unitario_diminui_com_volume(self):
        r = self.custo.preco_por_volume(self._produto(), self.param)
        precos = [f["preco_unitario"] for f in r["tabela"]]
        for i in range(1, len(precos)):
            self.assertLessEqual(precos[i], precos[0],
                                 "volume maior deve custar igual ou menos por unidade")

    def test_bandeja_calcula_com_ocupacao_80(self):
        p = self._produto(dimensao_x=100, dimensao_y=100)
        r = self.custo.preco_por_volume(p, self.param)
        self.assertEqual(r["quantidade_por_bandeja"], 7)

    def test_peca_grande_cabe_menos(self):
        pequena = self.custo.preco_por_volume(
            self._produto(dimensao_x=50, dimensao_y=50), self.param)
        grande = self.custo.preco_por_volume(
            self._produto(dimensao_x=150, dimensao_y=150), self.param)
        self.assertGreater(pequena["quantidade_por_bandeja"],
                           grande["quantidade_por_bandeja"])

    def test_margem_maior_sobe_preco(self):
        r150 = self.custo.preco_por_volume(
            self._produto(margem_volume=150), self.param)
        r200 = self.custo.preco_por_volume(
            self._produto(margem_volume=200), self.param)
        for i in range(4):
            self.assertGreater(r200["tabela"][i]["preco_unitario"],
                               r150["tabela"][i]["preco_unitario"])

    def test_setup_dilui_no_volume(self):
        r = self.custo.preco_por_volume(self._produto(taxa_setup=10.0), self.param)
        faixa1 = r["tabela"][0]
        faixa50 = r["tabela"][3]
        setup_impacto_1 = 10.0 / 1
        setup_impacto_50 = 10.0 / 50
        self.assertGreater(setup_impacto_1, setup_impacto_50)


class TesteMedirArquivo(unittest.TestCase):
    """A ponte para o analisador nao pode divergir do analisador."""

    def setUp(self):
        from sistema import analise
        self.analise = analise
        self.pasta = Path(tempfile.mkdtemp(prefix="morumbi-medir-"))

    def test_o_peso_e_o_do_analisador(self):
        from morumbi3d.config import Config
        from morumbi3d.mesh import analisar_arquivo
        arq = cubo_stl(self.pasta / "cubo.stl")
        direto = analisar_arquivo(arq, Config())
        pela_ponte = self.analise.medir(arq)
        self.assertEqual(pela_ponte["gramas"], round(direto.material_g, 1))
        self.assertEqual(pela_ponte["horas"], round(direto.tempo_h, 2))
        self.assertEqual(pela_ponte["malha_nota"], direto.nota)

    def test_a_caixa_e_a_da_peca(self):
        m = self.analise.medir(cubo_stl(self.pasta / "c.stl", lado=37.5))
        self.assertEqual((m["caixa_x"], m["caixa_y"], m["caixa_z"]), (37.5, 37.5, 37.5))

    def test_peca_grande_demais_e_denunciada(self):
        """Mesa de 256 mm. 400 mm nao cabe nem reta nem girada."""
        m = self.analise.medir(cubo_stl(self.pasta / "g.stl", lado=400))
        self.assertFalse(m["cabe_na_mesa"])
        self.assertFalse(m["cabe_girando"])

    def test_malha_aberta_e_marcada(self):
        """STL com um triangulo so: 3 arestas sem par."""
        p = self.pasta / "aberta.stl"
        with open(p, "wb") as f:
            f.write(b"\0" * 80 + struct.pack("<I", 1) + struct.pack("<3f", 0, 0, 1))
            for q in ((0, 0, 0), (10, 0, 0), (0, 10, 0)):
                f.write(struct.pack("<3f", *q))
            f.write(b"\0\0")
        m = self.analise.medir(p)
        self.assertEqual(m["malha_ok"], 0)
        self.assertFalse(m["fechada"])

    def test_formato_desconhecido_e_recusado_antes_de_gravar(self):
        class Falso:
            filename = "planilha.xlsx"

            def save(self, destino):
                raise AssertionError("nao podia ter chegado a gravar")

        with self.assertRaises(self.analise.ArquivoRecusado):
            self.analise.guardar(Falso(), self.pasta)

    def test_nome_de_arquivo_nao_anda_para_fora_da_pasta(self):
        for perigoso in ("../../etc/passwd", "/etc/passwd", "..\\..\\senha.stl",
                         "modelo com espaço.stl", "modelo\x00.stl"):
            seguro = self.analise.nome_seguro(perigoso)
            self.assertNotIn("/", seguro)
            self.assertNotIn("\\", seguro)
            self.assertFalse(seguro.startswith("."), seguro)


class TesteCadastros(unittest.TestCase):
    """Salvar, ler, e a migracao do estoque antigo."""

    def setUp(self):
        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-cad-")
        from sistema import dados
        importlib.reload(dados)
        self.dados = dados

    def test_filamento_exige_cor_do_catalogo(self):
        """Fila e estoque tem que falar a mesma lingua, senao nao se cruzam."""
        with self.assertRaises(ValueError):
            self.dados.salvar_filamento({"nome": "PLA X", "cor": "Bordô"}, "samir")

    def test_salva_e_le_de_volta(self):
        i = self.dados.salvar_filamento(
            {"nome": "PLA Basic Preto", "cor": "Preto", "gramas": 920, "preco_kg": 118}, "samir")
        f = self.dados.filamento(i)
        self.assertEqual(f["nome"], "PLA Basic Preto")
        self.assertEqual(f["preco_kg"], 118.0)
        self.assertEqual(f["criado_por"], "samir", "o autor tem que ficar gravado")

    def test_produto_carrega_o_preco_do_filamento(self):
        fil = self.dados.salvar_filamento(
            {"nome": "PLA Preto", "cor": "Preto", "gramas": 900, "preco_kg": 120}, "samir")
        ins = self.dados.salvar_insumo(
            {"nome": "Ima 8mm", "quantidade": 100, "valor_unit": 0.35}, "samir")
        pid = self.dados.salvar_produto(
            {"nome": "Topo ANA", "gramas": 85, "horas": 3.4, "filamento_id": fil},
            "samir", vinculos=[(ins, 2)])
        p = self.dados.produto(pid)
        self.assertEqual(p["filamento_preco_kg"], 120.0)
        self.assertEqual(len(p["insumos"]), 1)
        self.assertEqual(p["insumos"][0]["quantidade"], 2.0)

    def test_regravar_produto_nao_duplica_insumo(self):
        ins = self.dados.salvar_insumo({"nome": "Fita", "quantidade": 10}, "samir")
        pid = self.dados.salvar_produto({"nome": "P"}, "samir", vinculos=[(ins, 1)])
        self.dados.salvar_produto({"nome": "P"}, "samir", pid, vinculos=[(ins, 3)])
        p = self.dados.produto(pid)
        self.assertEqual(len(p["insumos"]), 1)
        self.assertEqual(p["insumos"][0]["quantidade"], 3.0)

    def test_migracao_do_estoque_antigo_preserva_gramas(self):
        """Era uma linha por cor; virou uma por rolo. Nao pode sumir grama."""
        with self.dados.conectar() as conn:
            conn.execute("DROP TABLE IF EXISTS filamentos")
            conn.execute("CREATE TABLE filamento (cor TEXT PRIMARY KEY,"
                         " gramas REAL NOT NULL DEFAULT 0, minimo REAL NOT NULL DEFAULT 300)")
            conn.executemany("INSERT INTO filamento (cor, gramas, minimo) VALUES (?, ?, ?)",
                             [("Preto", 920, 300), ("Rosa", 140, 250)])
            conn.commit()

        depois = {f["cor"]: f for f in self.dados.filamentos()}
        self.assertEqual(depois["Preto"]["gramas"], 920)
        self.assertEqual(depois["Rosa"]["minimo"], 250)
        self.assertEqual(depois["Preto"]["nome"], "PLA Preto")
        self.assertEqual(depois["Preto"]["criado_por"], "migracao")

        with self.dados.conectar() as conn:
            sobrou = conn.execute(
                "SELECT name FROM sqlite_master WHERE name = 'filamento'").fetchone()
        self.assertIsNone(sobrou, "a tabela antiga tem que sair, senao migra de novo")

    def test_parametros_tem_os_padroes_do_balcao(self):
        p = self.dados.parametros()
        self.assertEqual(p["piso"], 18.0)
        self.assertEqual(p["por_grama"], 0.60)


class TesteTelas(unittest.TestCase):
    """As seis telas novas, com sessao de verdade.

    Erro de template nao aparece em teste de funcao -- so quando a pagina e
    renderizada. Por isso cada tela e aberta aqui.
    """

    def setUp(self):
        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-telas-")
        os.environ["MORUMBI_USUARIO"] = "samir"
        os.environ["MORUMBI_SENHA"] = "segredo"
        os.environ["MORUMBI_BIND"] = "127.0.0.1:5000"
        os.environ["MORUMBI_HTTPS"] = "0"
        from sistema import auth, dados
        importlib.reload(dados)
        importlib.reload(auth)
        from sistema import app as modulo
        importlib.reload(modulo)
        self.dados = dados
        self.app = modulo.criar_app()
        self.app.config["TESTING"] = True
        self.cliente = self.app.test_client()
        self.cliente.post("/entrar", data={"usuario": "samir", "senha": "segredo"})

    def test_todas_as_telas_abrem(self):
        for rota in ("/produtos", "/produtos/novo", "/filamentos", "/filamentos/novo",
                     "/insumos", "/insumos/novo"):
            with self.subTest(rota=rota):
                self.assertEqual(self.cliente.get(rota).status_code, 200)

    def test_sem_sessao_nenhuma_abre(self):
        anonimo = self.app.test_client()
        for rota in ("/produtos", "/filamentos", "/insumos"):
            with self.subTest(rota=rota):
                r = anonimo.get(rota)
                self.assertEqual(r.status_code, 302)
                self.assertIn("/entrar", r.headers["Location"])

    def test_medir_sem_sessao_nao_aceita_upload(self):
        """A rota grava arquivo no disco: sem cadeado, e disco de qualquer um."""
        r = self.app.test_client().post("/produtos/medir")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/entrar", r.headers["Location"])

    def test_cadastrar_pelo_formulario(self):
        r = self.cliente.post("/filamentos/novo", data={
            "nome": "PLA Basic Preto", "tipo": "PLA", "cor": "Preto",
            "gramas": "920", "minimo": "300", "preco_kg": "118", "ativo": "1"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.dados.filamentos()[0]["nome"], "PLA Basic Preto")

    def test_cor_invalida_volta_o_formulario_com_o_motivo(self):
        r = self.cliente.post("/filamentos/novo",
                              data={"nome": "PLA X", "cor": "Bordô"})
        self.assertEqual(r.status_code, 400)
        corpo = r.get_data(as_text=True)
        self.assertTrue("cores do catálogo" in corpo, "a tela precisa dizer o motivo")
        # Desde o U4 o erro sabe de qual campo ele e, e a tela marca o campo.
        self.assertTrue('id="campo-cor"' in corpo, "o erro precisa apontar o campo")

    def test_lista_de_produto_mostra_custo_e_margem(self):
        fil = self.dados.salvar_filamento(
            {"nome": "PLA Preto", "cor": "Preto", "gramas": 900, "preco_kg": 120}, "samir")
        self.dados.salvar_produto(
            {"nome": "Topo ANA 18", "gramas": 85, "horas": 3.4, "filamento_id": fil}, "samir")
        corpo = self.cliente.get("/produtos").get_data(as_text=True)
        self.assertTrue("Topo ANA 18" in corpo, "o nome do produto")
        self.assertTrue("R$ 70,00" in corpo,   # ceil((18 + 85*0,6)/5)*5 = 70
                        "preco sugerido, na convencao da casa")

    def test_produto_sem_filamento_nao_mostra_custo_falso(self):
        """Custo sem material nao e custo baixo: e custo desconhecido.

        Um chaveiro de 9 g sem preco de filamento tinha custo R$ 1,54 (so a
        hora de mesa) e margem de 93,8% na tela. E o tipo de numero que leva
        a baixar o preco de um produto que da prejuizo.
        """
        self.dados.salvar_produto({"nome": "Chaveiro", "gramas": 9, "horas": 0.4}, "samir")
        corpo = self.cliente.get("/produtos").get_data(as_text=True)
        self.assertTrue("sem filamento" in corpo, "a tela precisa dizer o que falta")
        self.assertTrue("93,8" not in corpo, "margem inventada sobre custo incompleto")
        self.assertTrue("R$ 1,54" not in corpo,
                        "custo sem material nao pode aparecer como custo")

    def test_medir_devolve_medida_e_conta(self):
        import io
        pasta = Path(tempfile.mkdtemp())
        caminho = cubo_stl(pasta / "cubo.stl", 60)
        fil = self.dados.salvar_filamento(
            {"nome": "PLA Preto", "cor": "Preto", "gramas": 900, "preco_kg": 120}, "samir")
        r = self.cliente.post("/produtos/medir", data={
            "modelo": (io.BytesIO(caminho.read_bytes()), "cubo.stl"),
            "filamento_id": str(fil),
        }, content_type="multipart/form-data")
        self.assertEqual(r.status_code, 200)
        corpo = r.get_json()
        self.assertEqual(corpo["medida"]["caixa_x"], 60.0)
        self.assertEqual(corpo["medida"]["malha_ok"], 1)
        self.assertGreater(corpo["conta"]["custo_filamento"], 0)

    def test_medir_arquivo_errado_explica_em_vez_de_estourar(self):
        import io
        r = self.cliente.post("/produtos/medir", data={
            "modelo": (io.BytesIO(b"nao sou um stl"), "planilha.xlsx"),
        }, content_type="multipart/form-data")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Formato", r.get_json()["erro"])

    def test_campo_vazio_no_banco_nao_vira_a_palavra_None(self):
        """SKU aceita nulo, e nulo no Jinja vira o texto "None".

        Visto na tela do Samir: o campo SKU de um produto sem SKU aparecia
        preenchido com "None" -- e salvar dali gravaria o SKU "None".
        """
        pid = self.dados.salvar_produto({"nome": "Topo de Bolo Isabel"}, "samir")
        corpo = self.cliente.get(f"/produtos/{pid}").get_data(as_text=True)
        self.assertNotIn('value="None"', corpo)
        self.assertNotIn(">None<", corpo)


class TesteDoisTempos(unittest.TestCase):
    """A impressora trabalha sozinha; as maos entram por minutos.

    A primeira versao tinha uma linha de tempo so e multiplicava o valor da
    hora de trabalho pelas horas da MAQUINA. Com a hora do Samir a R$ 25, o
    topo de bolo de 5,77 h aparecia com R$ 96 de PREJUIZO -- cobrado por
    horas em que ninguem estava trabalhando. Estes testes existem para essa
    confusao nao voltar.
    """

    def setUp(self):
        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-tempos-")
        from sistema import custo, dados
        importlib.reload(dados)
        self.custo, self.dados = custo, dados
        self.param = dados.PADROES

    def test_a_hora_da_pessoa_nao_multiplica_as_horas_da_maquina(self):
        """Dobrar o tempo de IMPRESSAO nao pode dobrar o custo de mao de obra."""
        curto = self.custo.calcular(80, 2.0, 80.0, minutos=30, param=self.param)
        longo = self.custo.calcular(80, 8.0, 80.0, minutos=30, param=self.param)
        self.assertEqual(curto.custo_pessoa, longo.custo_pessoa)
        self.assertGreater(longo.custo_maquina, curto.custo_maquina)

    def test_o_topo_de_bolo_real_nao_da_prejuizo(self):
        """83,7 g, 5,77 h, 30 min de maos, vendido a R$ 70."""
        c = self.custo.calcular(83.7, 5.77, 80.0, minutos=30, param=self.param)
        self.assertAlmostEqual(c.custo_pessoa, 12.50, places=2)
        self.assertLess(c.custo, 70.0, "a peca que ele vende nao pode custar mais que o preco")
        self.assertGreater(c.margem_pct, 40)

    def test_sem_minutos_no_produto_usa_o_padrao(self):
        padrao = self.custo.calcular(80, 3, 80.0, param=self.param)
        igual = self.custo.calcular(80, 3, 80.0, minutos=self.param["minutos_acabamento"],
                                    param=self.param)
        self.assertEqual(padrao.custo_pessoa, igual.custo_pessoa)

    def test_menos_acabamento_custa_menos(self):
        """E o que o gerador de topo de bolo vale, em dinheiro."""
        trinta = self.custo.calcular(83.7, 5.77, 80.0, minutos=30, param=self.param)
        dez = self.custo.calcular(83.7, 5.77, 80.0, minutos=10, param=self.param)
        economia = trinta.custo - dez.custo
        self.assertGreater(economia, 9.0)
        self.assertLess(economia, 10.0)

    def test_a_reserva_de_falha_cobre_o_acabamento_perdido(self):
        """Peca refugada leva junto o acabamento que ja tinha sido feito."""
        sem = self.custo.calcular(80, 3, 80.0, minutos=0, param=self.param)
        com = self.custo.calcular(80, 3, 80.0, minutos=60, param=self.param)
        self.assertGreater(com.custo_falha, sem.custo_falha)

    def test_migracao_corrige_a_hora_de_maquina_antiga(self):
        """A versao anterior gravou 3,50, que misturava maquina com mao de obra."""
        with self.dados.conectar() as conn:
            conn.execute("UPDATE parametros SET valor = 3.50 WHERE chave = 'custo_hora_maquina'")
            conn.commit()
        self.assertEqual(self.dados.parametros()["custo_hora_maquina"],
                         self.dados.PADROES["custo_hora_maquina"])

    def test_migracao_respeita_valor_ja_ajustado(self):
        """Se alguem escolheu um numero, a escolha da pessoa vale mais."""
        with self.dados.conectar() as conn:
            conn.execute("UPDATE parametros SET valor = 4.20 WHERE chave = 'custo_hora_maquina'")
            conn.commit()
        self.assertEqual(self.dados.parametros()["custo_hora_maquina"], 4.20)

    def test_produto_guarda_os_minutos_dele(self):
        fil = self.dados.salvar_filamento(
            {"nome": "PLA Preto", "cor": "Preto", "preco_kg": 80}, "samir")
        pid = self.dados.salvar_produto(
            {"nome": "Chaveiro", "gramas": 9, "horas": 0.4, "minutos": 5,
             "filamento_id": fil}, "samir")
        self.assertEqual(self.dados.produto(pid)["minutos"], 5.0)
