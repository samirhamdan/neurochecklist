import io
import unittest
from contextlib import redirect_stdout
from unittest import mock

from morumbi3d import cli
from morumbi3d.db import Catalogo
from morumbi3d.models import Candidato

from .ajuda import config_temporaria, cubo, escrever_stl_binario


class TesteCLI(unittest.TestCase):
    def setUp(self):
        self.cfg = config_temporaria()
        patch = mock.patch.object(cli, "carregar_config", lambda caminho=None: self.cfg)
        patch.start()
        self.addCleanup(patch.stop)

    def rodar(self, *argv) -> tuple[int, str]:
        saida = io.StringIO()
        with redirect_stdout(saida):
            codigo = cli.main(list(argv))
        return codigo, saida.getvalue()

    def semear(self, **kwargs) -> int:
        padrao = dict(
            fonte="thingiverse", fonte_id="1", titulo="Porta-tempero churrasco",
            url="http://x/1", autor="Ana", licenca_raw="CC BY 4.0",
        )
        padrao.update(kwargs)
        with Catalogo(self.cfg) as cat:
            modelo_id, _ = cat.registrar(Candidato(**padrao))
        return modelo_id

    # ------------------------------------------------------------------
    def test_fontes(self):
        codigo, saida = self.rodar("fontes")
        self.assertEqual(codigo, 0)
        self.assertIn("thingiverse", saida)
        self.assertIn("termos de uso", saida)

    def test_init_cria_configuracao(self):
        destino = self.cfg.raiz / "morumbi3d.toml"
        codigo, saida = self.rodar("init", "--saida", str(destino))
        self.assertEqual(codigo, 0)
        self.assertTrue(destino.is_file())
        self.assertIn("[fontes]", destino.read_text())
        self.assertEqual(self.rodar("init", "--saida", str(destino))[0], 1)
        self.assertEqual(self.rodar("init", "--saida", str(destino), "--forcar")[0], 0)

    def test_init_gera_toml_valido(self):
        import tomllib

        destino = self.cfg.raiz / "c.toml"
        self.rodar("init", "--saida", str(destino))
        with destino.open("rb") as fh:
            dados = tomllib.load(fh)
        self.assertIn("impressora", dados)
        self.assertFalse(dados["fontes"]["makerworld"])

    def test_catalogo_vazio_e_com_itens(self):
        self.assertIn("Nada no catalogo", self.rodar("catalogo")[1])
        self.semear()
        codigo, saida = self.rodar("catalogo")
        self.assertEqual(codigo, 0)
        self.assertIn("Porta-tempero churrasco", saida)
        self.assertIn("[vende]", saida)

    def test_ver_detalha_e_avisa_inexistente(self):
        modelo_id = self.semear()
        codigo, saida = self.rodar("ver", str(modelo_id))
        self.assertEqual(codigo, 0)
        self.assertIn("Adultos/Churrasco", saida)
        self.assertIn("sem analise", saida)
        self.assertEqual(self.rodar("ver", "999")[0], 1)

    def test_analisar_arquivo_solto(self):
        arquivo = escrever_stl_binario(self.cfg.raiz / "cubo.stl", cubo(50.0))
        codigo, saida = self.rodar("analisar", str(arquivo))
        self.assertEqual(codigo, 0)
        self.assertIn("fechada", saida)
        self.assertIn("preco sugerido", saida)
        self.assertIn("nota", saida)

    def test_analisar_salva_no_modelo(self):
        modelo_id = self.semear()
        arquivo = escrever_stl_binario(self.cfg.raiz / "cubo.stl", cubo(50.0))
        codigo, _ = self.rodar(
            "analisar", "--modelo", str(modelo_id), "--arquivo", str(arquivo)
        )
        self.assertEqual(codigo, 0)
        with Catalogo(self.cfg) as cat:
            self.assertIsNotNone(cat.ultima_analise(modelo_id))
        self.assertIn("nota", self.rodar("ver", str(modelo_id))[1])

    def test_analisar_arquivo_invalido(self):
        ruim = self.cfg.raiz / "ruim.stl"
        ruim.write_bytes(b"")
        codigo, saida = self.rodar("analisar", str(ruim))
        self.assertEqual(codigo, 1)
        self.assertIn("nao foi possivel analisar", saida)

    def test_analisar_sem_arquivo_orienta_o_download_manual(self):
        modelo_id = self.semear()
        codigo, saida = self.rodar("analisar", "--modelo", str(modelo_id))
        self.assertEqual(codigo, 1)
        self.assertIn("Baixe o arquivo", saida)

    def test_aprovar_modelo_seguro(self):
        modelo_id = self.semear()
        codigo, saida = self.rodar("aprovar", str(modelo_id), "--motivo", "testar")
        self.assertEqual(codigo, 0)
        self.assertIn("aprovado", saida)
        with Catalogo(self.cfg) as cat:
            self.assertEqual(cat.obter(modelo_id)["status"], "aprovado")

    def test_aprovar_bloqueia_modelo_com_marca(self):
        modelo_id = self.semear(fonte_id="2", titulo="Escudo do Flamengo", licenca_raw="CC0")
        codigo, saida = self.rodar("aprovar", str(modelo_id))
        self.assertEqual(codigo, 2, "aprovacao com risco de marca deve falhar")
        self.assertIn("BLOQUEADO", saida)
        with Catalogo(self.cfg) as cat:
            self.assertEqual(cat.obter(modelo_id)["status"], "novo")

    def test_aprovar_bloqueia_licenca_nao_comercial(self):
        modelo_id = self.semear(fonte_id="3", titulo="Espeto", licenca_raw="CC BY-NC")
        self.assertEqual(self.rodar("aprovar", str(modelo_id))[0], 2)

    def test_mesmo_assim_libera_com_registro(self):
        modelo_id = self.semear(fonte_id="2", titulo="Escudo do Flamengo", licenca_raw="CC0")
        codigo, saida = self.rodar(
            "aprovar", str(modelo_id), "--mesmo-assim", "--motivo", "autorizacao por escrito"
        )
        self.assertEqual(codigo, 0)
        self.assertIn("aviso ignorado", saida)
        with Catalogo(self.cfg) as cat:
            r = cat.obter(modelo_id)
        self.assertEqual(r["status"], "aprovado")
        self.assertEqual(r["motivo"], "autorizacao por escrito")

    def test_reprovar_nao_exige_licenca_livre(self):
        modelo_id = self.semear(fonte_id="3", titulo="Espeto", licenca_raw="CC BY-NC")
        self.assertEqual(self.rodar("reprovar", str(modelo_id), "--motivo", "nc")[0], 0)

    def test_relatorio_e_exportacao(self):
        self.semear()
        destino_html = self.cfg.raiz / "r.html"
        codigo, saida = self.rodar("relatorio", "--saida", str(destino_html))
        self.assertEqual(codigo, 0)
        self.assertTrue(destino_html.is_file())
        self.assertIn("1 modelo", saida)

        destino_csv = self.cfg.raiz / "r.csv"
        codigo, saida = self.rodar("exportar", "--saida", str(destino_csv))
        self.assertEqual(codigo, 0)
        self.assertIn("Porta-tempero churrasco", destino_csv.read_text(encoding="utf-8-sig"))

    def test_stats(self):
        self.semear()
        self.semear(fonte_id="2", titulo="Escudo do Vasco")
        codigo, saida = self.rodar("stats")
        self.assertEqual(codigo, 0)
        self.assertIn("total", saida)
        self.assertIn("bloqueados", saida)

    def test_buscar_sem_fonte_disponivel(self):
        self.cfg.fontes.github = False
        codigo, saida = self.rodar("buscar", "churrasco")
        self.assertEqual(codigo, 0)
        self.assertIn("nenhuma fonte disponivel", saida)

    def test_comando_desconhecido(self):
        with self.assertRaises(SystemExit):
            self.rodar("inventado")


if __name__ == "__main__":
    unittest.main()
