# -*- coding: utf-8 -*-
"""Sprint U5 -- tela vazia que ensina, e espera que fala.

Medido antes deste sprint:

  * das cinco colunas do quadro de producao, **tres ficavam vazias** e nenhuma
    dizia nada -- um retangulo em branco onde devia estar "o que chega aqui,
    e como";
  * o cabecalho da coluna contava PECAS e so. "3" nao diz se a coluna e meia
    hora ou dois dias de mesa;
  * o gerador ficava **1,9 s com a tela branca** na primeira carga, e sem
    template nenhum ficava branco para sempre, sem uma palavra.

A regra deste arquivo: **toda tela que pode ficar vazia tem que ensinar**. O
ultimo teste varre todas elas com o banco zerado -- e e ele que impede a
proxima tela de nascer muda.

O que so o navegador prova -- a cobertura do gerador, e ela NAO cobrir o
desenho que ja existe -- fica em tests/test_navegador.py.
"""
from __future__ import annotations

import importlib
import os
import re
import tempfile
import unittest


class Base(unittest.TestCase):
    def setUp(self):
        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-vazio-")
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
        self.app = modulo.criar_app()
        self.app.config["TESTING"] = True
        self.cliente = self.app.test_client()
        self.cliente.post("/entrar", data={"usuario": "samir", "senha": "segredo"})

    def pagina(self, rota="/"):
        return self.cliente.get(rota).get_data(as_text=True)

    def semear(self):
        """Uma peca so, aguardando: quatro das cinco colunas ficam vazias."""
        fil = self.d.salvar_filamento({"nome": "PLA Rosa", "cor": "Rosa",
                                       "gramas": 1000, "preco_kg": 118}, "samir")
        cli = self.d.salvar_cliente({"nome": "Ana", "canal": "Instagram"}, "samir")
        ped = self.d.salvar_pedido({"cliente_id": cli}, "samir", itens=[
            {"descricao": "Topo ANA", "cor": "Rosa", "quantidade": 1,
             "valor_unit": 70, "gramas": 83.7, "horas": 5.77}])
        self.d.mudar_situacao(ped, "aprovado", "samir")
        return fil, ped


class TesteAColunaVaziaEnsina(Base):
    """Um retangulo em branco nao diz o que a etapa e nem o que a enche."""

    def test_toda_etapa_tem_convite(self):
        """Etapa nova sem convite fica vermelha aqui, em vez de nascer muda."""
        for etapa in self.d.ETAPAS:
            self.assertIn(etapa, self.d.CONVITES, f"etapa {etapa} sem convite")
            self.assertGreater(len(self.d.CONVITES[etapa]), 30,
                               f"o convite de {etapa} é curto demais para ensinar")

    def test_nenhum_convite_sobrando(self):
        """Convite de etapa que nao existe mais é texto morto no código."""
        for etapa in self.d.CONVITES:
            self.assertIn(etapa, self.d.ETAPAS, f"convite de etapa inexistente: {etapa}")

    def test_a_coluna_vazia_mostra_o_convite_e_a_cheia_nao(self):
        self.semear()
        pagina = self.pagina("/producao")
        quadro = pagina[pagina.index('id="quadro"'):pagina.index('id="lista"')]
        colunas = quadro.split('<section class="coluna"')
        # A primeira fatia é o que vem antes da primeira coluna.
        self.assertEqual(len(colunas) - 1, len(self.d.ETAPAS))
        aguardando = colunas[1]
        self.assertTrue("convite" not in aguardando, "coluna com peça não precisa de convite")
        for vazia in colunas[2:]:
            self.assertTrue("convite" in vazia, "coluna vazia ficou muda")

    def test_o_convite_da_etapa_certa_na_coluna_certa(self):
        """Convite trocado ensina a coisa errada, e ninguém percebe."""
        self.semear()
        pagina = self.pagina("/producao")
        for etapa in self.d.ETAPAS[1:]:
            trecho = pagina[pagina.index(f'data-etapa="{etapa}"'):]
            trecho = trecho[:trecho.index("</section>")]
            self.assertTrue(self.d.CONVITES[etapa][:40] in trecho,
                            f"a coluna {etapa} mostra o convite de outra")


