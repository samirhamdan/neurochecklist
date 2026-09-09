# -*- coding: utf-8 -*-
"""Sprint U2 -- o painel responde "como vai o negocio?".

Ate aqui o painel abria com tres avisos e duas listas. Ele contava o que
estava ACONTECENDO -- a fila, os pedidos, o estoque -- e nao dizia como vai.
Os numeros para isso ja existiam no banco; faltava alguem some-los.

Tres coisas precisam ser verdade, e sao o que este arquivo cobra:

  * cada numero do topo bate com a tela para onde ele aponta. Um total somado
    aqui por uma consulta e la por outra passa a discordar no dia em que uma
    das duas ganhar um filtro -- e quem olha nao tem como saber qual vale;
  * painel de sistema recem-instalado nao mostra quatro zeros e um grafico
    vazio: mostra o que fazer primeiro;
  * produto que nao da para custear fica FORA do grafico, e a tela diz
    quantos e por que. Sumir com um produto em silencio e a origem de "o
    grafico esta errado".
"""
from __future__ import annotations

import importlib
import os
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone


def texto_de(pagina: str, ident: str) -> str:
    """O conteudo do elemento com aquele id, sem as etiquetas de dentro."""
    achado = re.search(r'id="%s"[^>]*>(.*?)</' % re.escape(ident), pagina, re.S)
    return re.sub(r"\s+", " ", achado.group(1)).strip() if achado else ""


def valores_com_classe(pagina: str, classe: str) -> list[str]:
    return [re.sub(r"<[^>]+>|\s+", " ", c).strip()
            for c in re.findall(r'class="[^"]*\b%s\b[^"]*"[^>]*>(.*?)</' % classe, pagina, re.S)]


class Base(unittest.TestCase):
    def setUp(self):
        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-painel-")
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

    # ---- semeadura
    def filamento(self, nome="PLA Rosa", cor="Rosa", gramas=800, preco=118, minimo=300):
        return self.d.salvar_filamento(
            {"nome": nome, "cor": cor, "gramas": gramas, "minimo": minimo,
             "preco_kg": preco}, "samir")

    def produto(self, nome, gramas, horas, filamento_id, **extra):
        return self.d.salvar_produto(
            {"nome": nome, "gramas": gramas, "horas": horas,
             "filamento_id": filamento_id, **extra}, "samir")

    def pedido(self, cliente="Ana Paula", valor=140.0, prazo=None, situacao="aprovado",
               comissao=0):
        id_ = self.d.salvar_pedido(
            {"cliente": cliente, "canal": "Instagram", "prazo": prazo, "status": situacao,
             "comissao": comissao},
            "samir", itens=[{"descricao": "Topo", "quantidade": 1, "valor_unit": valor,
                             "gramas": 85, "horas": 3.4}])
        return id_


