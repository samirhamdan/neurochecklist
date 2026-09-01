import unittest

from morumbi3d.licensing import (
    DESCONHECIDO, PERMITIDO, PROIBIDO, avaliar_risco, classificar,
    motivo_bloqueio, seguro_para_venda,
)

from .ajuda import config_temporaria


class TesteClassificacao(unittest.TestCase):
    def test_matriz_de_licencas(self):
        casos = [
            ("CC0 1.0 Universal", "CC0", PERMITIDO, False),
            ("Creative Commons - Attribution", "CC-BY", PERMITIDO, True),
            ("CC BY-SA 4.0", "CC-BY-SA", PERMITIDO, True),
            ("Creative Commons - Attribution - Non-Commercial", "CC-BY-NC", PROIBIDO, True),
            ("CC BY-NC-SA 4.0", "CC-BY-NC-SA", PROIBIDO, True),
            ("CC BY-NC-ND", "CC-BY-NC-ND", PROIBIDO, True),
            ("Creative Commons - Attribution - No Derivatives", "CC-BY-ND", PERMITIDO, True),
            ("GNU GPL v3", "GPL", PERMITIDO, True),
            ("MIT", "PERMISSIVA", PERMITIDO, True),
            ("Standard Digital File License", "PADRAO-PLATAFORMA", PROIBIDO, True),
            ("All Rights Reserved", "RESERVADA", PROIBIDO, False),
            ("Somente uso pessoal", "PESSOAL", PROIBIDO, False),
        ]
        for texto, codigo, comercial, atribuicao in casos:
            with self.subTest(texto=texto):
                lic = classificar(texto)
                self.assertEqual(lic.codigo, codigo)
                self.assertEqual(lic.comercial, comercial)
                self.assertEqual(lic.atribuicao, atribuicao)

    def test_nc_vence_by_na_ordem_das_regras(self):
        # "Attribution-NonCommercial" tem BY e NC: precisa cair em NC.
        self.assertEqual(classificar("Attribution-NonCommercial 4.0").comercial, PROIBIDO)

    def test_licenca_vazia_ou_estranha_e_desconhecida(self):
        for texto in ("", None, "licenca da casa do Joao"):
            lic = classificar(texto)
            self.assertEqual(lic.comercial, DESCONHECIDO)
            self.assertTrue(lic.observacoes, "deve explicar o que fazer")

    def test_nd_permite_vender_mas_marca_sem_derivados(self):
        lic = classificar("CC BY-ND 4.0")
        self.assertTrue(lic.pode_vender)
        self.assertTrue(lic.sem_derivados)

    def test_acentos_e_caixa_nao_atrapalham(self):
        self.assertEqual(classificar("ATRIBUIÇÃO — NÃO COMERCIAL").comercial, PROIBIDO)


class TesteRiscoDeMarca(unittest.TestCase):
    def test_time_no_titulo_e_risco_alto(self):
        risco = avaliar_risco("Chaveiro do Corinthians", "", ["chaveiro"])
        self.assertEqual(risco.nivel, "alto")
        self.assertIn("corinthians", risco.mensagem.lower())

    def test_marca_so_na_descricao_e_risco_medio(self):
        risco = avaliar_risco("Luminaria de parede", "inspirada no Batman", [])
        self.assertEqual(risco.nivel, "medio")

    def test_modelo_generico_nao_dispara(self):
        self.assertEqual(avaliar_risco("Porta-tempero", "para churrasco", ["bbq"]).nivel, "nenhum")

    def test_cc0_com_marca_continua_bloqueado(self):
        # o caso do escudo de time: licenca livre nao libera a marca
        lic = classificar("CC0")
        risco = avaliar_risco("Escudo do Flamengo", "", [])
        self.assertTrue(lic.pode_vender)
        self.assertFalse(seguro_para_venda(lic, risco))
        self.assertIn("flamengo", motivo_bloqueio(lic, risco).lower())

    def test_termos_extras_do_usuario(self):
        cfg = config_temporaria()
        (cfg.raiz / "termos_sensiveis.txt").write_text(
            "# comentario\ncliente: Padaria do Ze\nMarca Propria\n", encoding="utf-8"
        )
        self.assertEqual(avaliar_risco("Brinde Padaria do Ze", raiz=cfg.raiz).nivel, "alto")
        self.assertEqual(avaliar_risco("Chaveiro Marca Propria", raiz=cfg.raiz).nivel, "alto")
        self.assertEqual(avaliar_risco("Brinde Padaria do Ze").nivel, "nenhum")

    def test_motivo_de_bloqueio_por_licenca(self):
        self.assertIn("nao permite venda", motivo_bloqueio(classificar("CC BY-NC"), avaliar_risco("x")))
        self.assertIn("desconhecida", motivo_bloqueio(classificar(""), avaliar_risco("x")))
        self.assertEqual(motivo_bloqueio(classificar("CC0"), avaliar_risco("x")), "")


if __name__ == "__main__":
    unittest.main()
