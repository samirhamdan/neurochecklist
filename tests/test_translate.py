import unittest

from morumbi3d.lines import classificar
from morumbi3d.translate import expandir

from .ajuda import config_temporaria


class TesteTraducao(unittest.TestCase):
    def test_termo_conhecido_vira_variantes_em_ingles(self):
        variantes = expandir("churrasco")
        self.assertEqual(variantes[0], "churrasco", "o original vem primeiro")
        self.assertIn("barbecue", variantes)
        self.assertIn("bbq", variantes)

    def test_frase_composta(self):
        self.assertIn("key holder", expandir("porta-chaves"))
        self.assertIn("cake topper", expandir("topo de bolo"))

    def test_conectivos_somem_na_traducao(self):
        variantes = expandir("suporte de celular")
        self.assertIn("phone stand", variantes)
        self.assertNotIn("holder de celular", variantes)

    def test_termo_desconhecido_volta_sozinho(self):
        self.assertEqual(expandir("xyzabc"), ["xyzabc"])

    def test_vazio(self):
        self.assertEqual(expandir("  "), [])

    def test_limite_de_variantes(self):
        self.assertLessEqual(len(expandir("churrasco", maximo=3)), 3)

    def test_dicionario_do_usuario(self):
        cfg = config_temporaria()
        (cfg.raiz / "dicionario.txt").write_text(
            "cuia = mate gourd, yerba mate cup\n", encoding="utf-8"
        )
        self.assertIn("mate gourd", expandir("cuia", cfg.raiz))


class TesteLinhas(unittest.TestCase):
    def test_classificacao_por_titulo(self):
        casos = [
            ("Porta-tempero para churrasqueira", "Adultos", "Churrasco"),
            ("Cake topper unicorn birthday", "Infantil", "Festa Infantil"),
            ("Vaso para suculenta", "Casa e Decoracao", "Vasos e Plantas"),
            ("Trofeu de futebol", "Adultos", "Futebol"),
            ("Wedding cake topper noivos", "Social", "Casamento"),
        ]
        for titulo, linha, colecao in casos:
            with self.subTest(titulo=titulo):
                self.assertEqual(classificar(titulo)[:2], (linha, colecao))

    def test_sem_pista_fica_sem_linha(self):
        self.assertEqual(classificar("Coisa aleatoria xyz")[0], "Sem linha")

    def test_titulo_pesa_mais_que_descricao(self):
        linha, _, pontos = classificar("Vaso decorativo", "otimo para churrasco tambem")
        self.assertEqual(linha, "Casa e Decoracao")
        self.assertGreater(pontos, 0)


if __name__ == "__main__":
    unittest.main()