class TesteOsQuatroNumeros(Base):
    """A regra que faz o painel poder ser acreditado.

    Cada numero e um LINK. O teste segue o link e compara com o total que a
    tela de destino mostra: se os dois discordarem, um dos dois esta mentindo
    e nao ha como saber qual.
    """

    def setUp(self):
        super().setUp()
        self.fil = self.filamento(gramas=800, preco=118)
        self.filamento("PLA Preto", "Preto", gramas=1200, preco=95)
        self.pedido("Ana Paula", 140.0)
        # Com comissao, `valor` e `valor_liquido` sao numeros DIFERENTES. Sem
        # isso, somar a coluna errada dava o mesmo resultado e o teste passava
        # com o defeito dentro.
        self.pedido("Bruno", 320.0, comissao=12)
        self.painel = self.pagina("/")

    def test_a_receber_bate_com_a_tela_de_pedidos(self):
        self.assertEqual(texto_de(self.painel, "v-a-receber"),
                         texto_de(self.pagina("/pedidos"), "total-pedidos"))

    def test_a_receber_e_a_soma_dos_pedidos_abertos(self):
        """Alem de baterem entre si, os dois precisam estar CERTOS."""
        self.assertEqual(texto_de(self.painel, "v-a-receber"), "R$ 460,00")

    def test_na_mesa_bate_com_a_tela_de_producao(self):
        na_mesa = texto_de(self.painel, "v-na-mesa")
        self.assertEqual(na_mesa.replace(" h", ""),
                         texto_de(self.pagina("/producao"), "horas-na-mesa").replace(" h na mesa", ""))

    def test_a_entregar_nao_conta_como_na_mesa(self):
        """A peca que ja saiu da impressora nao ocupa mais a bancada.

        Com todas as pecas ainda aguardando, contar "tudo" e contar "so a
        bancada" dao o MESMO numero -- e o teste de cima passa mesmo com a
        definicao errada dos dois lados.
        """
        peca = self.d.quadro()["pecas"][0]
        antes = texto_de(self.pagina("/"), "v-na-mesa")
        self.d.mover_peca(peca["id"], "imprimindo", "samir")
        self.d.mover_peca(peca["id"], "a entregar", "samir")
        painel = self.pagina("/")
        self.assertNotEqual(texto_de(painel, "v-na-mesa"), antes,
                            "a peca saiu da mesa e o numero nao mudou")
        self.assertEqual(texto_de(painel, "v-na-mesa").replace(" h", ""),
                         texto_de(self.pagina("/producao"), "horas-na-mesa")
                         .replace(" h na mesa", ""))

    def test_parado_em_filamento_bate_com_a_tela_de_filamentos(self):
        self.assertEqual(texto_de(self.painel, "v-parado"),
                         texto_de(self.pagina("/filamentos"), "parado-total"))

    def test_parado_em_filamento_e_gramas_vezes_preco(self):
        # 800 g x R$ 118/kg + 1200 g x R$ 95/kg = 94,40 + 114,00
        self.assertEqual(texto_de(self.painel, "v-parado"), "R$ 208,40")

    def test_rolo_sem_preco_fica_fora_da_conta_e_a_tela_diz(self):
        """Rolo sem preco nao vale zero: vale desconhecido."""
        self.filamento("PLA Azul", "Azul", gramas=1000, preco=None)
        painel = self.pagina("/")
        self.assertEqual(texto_de(painel, "v-parado"), "R$ 208,40")
        self.assertTrue("sem preço" in painel, "o painel precisa dizer quem ficou de fora")
        self.assertTrue("sem preço" in self.pagina("/filamentos"),
                        "a tela de filamentos tambem")

    def test_entregue_no_mes_bate_com_a_tela_que_ele_aponta(self):
        self.d.mudar_situacao(1, "entregue", "samir")
        painel = self.pagina("/")
        self.assertEqual(texto_de(painel, "v-entregue"),
                         texto_de(self.pagina("/pedidos?ver=entregues"), "total-pedidos"))
        self.assertEqual(texto_de(painel, "v-entregue"), "R$ 140,00")

    def test_entregar_tira_de_a_receber_e_poe_no_mes(self):
        antes = texto_de(self.painel, "v-a-receber")
        self.d.mudar_situacao(2, "entregue", "samir")
        depois = self.pagina("/")
        self.assertEqual(antes, "R$ 460,00")
        self.assertEqual(texto_de(depois, "v-a-receber"), "R$ 140,00")
        self.assertEqual(texto_de(depois, "v-entregue"), "R$ 320,00")


