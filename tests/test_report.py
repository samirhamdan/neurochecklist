import csv
import unittest

from morumbi3d.db import Catalogo
from morumbi3d.mesh import RelatorioMalha
from morumbi3d.models import Candidato
from morumbi3d.pricing import orcar
from morumbi3d.report import COLUNAS_CSV, exportar_csv, gerar_html, montar_itens

from .ajuda import config_temporaria


class TesteRelatorio(unittest.TestCase):
    def setUp(self):
        self.cfg = config_temporaria()
        self.cat = Catalogo(self.cfg)
        self.addCleanup(self.cat.fechar)
        self.seguro, _ = self.cat.registrar(
            Candidato(fonte="thingiverse", fonte_id="1",
                      titulo="Porta-tempero churrasco", url="http://x/1",
                      autor="Ana", licenca_raw="CC BY 4.0", thumb_url="http://x/1.jpg")
        )
        self.bloqueado, _ = self.cat.registrar(
            Candidato(fonte="thingiverse", fonte_id="2", titulo="Escudo do Gremio",
                      url="http://x/2", autor="Bob", licenca_raw="CC0")
        )
        rel = RelatorioMalha(
            arquivo="/tmp/a.stl", triangulos=12, fechada=True, partes_soltas=1,
            dimensoes_mm=(60.0, 60.0, 60.0), volume_cm3=216.0, cabe_na_mesa=True,
            suporte="pouco", material_g=51.0, tempo_h=3.6, nota=95,
            alertas=["3% da area em balanco"],
        )
        self.cat.salvar_analise(self.seguro, rel, orcar(rel, self.cfg), "/tmp/a.stl")

    def test_montar_itens_junta_analise_e_orcamento(self):
        itens = {i["id"]: i for i in montar_itens(self.cat)}
        self.assertTrue(itens[self.seguro]["seguro"])
        self.assertFalse(itens[self.bloqueado]["seguro"])
        self.assertEqual(itens[self.seguro]["analise"]["nota"], 95)
        self.assertGreater(itens[self.seguro]["orcamento"]["preco_sugerido"], 0)
        self.assertIsNone(itens[self.bloqueado]["analise"])

    def test_html_tem_o_essencial(self):
        caminho = gerar_html(self.cfg, montar_itens(self.cat))
        html = caminho.read_text(encoding="utf-8")
        self.assertTrue(caminho.is_file())
        self.assertIn("Porta-tempero churrasco", html)
        self.assertIn("pode vender", html)
        self.assertIn("nao vender", html.replace("&#x27;", "'"))
        self.assertIn("Propriedade intelectual de terceiros", html)
        self.assertIn("imprimibilidade 95/100", html)
        self.assertIn("R$", html)
        self.assertNotIn("http://cdn", html, "relatorio deve ser offline")

    def test_html_escapa_conteudo_perigoso(self):
        self.cat.registrar(
            Candidato(fonte="x", fonte_id="9", titulo='<script>alert(1)</script>',
                      url="http://x/9", licenca_raw="CC0")
        )
        html = gerar_html(self.cfg, montar_itens(self.cat)).read_text(encoding="utf-8")
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_html_vazio_nao_quebra(self):
        html = gerar_html(self.cfg, []).read_text(encoding="utf-8")
        self.assertIn("Nenhum modelo", html)

    def test_csv_no_formato_do_projeto30(self):
        destino = exportar_csv(montar_itens(self.cat), self.cfg.raiz / "saida.csv")
        with destino.open(encoding="utf-8-sig") as fh:
            linhas = list(csv.DictReader(fh, delimiter=";"))
        self.assertEqual(list(linhas[0]), COLUNAS_CSV)
        por_titulo = {l["titulo"]: l for l in linhas}
        seguro = por_titulo["Porta-tempero churrasco"]
        self.assertEqual(seguro["uso_comercial"], "permitido")
        self.assertEqual(seguro["risco_marca"], "nenhum")
        self.assertEqual(seguro["dimensoes_mm"], "60.0x60.0x60.0")
        self.assertEqual(seguro["nota_imprimibilidade"], "95")
        bloqueado = por_titulo["Escudo do Gremio"]
        self.assertEqual(bloqueado["risco_marca"], "alto")
        self.assertIn("gremio", bloqueado["risco_termos"].lower())
        self.assertEqual(bloqueado["nota_imprimibilidade"], "")


if __name__ == "__main__":
    unittest.main()
