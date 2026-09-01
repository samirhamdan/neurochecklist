import unittest

from morumbi3d.mesh import RelatorioMalha
from morumbi3d.pricing import _arredondar_comercial, orcar

from .ajuda import config_temporaria


class TestePreco(unittest.TestCase):
    def setUp(self):
        self.cfg = config_temporaria()

    def test_formula_bate_com_a_conta_na_mao(self):
        rel = RelatorioMalha(material_g=100.0, tempo_h=4.0)
        orc = orcar(rel, self.cfg)
        # material: 0,100 kg * 120 = 12,00 | maquina: 4 * 3,50 = 14,00
        self.assertAlmostEqual(orc.custo_material, 12.00, places=2)
        self.assertAlmostEqual(orc.custo_maquina, 14.00, places=2)
        self.assertAlmostEqual(orc.custo_falha, 2.60, places=2)  # 10% de 26
        self.assertAlmostEqual(orc.custo_total, 30.10, places=2)  # + 1,50 fixo
        self.assertGreater(orc.preco_sugerido, orc.custo_total)
        self.assertAlmostEqual(
            orc.margem_reais, orc.preco_sugerido - orc.custo_total, places=2
        )

    def test_quantidade_multiplica(self):
        rel = RelatorioMalha(material_g=50.0, tempo_h=2.0)
        um = orcar(rel, self.cfg, 1)
        dez = orcar(rel, self.cfg, 10)
        self.assertAlmostEqual(dez.material_g, um.material_g * 10, places=1)
        self.assertGreater(dez.custo_total, um.custo_total * 9)

    def test_arredondamento_comercial_nunca_fica_abaixo(self):
        for valor in (0.5, 5.0, 12.34, 19.95, 20.0, 37.42, 41.0, 44.90, 100.0, 249.99):
            with self.subTest(valor=valor):
                preco = _arredondar_comercial(valor)
                self.assertGreaterEqual(preco, valor)
                self.assertAlmostEqual(preco % 1, 0.90, places=2)

    def test_valor_zero(self):
        self.assertEqual(_arredondar_comercial(0), 0.0)
        self.assertEqual(orcar(RelatorioMalha(), self.cfg).custo_material, 0.0)

    def test_filamento_mais_caro_aumenta_o_preco(self):
        rel = RelatorioMalha(material_g=100.0, tempo_h=4.0)
        barato = orcar(rel, self.cfg)
        self.cfg.custo.preco_filamento_kg = 300.0
        caro = orcar(rel, self.cfg)
        self.assertGreater(caro.preco_sugerido, barato.preco_sugerido)


if __name__ == "__main__":
    unittest.main()
