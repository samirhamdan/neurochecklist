import unittest

from morumbi3d.mesh import ArquivoInvalido, analisar_arquivo, carregar_triangulos

from .ajuda import (
    config_temporaria, cubo, escrever_3mf, escrever_stl_ascii, escrever_stl_binario,
)


class TesteLeitura(unittest.TestCase):
    def setUp(self):
        self.cfg = config_temporaria()
        self.dir = self.cfg.raiz

    def test_stl_binario_e_ascii_dao_o_mesmo_resultado(self):
        b = analisar_arquivo(escrever_stl_binario(self.dir / "b.stl", cubo()), self.cfg)
        a = analisar_arquivo(escrever_stl_ascii(self.dir / "a.stl", cubo()), self.cfg)
        self.assertEqual(b.triangulos, a.triangulos)
        self.assertEqual(b.volume_cm3, a.volume_cm3)
        self.assertEqual(b.dimensoes_mm, a.dimensoes_mm)

    def test_3mf(self):
        rel = analisar_arquivo(escrever_3mf(self.dir / "c.3mf", cubo()), self.cfg)
        self.assertTrue(rel.fechada)
        self.assertEqual(rel.dimensoes_mm, (20.0, 20.0, 20.0))
        self.assertEqual(rel.formato, "3mf")

    def test_formato_nao_suportado(self):
        alvo = self.dir / "x.gcode"
        alvo.write_text("nao e malha")
        with self.assertRaises(ArquivoInvalido):
            carregar_triangulos(alvo)

    def test_arquivo_inexistente(self):
        with self.assertRaises(ArquivoInvalido):
            carregar_triangulos(self.dir / "nao-existe.stl")

    def test_stl_binario_truncado(self):
        alvo = escrever_stl_binario(self.dir / "t.stl", cubo())
        dados = alvo.read_bytes()
        alvo.write_bytes(dados[: len(dados) - 60])  # some 1 triangulo
        with self.assertRaises(ArquivoInvalido):
            carregar_triangulos(alvo)


class TesteAnalise(unittest.TestCase):
    def setUp(self):
        self.cfg = config_temporaria()
        self.dir = self.cfg.raiz

    def analisar(self, triangulos, nome="m.stl"):
        return analisar_arquivo(escrever_stl_binario(self.dir / nome, triangulos), self.cfg)

    def test_cubo_fechado(self):
        rel = self.analisar(cubo(20.0))
        self.assertTrue(rel.fechada)
        self.assertEqual(rel.arestas_abertas, 0)
        self.assertEqual(rel.partes_soltas, 1)
        self.assertAlmostEqual(rel.volume_cm3, 8.0, places=2)  # 2cm x 2cm x 2cm
        self.assertAlmostEqual(rel.area_cm2, 24.0, places=1)

    def test_malha_aberta_vira_problema(self):
        rel = self.analisar(cubo()[:-1], "aberto.stl")
        self.assertFalse(rel.fechada)
        self.assertEqual(rel.arestas_abertas, 3)
        self.assertTrue(any("aberta" in p for p in rel.problemas))
        self.assertLess(rel.nota, 90)

    def test_partes_soltas(self):
        rel = self.analisar(cubo(20.0) + cubo(10.0, (60, 0, 0)), "duas.stl")
        self.assertEqual(rel.partes_soltas, 2)
        self.assertTrue(any("partes soltas" in a for a in rel.alertas))

    def test_face_apoiada_na_mesa_nao_conta_como_balanco(self):
        rel = self.analisar(cubo(20.0), "apoiado.stl")
        self.assertEqual(rel.balanco_ratio, 0.0)
        self.assertEqual(rel.suporte, "nenhum")

    def test_balanco_real_pede_suporte(self):
        # bloco no chao + bloco deslocado no alto: o de cima fica em balanco
        rel = self.analisar(
            cubo(10.0) + cubo(10.0, (0, 0, 20)) + cubo(10.0, (-10, 0, 20)), "t.stl"
        )
        self.assertGreater(rel.balanco_ratio, 0.05)
        self.assertIn(rel.suporte, ("moderado", "muito"))
        self.assertGreater(rel.volume_suporte_cm3, 0.0)

    def test_nao_cabe_na_mesa(self):
        rel = self.analisar(cubo(400.0), "grande.stl")
        self.assertFalse(rel.cabe_na_mesa)
        self.assertLess(rel.escala_sugerida, 1.0)
        self.assertTrue(any("nao cabe" in p for p in rel.problemas))

    def test_cabe_girando_na_diagonal(self):
        # 280 x 40 nao cabe reto (280 > 253) mas cabe girado 45 graus:
        # (280 + 40) / raiz(2) = 226 mm de cada lado.
        rel = self.analisar(
            [
                ((0, 0, 0), (280, 0, 0), (280, 40, 0)),
                ((0, 0, 0), (280, 40, 0), (0, 40, 0)),
            ],
            "diagonal.stl",
        )
        self.assertFalse(rel.cabe_na_mesa)
        self.assertTrue(rel.cabe_girando)
        self.assertIn("diagonal", " ".join(rel.problemas))

    def test_muito_grande_nao_cabe_nem_girando(self):
        rel = self.analisar(cubo(400.0), "enorme.stl")
        self.assertFalse(rel.cabe_na_mesa)
        self.assertFalse(rel.cabe_girando)

    def test_material_cresce_com_o_preenchimento(self):
        leve = self.analisar(cubo(50.0), "leve.stl")
        self.cfg.impressora.preenchimento = 0.9
        pesado = self.analisar(cubo(50.0), "pesado.stl")
        self.assertGreater(pesado.material_g, leve.material_g)

    def test_malha_vazia(self):
        rel = self.analisar([], "vazio.stl")
        self.assertEqual(rel.triangulos, 0)
        self.assertTrue(rel.problemas)


if __name__ == "__main__":
    unittest.main()
