import unittest
from unittest import mock

from morumbi3d import search
from morumbi3d.db import Catalogo
from morumbi3d.models import Candidato
from morumbi3d.net import SessaoEducada
from morumbi3d.sources.base import Conector

from .ajuda import config_temporaria


class FonteBoa(Conector):
    id = "github"
    nome = "Boa"
    site = "http://boa"
    exige_optin = False

    def buscar(self, termo, limite=20):
        return [
            Candidato(fonte="boa", fonte_id="1", titulo="Porta-tempero churrasco",
                      url="http://boa/1", autor="Ana", licenca_raw="CC BY 4.0",
                      thumb_url="http://boa/1.jpg", gratuito=True, formatos=["stl"]),
            Candidato(fonte="boa", fonte_id="2", titulo="Escudo do Santos FC",
                      url="http://boa/2", autor="Bob", licenca_raw="CC0",
                      gratuito=True, formatos=["stl"]),
            Candidato(fonte="boa", fonte_id="3", titulo="Espeto premium",
                      url="http://boa/3", autor="Cid", licenca_raw="CC BY-NC",
                      gratuito=False, preco=5.0, formatos=["3mf"]),
        ]


class FonteQuebrada(Conector):
    id = "thingiverse"
    nome = "Quebrada"
    site = "http://quebrada"
    exige_optin = False

    def _pronta(self):
        return True, "pronta"

    def buscar(self, termo, limite=20):
        raise RuntimeError("API fora do ar (503)")


class FonteDesligada(Conector):
    id = "makerworld"
    nome = "Desligada"
    site = "http://desligada"
    exige_optin = True

    def buscar(self, termo, limite=20):  # pragma: no cover - nunca chamada
        raise AssertionError("fonte desligada nao deveria ser consultada")


class TesteBusca(unittest.TestCase):
    def setUp(self):
        self.cfg = config_temporaria()
        self.cfg.fontes.thingiverse = True
        self.cfg.fontes.github = True
        self.sessao = SessaoEducada(self.cfg)
        patch = mock.patch.object(
            search,
            "instanciar",
            lambda cfg, sessao=None: [
                FonteBoa(cfg, sessao), FonteQuebrada(cfg, sessao), FonteDesligada(cfg, sessao)
            ],
        )
        patch.start()
        self.addCleanup(patch.stop)

    def buscar(self, **kwargs):
        kwargs.setdefault("sessao", self.sessao)
        return search.buscar(self.cfg, kwargs.pop("termo", "churrasco"), **kwargs)

    def test_fonte_quebrada_nao_derruba_a_busca(self):
        r = self.buscar()
        self.assertEqual(len(r.achados), 3)
        self.assertEqual(len(r.erros), 1)
        self.assertIn("503", r.erros[0])
        self.assertIn("thingiverse", r.erros[0])

    def test_fonte_desligada_e_reportada_e_nao_consultada(self):
        r = self.buscar()
        self.assertIn("makerworld", [f for f, _ in r.fontes_ignoradas])
        self.assertNotIn("makerworld", r.fontes_consultadas)

    def test_expande_o_termo_para_ingles(self):
        self.assertIn("bbq", self.buscar().variantes)
        self.assertEqual(self.buscar(traduzir=False).variantes, ["churrasco"])

    def test_filtro_so_comercial(self):
        r = self.buscar(so_comercial=True)
        titulos = [a.candidato.titulo for a in r.achados]
        self.assertEqual(titulos, ["Porta-tempero churrasco"])
        self.assertEqual(r.descartados_filtro, 2)

    def test_filtro_gratuitos_imagem_e_formato(self):
        self.assertEqual(len(self.buscar(so_gratuitos=True).achados), 2)
        self.assertEqual(len(self.buscar(com_imagem=True).achados), 1)
        self.assertEqual(len(self.buscar(formato="3mf").achados), 1)

    def test_grava_no_catalogo_e_marca_novos(self):
        with Catalogo(self.cfg) as cat:
            primeira = self.buscar(catalogo=cat)
            self.assertEqual(primeira.novos, 3)
            segunda = self.buscar(catalogo=cat)
            self.assertEqual(segunda.novos, 0, "segunda busca nao duplica")
            self.assertEqual(len(cat.listar()), 3)
            self.assertEqual(
                cat.conn.execute("SELECT COUNT(*) c FROM buscas").fetchone()["c"], 2
            )

    def test_risco_de_marca_sobrevive_a_licenca_livre(self):
        achado = next(a for a in self.buscar().achados if "Santos" in a.candidato.titulo)
        self.assertTrue(achado.licenca.pode_vender)
        self.assertEqual(achado.risco.nivel, "alto")
        self.assertFalse(achado.seguro)

    def test_sem_fonte_disponivel(self):
        self.cfg.fontes.github = False
        self.cfg.fontes.thingiverse = False
        r = self.buscar()
        self.assertEqual(r.achados, [])
        self.assertTrue(r.erros)

    def test_restringir_fontes(self):
        r = self.buscar(fontes=["github"])
        self.assertEqual(r.fontes_consultadas, ["github"])
        self.assertEqual(r.erros, [])


if __name__ == "__main__":
    unittest.main()
