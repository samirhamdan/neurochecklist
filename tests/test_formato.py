# -*- coding: utf-8 -*-
"""Sprint U2 -- numero e data do jeito que se le aqui.

Desde a primeira tela o sistema escrevia `R$ 1120.00` e `2026-09-08`. As duas
sao a convencao de MAQUINA, e nenhuma e como o Samir le um valor no meio de
uma festa. O levantamento de interface listou as duas como defeito.

O ultimo teste deste arquivo e o que impede a reincidencia: ele varre os
templates atras do padrao antigo. Sem ele, a proxima tela nasce com ponto de
novo -- foi assim que quatorze telas ficaram erradas.
"""
from __future__ import annotations

import os
import re
import unittest
from datetime import date, datetime, timezone

from sistema import formato

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = os.path.join(RAIZ, "sistema", "templates")


class TesteDinheiro(unittest.TestCase):
    def test_milhar_com_ponto_e_decimal_com_virgula(self):
        self.assertEqual(formato.dinheiro(1120), "R$ 1.120,00")
        self.assertEqual(formato.dinheiro(1234567.891), "R$ 1.234.567,89")
        self.assertEqual(formato.dinheiro(0.6), "R$ 0,60")

    def test_a_troca_e_posicional_e_nao_uma_substituicao_cega(self):
        """`.replace(",", ".")` sozinho faria 1,120.50 virar 1.120.50."""
        self.assertEqual(formato.dinheiro(1120.5), "R$ 1.120,50")

    def test_o_sinal_vem_antes_do_cifrao(self):
        """`R$ -5,00` nao existe em portugues."""
        self.assertEqual(formato.dinheiro(-5.5), "-R$ 5,50")

    def test_vazio_nao_e_zero(self):
        """Produto sem preco de filamento tem custo DESCONHECIDO.

        Escrever `R$ 0,00` ali faria a margem parecer de 100% -- que e o tipo
        de numero que leva a baixar o preco de um produto que da prejuizo.
        """
        self.assertEqual(formato.dinheiro(None), "—")
        self.assertEqual(formato.dinheiro(""), "—")
        self.assertEqual(formato.dinheiro("nao e numero"), "—")
        self.assertEqual(formato.dinheiro(0), "R$ 0,00")


class TesteData(unittest.TestCase):
    def test_dia_na_frente(self):
        self.assertEqual(formato.data("2026-09-08"), "08/09/2026")
        self.assertEqual(formato.data(date(2026, 1, 31)), "31/01/2026")
        self.assertEqual(formato.data(None), "—")
        self.assertEqual(formato.data("nem data"), "—")

    def test_carimbo_utc_vira_hora_daqui(self):
        """O banco grava em UTC; a tela mostra o relogio de Campo Grande.

        Mostrar UTC com cara de hora local erra por quatro horas: uma geracao
        das 22h de terca aparece como quarta-feira.
        """
        self.assertEqual(formato.datahora("2026-09-09T01:30:00+00:00"), "08/09/2026 21:30")

    def test_carimbo_antigo_sem_fuso_e_lido_como_utc(self):
        """Era o que `agora()` gravava antes de ganhar o fuso."""
        self.assertEqual(formato.datahora("2026-09-08T14:03:11"), "08/09/2026 10:03")

    def test_a_conversao_nao_e_um_recorte_de_texto(self):
        """A versao anterior era `criado_em[:16].replace('T', ' ')`.

        Ela nao erra o formato -- erra o FUSO, em silencio, e so nas horas
        depois das 20h. Aqui a mesma entrada tem que trocar de DIA.
        """
        cru = "2026-09-09T02:00:00+00:00"
        self.assertEqual(cru[:16].replace("T", " "), "2026-09-09 02:00")
        self.assertEqual(formato.datahora(cru), "08/09/2026 22:00")

    def test_hoje_e_a_data_daqui(self):
        agora_utc = datetime.now(timezone.utc)
        self.assertEqual(formato.hoje(), agora_utc.astimezone(formato.AQUI).date())


class TesteNumero(unittest.TestCase):
    def test_casas_pedidas(self):
        self.assertEqual(formato.numero(11.5, 1), "11,5")
        self.assertEqual(formato.numero(120, 0), "120")
        self.assertEqual(formato.numero(1234.5, 1), "1.234,5")


class TesteNenhumaTelaVoltaAoPadraoDeMaquina(unittest.TestCase):
    """A guarda que impede a reincidencia.

    Nao basta consertar as vinte telas de hoje: a de amanha nasce copiada de
    uma delas. Entao o padrao antigo fica proibido no repositorio.
    """

    # `<input type="number">` SO aceita ponto decimal -- e o navegador que le,
    # nao o Samir. Por isso o valor de campo continua em formato de maquina.
    CAMPO = re.compile(r"value=\"[^\"]*\{\{[^}]*%\.\df[^}]*\}\}")

    def paginas(self):
        for nome in sorted(os.listdir(TEMPLATES)):
            if nome.endswith(".html"):
                caminho = os.path.join(TEMPLATES, nome)
                with open(caminho, encoding="utf-8") as fh:
                    yield nome, fh.read()

    def test_nenhum_valor_em_reais_sai_por_format(self):
        for nome, corpo in self.paginas():
            sem_campos = self.CAMPO.sub("", corpo)
            achado = re.search(r"R\$[^<{]{0,4}\{\{[^}]*%\.2f", sem_campos)
            self.assertIsNone(
                achado, f"{nome}: use o filtro |dinheiro em vez de '%.2f'|format")

    def test_nenhuma_data_sai_crua(self):
        """`{{ x.criado_em[:16] }}` e o recorte que erra o fuso em silencio."""
        for nome, corpo in self.paginas():
            self.assertTrue("criado_em[" not in corpo,
                            f"{nome}: use o filtro |datahora em vez de recortar o texto")

    def test_o_navegador_formata_igual_a_tela_servida(self):
        """Total recalculado ao vivo tem que casar com o que o servidor mandou.

        As telas de pedido e de compra somam os itens no navegador. Com
        `toFixed(2)` o rodape mostrava `R$ 1120.00` embaixo de linhas escritas
        `R$ 1.120,00` -- na mesma tabela.
        """
        for nome, corpo in self.paginas():
            self.assertTrue("toFixed(2)" not in corpo,
                            f"{nome}: use toLocaleString('pt-BR') para o total ao vivo")


if __name__ == "__main__":
    unittest.main()