class TesteAConversaDoMes(Base):
    """`entregue_em` -- a coluna sem a qual "no mes" nao tem resposta."""

    def test_criado_em_nao_serve_de_data_de_entrega(self):
        """Um pedido de festa entra ate dois meses antes de ser entregue."""
        id_ = self.pedido(valor=200.0)
        with self.d.conectar() as conn:
            conn.execute("UPDATE pedidos SET criado_em = '2026-06-01T12:00:00+00:00'"
                         " WHERE id = ?", (id_,))
            conn.commit()
        self.d.mudar_situacao(id_, "entregue", "samir")
        self.assertEqual(len(self.d.entregues_no_mes()), 1)

    def test_voltar_atras_apaga_a_data(self):
        id_ = self.pedido(valor=200.0)
        self.d.mudar_situacao(id_, "entregue", "samir")
        self.d.mudar_situacao(id_, "aprovado", "samir")
        self.assertEqual(self.d.entregues_no_mes(), [])
        self.assertIsNone(self.d.pedido(id_)["entregue_em"])

    def test_editar_pedido_entregue_nao_move_a_data_da_entrega(self):
        id_ = self.pedido(valor=200.0)
        self.d.mudar_situacao(id_, "entregue", "samir")
        # Uma data de ONTEM: `agora()` tem precisao de segundos, e editar no
        # mesmo segundo da entrega daria o mesmo carimbo mesmo sem o COALESCE.
        antes = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(timespec="seconds")
        with self.d.conectar() as conn:
            conn.execute("UPDATE pedidos SET entregue_em = ? WHERE id = ?", (antes, id_))
            conn.commit()
        self.d.salvar_pedido({"cliente": "Ana Paula", "canal": "Instagram",
                              "status": "entregue"}, "samir", id_=id_,
                             itens=[{"descricao": "Topo", "quantidade": 1,
                                     "valor_unit": 200.0}])
        self.assertEqual(self.d.pedido(id_)["entregue_em"], antes)

    def test_o_mes_vira_a_meia_noite_DAQUI_e_nao_em_UTC(self):
        """Uma entrega das 21h de 31 de agosto esta gravada como 1º de setembro.

        Comparar o texto cru do carimbo jogaria essa venda no mes seguinte --
        e o fechamento do mes sairia errado exatamente nas vendas da noite.
        """
        inicio, _ = self.d.limites_do_mes(datetime(2026, 9, 15).date())
        self.assertEqual(inicio, "2026-09-01T04:00:00+00:00")

    def test_dezembro_vira_janeiro_do_ano_seguinte(self):
        _, fim = self.d.limites_do_mes(datetime(2026, 12, 10).date())
        self.assertEqual(fim, "2027-01-01T04:00:00+00:00")

    def test_pedido_entregue_nao_aparece_como_atrasado(self):
        """Acabou. Marcar de vermelho o prazo de quem ja recebeu e susto a toa."""
        from sistema import formato
        ontem = (formato.hoje() - timedelta(days=6)).isoformat()
        id_ = self.pedido(valor=190.0, prazo=ontem)
        self.d.mudar_situacao(id_, "entregue", "samir")
        tela = self.pagina("/pedidos?ver=entregues")
        self.assertTrue("atrasado" not in tela, "pedido entregue nao esta atrasado")
        self.assertTrue("Entregue em" in tela, "a coluna passa a mostrar a data da entrega")

    def test_entrega_do_mes_passado_nao_conta(self):
        self.filamento()          # senao o painel fica vazio e nem mostra o placar
        id_ = self.pedido(valor=200.0)
        self.d.mudar_situacao(id_, "entregue", "samir")
        passado = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()
        with self.d.conectar() as conn:
            conn.execute("UPDATE pedidos SET entregue_em = ? WHERE id = ?", (passado, id_))
            conn.commit()
        self.assertEqual(self.d.entregues_no_mes(), [])
        self.assertEqual(texto_de(self.pagina("/"), "v-entregue"), "R$ 0,00")