class TesteOsTotaisPorColuna(Base):
    """Peça sozinha não diz se a coluna é meia hora ou dois dias de mesa."""

    def somas(self, pagina):
        """O que a linha de total de cada coluna diz -- e não o que os cartões
        de peça dizem. A primeira versão deste teste procurava "5,8 h" na
        página inteira e achava no cartão, com o total apagado."""
        return re.findall(r'class="soma mono">(.*?)</p>', pagina, re.S)

    def test_a_coluna_soma_hora_e_grama(self):
        self.semear()
        somas = self.somas(self.pagina("/producao"))
        self.assertEqual(len(somas), 1, "uma soma, na única coluna com peça")
        self.assertIn("5,8 h", somas[0])
        self.assertIn("84 g", somas[0])

    def test_saem_das_MESMAS_funcoes_que_o_painel_usa(self):
        """A regra do U2, aplicada de novo: número que a tela também mostra
        sai da mesma função. Senão a coluna e o painel discordam."""
        self.semear()
        q = self.d.quadro()
        for etapa, total in q["totais"].items():
            pecas = q["por_etapa"][etapa]
            self.assertEqual(total["pecas"], len(pecas))
            self.assertEqual(total["horas"], self.d.horas_na_mesa(pecas))
            self.assertEqual(total["gramas"], self.d.gramas_na_fila(pecas))

    def test_as_colunas_da_bancada_somam_o_na_mesa_do_painel(self):
        """"A entregar" já saiu da impressora: as horas dela não contam.

        Sem uma peça DEPOIS da bancada, somar tudo e somar só a bancada dão o
        mesmo número -- e o teste passa com a definição errada dos dois lados.
        """
        self.semear()
        cli = self.d.salvar_cliente({"nome": "Bia"}, "samir")
        ped = self.d.salvar_pedido({"cliente_id": cli}, "samir", itens=[
            {"descricao": "Letreiro", "cor": "Rosa", "quantidade": 1,
             "valor_unit": 190, "gramas": 152, "horas": 9.2}])
        self.d.mudar_situacao(ped, "aprovado", "samir")
        peca = self.d.pedido(ped)["itens"][0]["id"]
        self.d.mover_peca(peca, "a entregar", "samir")
        q = self.d.quadro()
        self.assertTrue(q["totais"]["a entregar"]["horas"] > 0,
                        "sem peça em 'a entregar' o teste não separa nada")
        soma = round(sum(q["totais"][e]["horas"] for e in self.d.EM_PRODUCAO), 2)
        self.assertEqual(soma, q["horas_na_mesa"])

    def test_coluna_vazia_nao_mostra_zero_hora_zero_grama(self):
        """"0,0 h · 0 g" é ruído com moldura: o convite é a resposta ali."""
        self.semear()
        pagina = self.pagina("/producao")
        self.assertTrue("0,0 h" not in pagina, "coluna vazia mostrando zero")


class TesteNenhumaTelaFicaMuda(Base):
    """A guarda que impede a próxima tela de nascer muda.

    Com o banco zerado, toda tela do menu tem que ensinar alguma coisa: o que
    ela é, e o que fazer para enchê-la. Não basta não quebrar.
    """

    TELAS = ("/", "/producao", "/pedidos", "/clientes", "/produtos", "/compras",
             "/filamentos", "/insumos", "/templates", "/criar")

    # As marcas de "aqui vai um recado de vazio" que as telas usam.
    ENSINA = ("cartao-vazio", 'class="vazio"', "convite", "nada-encontrado")

    def test_toda_tela_vazia_ensina(self):
        for rota in self.TELAS:
            pagina = self.pagina(rota)
            self.assertTrue(any(m in pagina for m in self.ENSINA),
                            f"{rota}: tela vazia sem nenhum recado")

    def test_o_recado_diz_o_QUE_FAZER_e_nao_so_que_esta_vazio(self):
        """"Nenhum pedido." e um fato. O recado tem que ter uma saida."""
        for rota in ("/pedidos", "/clientes", "/produtos", "/filamentos",
                     "/insumos", "/compras", "/templates"):
            pagina = self.pagina(rota)
            vazio = pagina[pagina.index("cartao-vazio"):]
            vazio = vazio[:vazio.index("</div>") + 6]
            texto = re.sub(r"<[^>]+>", " ", vazio)
            self.assertGreater(len(texto.split()), 12,
                               f"{rota}: o recado de vazio é curto demais para ensinar")

    def test_tela_vazia_nao_mostra_tabela_de_zero_linha(self):
        """Cabeçalho de tabela sem uma linha embaixo é moldura vazia."""
        for rota in ("/pedidos", "/produtos", "/filamentos", "/insumos", "/compras"):
            pagina = self.pagina(rota)
            self.assertTrue("<tbody>" not in pagina, f"{rota}: tabela vazia na tela")


if __name__ == "__main__":
    unittest.main()
