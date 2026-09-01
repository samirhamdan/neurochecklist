import unittest
import urllib.robotparser
from unittest import mock

from morumbi3d.net import AcessoNegado, Resposta, SessaoEducada

from .ajuda import config_temporaria


def robots(texto: str):
    parser = urllib.robotparser.RobotFileParser()
    parser.parse(texto.splitlines())
    return parser


class TesteSessao(unittest.TestCase):
    def setUp(self):
        self.cfg = config_temporaria()
        self.cfg.rede.intervalo_min_s = 0.0
        self.sessao = SessaoEducada(self.cfg)

    def test_cache_ida_e_volta(self):
        caminho = self.sessao._caminho_cache("http://x/1", None)
        self.sessao._gravar_cache(
            caminho, Resposta(url="http://x/1", status=200, corpo=b'{"a": 1}')
        )
        lido = self.sessao._ler_cache(caminho)
        self.assertEqual(lido.json(), {"a": 1})
        self.assertTrue(lido.do_cache)

    def test_cache_expira(self):
        import os
        import time

        caminho = self.sessao._caminho_cache("http://x/2", None)
        self.sessao._gravar_cache(caminho, Resposta(url="http://x/2", status=200, corpo=b"1"))
        self.cfg.rede.cache_ttl_s = 1
        antigo = time.time() - 10
        os.utime(caminho, (antigo, antigo))
        self.assertIsNone(self.sessao._ler_cache(caminho))

    def test_urls_diferentes_nao_colidem_no_cache(self):
        self.assertNotEqual(
            self.sessao._caminho_cache("http://x/1", None),
            self.sessao._caminho_cache("http://x/2", None),
        )
        self.assertNotEqual(
            self.sessao._caminho_cache("http://x/1", b"corpo-a"),
            self.sessao._caminho_cache("http://x/1", b"corpo-b"),
        )

    def test_robots_bloqueia(self):
        with mock.patch.object(
            SessaoEducada, "_carregar_robots",
            return_value=robots("User-agent: *\nDisallow: /privado"),
        ):
            self.assertTrue(self.sessao.permitido("http://x/publico")[0])
            ok, motivo = self.sessao.permitido("http://x/privado/coisa")
            self.assertFalse(ok)
            self.assertIn("robots.txt", motivo)

    def test_requisicao_bloqueada_levanta_acesso_negado(self):
        with mock.patch.object(
            SessaoEducada, "_carregar_robots",
            return_value=robots("User-agent: *\nDisallow: /"),
        ):
            with self.assertRaises(AcessoNegado):
                self.sessao.obter("http://x/qualquer")

    def test_robots_ausente_nao_bloqueia(self):
        with mock.patch.object(SessaoEducada, "_carregar_robots", return_value=None):
            ok, motivo = self.sessao.permitido("http://x/qualquer")
            self.assertTrue(ok)
            self.assertIn("indisponivel", motivo)

    def test_desligar_robots_na_configuracao(self):
        self.cfg.rede.respeitar_robots = False
        with mock.patch.object(SessaoEducada, "_carregar_robots") as carregar:
            self.assertTrue(self.sessao.permitido("http://x/privado")[0])
            carregar.assert_not_called()

    def test_intervalo_entre_requisicoes_ao_mesmo_host(self):
        self.cfg.rede.intervalo_min_s = 0.05
        dormidas = []
        with mock.patch("morumbi3d.net.time.sleep", side_effect=dormidas.append):
            self.sessao._esperar_vez("http://a/1")
            self.sessao._esperar_vez("http://a/2")  # mesmo host: espera
            self.sessao._esperar_vez("http://b/1")  # host novo: nao espera
        self.assertEqual(len(dormidas), 1)
        self.assertGreater(dormidas[0], 0)

    def test_baixar_nao_repete_arquivo_ja_no_cache(self):
        destino = self.cfg.cache_arquivos / "ja-existe.stl"
        destino.write_bytes(b"conteudo")
        with mock.patch.object(SessaoEducada, "obter") as obter:
            resultado = self.sessao.baixar("http://x/arquivo.stl", destino)
            obter.assert_not_called()
        self.assertEqual(resultado.read_bytes(), b"conteudo")

    def test_baixar_imagem_engole_falha(self):
        with mock.patch.object(
            SessaoEducada, "baixar", side_effect=AcessoNegado("bloqueado")
        ):
            self.assertIsNone(self.sessao.baixar_imagem("http://x/i.jpg", "n"))
        self.assertIsNone(self.sessao.baixar_imagem("", "n"))


if __name__ == "__main__":
    unittest.main()