class TesteOGrafico(Base):
    """Retorno por hora de impressora -- a comparacao que decide.

    A impressora e uma so. A peca que ocupa ela doze horas impede todas as
    outras, mesmo com margem boa por peca.
    """

    def setUp(self):
        super().setUp()
        self.fil = self.filamento(preco=118)
        self.chaveiro = self.produto("Chaveiro", 9, 0.4, self.fil, minutos=5)
        self.topo = self.produto("Topo de bolo", 83.7, 5.77, self.fil, minutos=30)

    def test_ordenado_do_maior_retorno_para_o_menor(self):
        from sistema import custo
        r = custo.retorno_por_hora(self.d.produtos(), self.d.parametros())
        nomes = [i["nome"] for i in r["itens"]]
        valores = [i["conta"].por_hora for i in r["itens"]]
        self.assertEqual(nomes, ["Chaveiro", "Topo de bolo"])
        self.assertEqual(valores, sorted(valores, reverse=True))

    def test_o_chaveiro_paga_a_hora_melhor_que_o_topo(self):
        """O numero que motivou o grafico: margem por peca engana."""
        from sistema import custo
        r = custo.retorno_por_hora(self.d.produtos(), self.d.parametros())
        por_nome = {i["nome"]: i["conta"] for i in r["itens"]}
        self.assertGreater(por_nome["Topo de bolo"].margem, por_nome["Chaveiro"].margem)
        self.assertGreater(por_nome["Chaveiro"].por_hora, por_nome["Topo de bolo"].por_hora)

    def test_produto_sem_preco_de_filamento_fica_de_fora_e_a_tela_diz_por_que(self):
        """A mesma regra do `Conta.completo`.

        Sem o preco do filamento falta a MAIOR parcela do custo. Um chaveiro
        de 9 g apareceria com 94% de margem -- e com um retorno por hora que
        nao existe.
        """
        self.produto("Sem filamento", 40, 2.0, None)
        from sistema import custo
        r = custo.retorno_por_hora(self.d.produtos(), self.d.parametros())
        self.assertEqual([i["nome"] for i in r["itens"]], ["Chaveiro", "Topo de bolo"])
        self.assertEqual(len(r["sem_filamento"]), 1)

        painel = self.pagina("/")
        self.assertTrue("Sem filamento" not in painel, "produto sem custo nao entra no gráfico")
        self.assertTrue("preço por kg do filamento" in painel,
                        "a tela precisa dizer POR QUE ele ficou de fora")

    def test_produto_sem_horas_medidas_fica_de_fora(self):
        """Dividir por zero hora nao da numero nenhum."""
        self.produto("Sem tempo", 40, 0, self.fil)
        from sistema import custo
        r = custo.retorno_por_hora(self.d.produtos(), self.d.parametros())
        self.assertEqual(len(r["sem_horas"]), 1)
        self.assertTrue("tempo de impressão medido" in self.pagina("/"))

    def test_o_grafico_bate_com_a_coluna_da_tela_de_produtos(self):
        """O mesmo numero, pela mesma conta, nas duas telas."""
        no_painel = set(valores_com_classe(self.pagina("/"), "por-hora"))
        na_lista = set(valores_com_classe(self.pagina("/produtos"), "por-hora"))
        self.assertTrue(no_painel, "o grafico precisa ter barras")
        self.assertTrue(no_painel <= na_lista, f"{no_painel} nao esta em {na_lista}")

    def test_preco_digitado_manda_na_margem_e_no_retorno(self):
        """A coluna Preco mostrava um numero e a Margem era feita sobre outro."""
        from sistema import custo
        self.d.salvar_produto({"nome": "Topo de bolo", "gramas": 83.7, "horas": 5.77,
                               "filamento_id": self.fil, "minutos": 30, "preco": 150},
                              "samir", id_=self.topo)
        param = self.d.parametros()
        prod = self.d.produto(self.topo)
        sugerido = custo.conta_de_produto(prod, param)
        cobrado = sugerido.com_preco(prod["preco"])
        self.assertEqual(sugerido.preco, 70.0)
        self.assertEqual(cobrado.preco, 150.0)
        self.assertGreater(cobrado.por_hora, sugerido.por_hora)

    def test_prejuizo_por_hora_cresce_para_a_esquerda_do_zero(self):
        """Peca que nao paga a hora que ocupa e o caso que o grafico existe para achar."""
        from sistema import custo
        caro = self.produto("Peça longa", 20, 40.0, self.fil, minutos=120)
        r = custo.retorno_por_hora(self.d.produtos(), self.d.parametros())
        por_nome = {i["nome"]: i for i in r["itens"]}
        self.assertLess(por_nome["Peça longa"]["conta"].por_hora, 0)
        self.assertTrue(r["tem_prejuizo"])
        # A barra do prejuizo termina onde o zero comeca.
        item = por_nome["Peça longa"]
        self.assertAlmostEqual(item["esquerda"] + item["largura"], r["zero"], places=1)
        self.assertTrue("perde" in self.pagina("/"), "a barra do prejuizo tem cor propria")
        del caro

    def test_a_tabela_do_leitor_de_tela_traz_os_mesmos_produtos(self):
        """Cor e comprimento de barra nao chegam a quem usa leitor de tela."""
        painel = self.pagina("/")
        tabela = painel[painel.index('class="so-leitor"'):painel.index("</table>")]
        for nome in ("Chaveiro", "Topo de bolo"):
            self.assertTrue(nome in tabela, f"{nome} fora da tabela do leitor")


class TestePainelVazio(Base):
    """Sistema recem-instalado nao mostra quatro zeros e um grafico vazio."""

    def test_sem_nada_cadastrado_ensina_o_que_fazer(self):
        painel = self.pagina("/")
        self.assertTrue("Ainda não há nada registrado" in painel)
        self.assertTrue('class="placar"' not in painel, "zero nao e resposta para quem nao comecou")
        self.assertTrue("R$ 0,00" not in painel, "quatro zeros nao ensinam nada")

    def test_sem_produto_medido_nao_ha_grafico(self):
        """Grafico de zero barras e ruido com moldura."""
        self.filamento()
        self.assertTrue("Retorno por hora" not in self.pagina("/"))


