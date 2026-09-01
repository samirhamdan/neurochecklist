import json
import unittest
from unittest import mock

from morumbi3d.net import FalhaRede, Resposta, SessaoEducada
from morumbi3d.sources import instanciar, por_id
from morumbi3d.sources.base import achar_lista, primeiro

from .ajuda import config_temporaria


def resposta(dado) -> Resposta:
    return Resposta(url="http://x", status=200,
                    corpo=json.dumps(dado).encode("utf-8"), tipo="application/json")


class TesteRegistro(unittest.TestCase):
    def setUp(self):
        self.cfg = config_temporaria()

    def test_todas_as_fontes_da_especificacao_existem(self):
        ids = {c.id for c in instanciar(self.cfg)}
        self.assertEqual(
            ids, {"thingiverse", "printables", "makerworld", "thangs", "cults3d", "github"}
        )

    def test_fontes_sem_api_ficam_desligadas_por_padrao(self):
        for ident in ("printables", "makerworld", "thangs", "cults3d"):
            with self.subTest(fonte=ident):
                conector = por_id(self.cfg, ident)
                self.assertTrue(conector.exige_optin)
                ok, motivo = conector.disponivel()
                self.assertFalse(ok)
                self.assertIn("termos de uso", motivo)

    def test_ligar_a_fonte_exige_decisao_explicita(self):
        self.cfg.fontes.printables = True
        ok, motivo = por_id(self.cfg, "printables").disponivel()
        self.assertTrue(ok)
        self.assertIn("conta e risco", motivo)

    def test_thingiverse_sem_chave_fica_indisponivel(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            ok, motivo = por_id(self.cfg, "thingiverse").disponivel()
        self.assertFalse(ok)
        self.assertIn("THINGIVERSE_TOKEN", motivo)


class TesteAjudantes(unittest.TestCase):
    def test_primeiro_valor_util(self):
        dado = {"a": "", "b": None, "c": "valor", "d": {"e": "aninhado"}}
        self.assertEqual(primeiro(dado, "a", "b", "c"), "valor")
        self.assertEqual(primeiro(dado, "d.e"), "aninhado")
        self.assertEqual(primeiro(dado, "x", padrao="fallback"), "fallback")

    def test_achar_lista_em_json_de_formato_incerto(self):
        self.assertEqual(achar_lista({"hits": [{"id": 1}]}, "hits"), [{"id": 1}])
        self.assertEqual(achar_lista({"data": {"list": [{"id": 2}]}}, "data.list"), [{"id": 2}])
        # caminho desconhecido: acha a maior lista de dicionarios
        self.assertEqual(
            achar_lista({"qualquer": {"coisa": [{"id": 3}, {"id": 4}]}}, "nao.existe"),
            [{"id": 3}, {"id": 4}],
        )
        self.assertEqual(achar_lista({"vazio": {}}, "x"), [])


class TesteThingiverse(unittest.TestCase):
    def setUp(self):
        self.cfg = config_temporaria()
        self.cfg.fontes.thingiverse = True
        self.conector = por_id(self.cfg, "thingiverse", SessaoEducada(self.cfg))

    def test_mapeia_os_campos(self):
        dado = {"hits": [{
            "id": 4321, "name": "BBQ Spice Rack",
            "public_url": "https://www.thingiverse.com/thing:4321",
            "creator": {"name": "maker"}, "description": "porta tempero",
            "tags": ["bbq", "kitchen"], "license": "Creative Commons - Attribution",
            "preview_image": "https://img/x.jpg", "download_count": 120, "like_count": 9,
        }]}
        with mock.patch.dict("os.environ", {"THINGIVERSE_TOKEN": "chave"}), \
             mock.patch.object(SessaoEducada, "obter", return_value=resposta(dado)):
            achados = self.conector.buscar("bbq")
        self.assertEqual(len(achados), 1)
        c = achados[0]
        self.assertEqual((c.fonte, c.fonte_id, c.titulo), ("thingiverse", "4321", "BBQ Spice Rack"))
        self.assertEqual(c.autor, "maker")
        self.assertEqual(c.licenca_raw, "Creative Commons - Attribution")
        self.assertEqual(c.downloads, 120)

    def test_ignora_conteudo_adulto_e_itens_quebrados(self):
        dado = {"hits": [
            {"id": 1, "name": "ok", "license": "CC0"},
            {"id": 2, "name": "nsfw", "is_nsfw": True},
            {"id": 3},  # sem titulo
            "lixo",
        ]}
        with mock.patch.dict("os.environ", {"THINGIVERSE_TOKEN": "chave"}), \
             mock.patch.object(SessaoEducada, "obter", return_value=resposta(dado)):
            achados = self.conector.buscar("x")
        self.assertEqual([c.titulo for c in achados], ["ok"])

    def test_sem_chave_devolve_lista_vazia(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(self.conector.buscar("x"), [])

    def test_erro_de_rede_vira_falha_identificada(self):
        with mock.patch.dict("os.environ", {"THINGIVERSE_TOKEN": "chave"}), \
             mock.patch.object(SessaoEducada, "obter", side_effect=FalhaRede("timeout")):
            with self.assertRaises(FalhaRede) as ctx:
                self.conector.buscar("x")
        self.assertIn("Thingiverse", str(ctx.exception))


class TesteOutrasFontes(unittest.TestCase):
    def setUp(self):
        self.cfg = config_temporaria()
        for nome in ("printables", "makerworld", "thangs", "github"):
            setattr(self.cfg.fontes, nome, True)

    def conector(self, ident):
        return por_id(self.cfg, ident, SessaoEducada(self.cfg))

    def test_printables(self):
        dado = {"data": {"result": {"items": [{
            "id": "77", "name": "Grill tool", "slug": "77-grill-tool",
            "summary": "resumo", "license": {"name": "CC BY-NC"},
            "user": {"publicUsername": "prusa"}, "image": {"filePath": "media/x.jpg"},
            "downloadCount": 5, "likesCount": 2,
        }]}}}
        with mock.patch.object(SessaoEducada, "obter", return_value=resposta(dado)):
            c = self.conector("printables").buscar("grill")[0]
        self.assertEqual(c.fonte_id, "77")
        self.assertEqual(c.autor, "prusa")
        self.assertEqual(c.licenca_raw, "CC BY-NC")
        self.assertTrue(c.url.endswith("/model/77-grill-tool"))
        self.assertTrue(c.thumb_url.startswith("https://media.printables.com/"))

    def test_printables_avisa_quando_o_endpoint_muda(self):
        dado = {"errors": [{"message": "Cannot query field searchPrints"}]}
        with mock.patch.object(SessaoEducada, "obter", return_value=resposta(dado)):
            with self.assertRaises(FalhaRede) as ctx:
                self.conector("printables").buscar("x")
        self.assertIn("endpoint", str(ctx.exception))

    def test_makerworld(self):
        dado = {"hits": [{
            "id": 900, "title": "Churrasco holder", "cover": "https://img/c.jpg",
            "designCreator": {"name": "bambu"}, "license": "CC BY", "isPaid": False,
            "downloadCount": 33,
        }]}
        with mock.patch.object(SessaoEducada, "obter", return_value=resposta(dado)):
            c = self.conector("makerworld").buscar("churrasco")[0]
        self.assertEqual((c.fonte_id, c.autor, c.gratuito), ("900", "bambu", True))
        self.assertIn("3mf", c.formatos)

    def test_makerworld_marca_modelo_pago(self):
        dado = {"hits": [{"id": 1, "title": "Pago", "isPaid": True}]}
        with mock.patch.object(SessaoEducada, "obter", return_value=resposta(dado)):
            self.assertFalse(self.conector("makerworld").buscar("x")[0].gratuito)

    def test_thangs(self):
        dado = {"results": [{
            "modelId": "abc", "name": "Trophy", "ownerUsername": "user",
            "license": "CC0", "thumbnailUrl": "https://img/t.jpg",
        }]}
        with mock.patch.object(SessaoEducada, "obter", return_value=resposta(dado)):
            c = self.conector("thangs").buscar("trophy")[0]
        self.assertEqual((c.fonte_id, c.titulo, c.licenca_raw), ("abc", "Trophy", "CC0"))

    def test_thangs_busca_por_geometria_e_segunda_fase(self):
        with self.assertRaises(NotImplementedError):
            self.conector("thangs").buscar_por_geometria("x.stl")

    def test_github(self):
        dado = {"items": [{
            "id": 5, "full_name": "user/stl-models", "html_url": "https://github.com/user/stl-models",
            "owner": {"login": "user"}, "description": "colecao", "topics": ["stl"],
            "license": {"spdx_id": "MIT"}, "stargazers_count": 42, "default_branch": "main",
        }]}
        with mock.patch.object(SessaoEducada, "obter", return_value=resposta(dado)):
            c = self.conector("github").buscar("stl")[0]
        self.assertEqual(c.licenca_raw, "MIT")
        self.assertEqual(c.curtidas, 42)
        self.assertTrue(c.arquivo_url.endswith("/archive/refs/heads/main.zip"))

    def test_cults3d_explica_quando_vem_html(self):
        self.cfg.fontes.cults3d = True
        html = Resposta(url="http://x", status=200, corpo=b"<html>pagina</html>", tipo="text/html")
        with mock.patch.object(SessaoEducada, "obter", return_value=html):
            with self.assertRaises(FalhaRede) as ctx:
                self.conector("cults3d").buscar("x")
        self.assertIn("HTML", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
