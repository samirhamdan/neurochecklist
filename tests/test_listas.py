# -*- coding: utf-8 -*-
"""Sprint U3 -- ordenar e buscar nas listas que crescem.

Numa lista de oito linhas a ordem do banco basta. Em oitenta, a pergunta muda
toda semana -- "qual pedido esta mais atrasado" hoje, "qual produto paga
melhor a hora" depois -- e rolar procurando e o que faz o sistema deixar de
ser usado.

Duas regras deste arquivo valem mais que as outras:

  * o VAZIO vai para o fim nos dois sentidos. "Sem prazo" nao e o prazo mais
    urgente nem o menos urgente: ele nao tem prazo, e no meio da lista ele
    esconde justamente os que tem;
  * a busca ignora acento. Quem digita no telefone, com uma mao, no meio de
    uma festa, nao poe acento -- e busca que exige acento e busca que nao
    encontra.
"""
from __future__ import annotations

import unittest

from sistema import listas

ORDENS = (
    ("nome", "Nome", "nome"),
    ("valor", "Valor", "valor"),
    ("calculado", "Calculado", lambda i: i["valor"] * 2 if i["valor"] else None),
)

ITENS = [
    {"nome": "Ávila", "valor": 30},
    {"nome": "banana", "valor": 10},
    {"nome": None, "valor": 20},
    {"nome": "Cebola", "valor": None},
]


class TesteOrdenar(unittest.TestCase):
    def nomes(self, chave, invertido=False, itens=None):
        return [i["nome"] for i in listas.ordenar(itens or ITENS, chave, invertido, ORDENS)]

    def test_texto_ignora_caixa_e_acento(self):
        """Senao "Ávila" cai depois de "banana", porque À vem depois de z."""
        self.assertEqual(self.nomes("nome"), ["Ávila", "banana", "Cebola", None])

    def test_numero_ordena_como_numero(self):
        self.assertEqual([i["valor"] for i in listas.ordenar(ITENS, "valor", False, ORDENS)],
                         [10, 20, 30, None])

    def test_o_vazio_vai_para_o_fim_NOS_DOIS_SENTIDOS(self):
        """A regra que o `reverse=True` sozinho nao consegue dar."""
        self.assertIsNone(self.nomes("nome")[-1])
        self.assertIsNone(self.nomes("nome", invertido=True)[-1])
        self.assertIsNone(listas.ordenar(ITENS, "valor", True, ORDENS)[-1]["valor"])

    def test_inverter_vira_so_o_que_tem_valor(self):
        self.assertEqual(self.nomes("nome", invertido=True), ["Cebola", "banana", "Ávila", None])

    def test_ordem_desconhecida_nao_mexe_na_lista(self):
        """Chave vinda da URL nao pode virar ORDER BY -- nem erro de tela."""
        self.assertEqual(self.nomes("apagar_tudo"), self.nomes(""))
        self.assertEqual(listas.ordenar(ITENS, "nao_existe", False, ORDENS), ITENS)

    def test_campo_que_EXISTE_mas_nao_esta_na_lista_tambem_nao_ordena(self):
        """A versao fraca deste teste usava um campo inventado.

        Chave inventada nao ordena por acidente: ela e nula em toda linha, e
        toda linha vai junta para o fim. O que a lista de permitidos protege
        e o campo que EXISTE no banco e nao devia sair na URL -- quem
        cadastrou, quando, o id interno.
        """
        itens = [{"nome": "A", "criado_por": "zeca"}, {"nome": "B", "criado_por": "ana"}]
        ordens = (("nome", "Nome", "nome"),)
        self.assertEqual([i["nome"] for i in listas.ordenar(itens, "criado_por", False, ordens)],
                         ["A", "B"])

    def test_ordena_por_valor_calculado(self):
        self.assertEqual([i["valor"] for i in listas.ordenar(ITENS, "calculado", True, ORDENS)],
                         [30, 20, 10, None])

    def test_nao_estraga_a_lista_de_origem(self):
        antes = list(ITENS)
        listas.ordenar(ITENS, "nome", True, ORDENS)
        self.assertEqual(ITENS, antes)


class TesteBuscar(unittest.TestCase):
    def nomes(self, termo, campos=("nome",)):
        return [i["nome"] for i in listas.filtrar(ITENS, termo, campos)]

    def test_acento_nao_atrapalha_dos_dois_lados(self):
        self.assertEqual(self.nomes("avila"), ["Ávila"])
        self.assertEqual(self.nomes("Ávila"), ["Ávila"])

    def test_caixa_nao_atrapalha(self):
        self.assertEqual(self.nomes("CEBOLA"), ["Cebola"])

    def test_pedaco_no_meio_conta(self):
        self.assertEqual(self.nomes("nan"), ["banana"])

    def test_termo_vazio_nao_filtra(self):
        self.assertEqual(len(listas.filtrar(ITENS, "", ("nome",))), len(ITENS))
        self.assertEqual(len(listas.filtrar(ITENS, "   ", ("nome",))), len(ITENS))

    def test_campo_vazio_nao_quebra(self):
        """Uma linha com o campo nulo nao pode derrubar a tela de busca."""
        self.assertEqual(self.nomes("a"), ["Ávila", "banana", "Cebola"])

    def test_busca_em_mais_de_um_campo(self):
        itens = [{"nome": "Topo", "sku": "M3D-TB-001"}, {"nome": "Chaveiro", "sku": "M3D-CH-001"}]
        achados = listas.filtrar(itens, "tb-001", ("nome", "sku"))
        self.assertEqual([i["nome"] for i in achados], ["Topo"])


class TesteOPedidoDaURL(unittest.TestCase):
    def test_so_aceita_ordem_que_existe(self):
        self.assertEqual(listas.pedido_da_url({"ordem": "nome"}, ORDENS), ("nome", False))
        self.assertEqual(listas.pedido_da_url({"ordem": ";DROP"}, ORDENS), ("", False))

    def test_dir_desc_inverte_e_o_resto_nao(self):
        self.assertTrue(listas.pedido_da_url({"ordem": "nome", "dir": "desc"}, ORDENS)[1])
        self.assertFalse(listas.pedido_da_url({"ordem": "nome", "dir": "asc"}, ORDENS)[1])
        self.assertFalse(listas.pedido_da_url({"ordem": "nome", "dir": "xis"}, ORDENS)[1])


class TesteAsOrdensDeCadaTela(unittest.TestCase):
    """As listas de ordem sao dado, e o dado tem que estar inteiro."""

    TODAS = (listas.ORDENS_PEDIDOS, listas.ORDENS_PRODUTOS, listas.ORDENS_GERACOES)

    def test_toda_ordem_tem_chave_rotulo_e_campo(self):
        for ordens in self.TODAS:
            for chave, rotulo, campo in ordens:
                self.assertTrue(chave and rotulo and campo, f"{chave} incompleta")

    def test_nenhuma_chave_repetida(self):
        for ordens in self.TODAS:
            chaves = [c for c, _, _ in ordens]
            self.assertEqual(len(chaves), len(set(chaves)), chaves)


if __name__ == "__main__":
    unittest.main()