class TesteAvisosPorUrgencia(Base):
    """Ordenados por urgencia, nao por tipo.

    A versao anterior tinha tres blocos por TIPO: senha, todo atraso, todo
    filamento baixo. Um rolo ZERADO -- que para a impressora agora, no meio de
    uma peca -- aparecia embaixo de um pedido que atrasou ontem.
    """

    def ontem(self, dias=1):
        from sistema import formato
        return (formato.hoje() - timedelta(days=dias)).isoformat()

    def test_rolo_zerado_vem_antes_de_pedido_atrasado(self):
        self.filamento("PLA Rosa", "Rosa", gramas=0, preco=118)
        self.pedido("Ana Paula", 140.0, prazo=self.ontem())
        tipos = [a["tipo"] for a in self.d.resumo()["avisos"]]
        self.assertEqual(tipos, ["filamento_zero", "atraso"])

    def test_pedido_atrasado_vem_antes_de_rolo_acabando(self):
        self.filamento("PLA Rosa", "Rosa", gramas=100, minimo=300, preco=118)
        self.pedido("Ana Paula", 140.0, prazo=self.ontem())
        tipos = [a["tipo"] for a in self.d.resumo()["avisos"]]
        self.assertEqual(tipos, ["atraso", "filamento"])

    def test_o_atraso_maior_vem_primeiro(self):
        self.pedido("Atrasou pouco", 100.0, prazo=self.ontem(1))
        self.pedido("Atrasou muito", 100.0, prazo=self.ontem(9))
        nomes = [a["item"]["cliente"] for a in self.d.resumo()["avisos"]]
        self.assertEqual(nomes, ["Atrasou muito", "Atrasou pouco"])

    def test_o_rolo_mais_vazio_vem_primeiro(self):
        self.filamento("Quase cheio", "Rosa", gramas=280, minimo=300, preco=118)
        self.filamento("Quase vazio", "Azul", gramas=30, minimo=300, preco=118)
        nomes = [a["item"]["nome"] for a in self.d.resumo()["avisos"]]
        self.assertEqual(nomes, ["Quase vazio", "Quase cheio"])

    def test_a_ordem_do_banco_nao_manda_na_ordem_do_aviso(self):
        """O rolo zerado entra por ULTIMO no cadastro e sai em primeiro."""
        self.pedido("Ana Paula", 140.0, prazo=self.ontem(9))
        self.filamento("PLA Rosa", "Rosa", gramas=0, preco=118)
        self.assertEqual(self.d.resumo()["avisos"][0]["tipo"], "filamento_zero")

    def test_cada_aviso_leva_a_tela_que_resolve(self):
        self.filamento("PLA Rosa", "Rosa", gramas=0, preco=118)
        self.pedido("Ana Paula", 140.0, prazo=self.ontem())
        painel = self.pagina("/")
        bloco = painel[painel.index('class="avisos"'):painel.index('class="placar"')]
        self.assertTrue('href="/filamentos"' in bloco)
        self.assertTrue('href="/pedidos"' in bloco)


class TesteCriarNaoParaNoTempo(Base):
    """A secao Criar do painel listava dois geradores. O catalogo tem nove."""

    def test_a_secao_sai_do_mesmo_catalogo_da_tela_criar(self):
        from sistema import criar
        self.pedido()                       # tira o painel do estado vazio
        painel = self.pagina("/")
        no_ar = [m for m in criar.MODELOS if m.rota]
        for m in no_ar:
            self.assertTrue(m.nome in painel, f"{m.nome} nao aparece no painel")
        self.assertEqual(len(re.findall(r'class="atalho[ "]', painel)), len(no_ar),
                         "um cartao por modelo no ar, nem mais nem menos")

    def test_modelo_sem_gerador_nao_vira_botao(self):
        """Botao que nao leva a lugar nenhum e pior do que ausencia de botao."""
        from sistema import criar
        self.pedido()
        painel = self.pagina("/")
        for m in criar.MODELOS:
            if not m.rota:
                self.assertTrue(f'>{m.nome}</b>' not in painel, f"{m.nome} nao tem rota")


if __name__ == "__main__":
    unittest.main()
