import unittest

from morumbi3d.db import Catalogo, chave_dedupe
from morumbi3d.models import Candidato

from .ajuda import config_temporaria


def candidato(**kwargs) -> Candidato:
    padrao = dict(
        fonte="thingiverse", fonte_id="1", titulo="Porta-tempero churrasco",
        url="http://x/1", autor="Ana", licenca_raw="CC BY 4.0", tags=["bbq"],
    )
    padrao.update(kwargs)
    return Candidato(**padrao)


class TesteCatalogo(unittest.TestCase):
    def setUp(self):
        self.cfg = config_temporaria()
        self.cat = Catalogo(self.cfg)
        self.addCleanup(self.cat.fechar)

    def test_registrar_e_idempotente(self):
        primeiro = self.cat.registrar(candidato())
        segundo = self.cat.registrar(candidato())
        self.assertEqual(primeiro, (1, True))
        self.assertEqual(segundo, (1, False))
        self.assertEqual(len(self.cat.listar()), 1)

    def test_classifica_licenca_linha_e_risco_ao_registrar(self):
        modelo_id, _ = self.cat.registrar(candidato())
        r = self.cat.obter(modelo_id)
        self.assertEqual(r["licenca_comercial"], "permitido")
        self.assertEqual(r["linha"], "Adultos")
        self.assertEqual(r["colecao"], "Churrasco")
        self.assertEqual(r["risco_nivel"], "nenhum")

    def test_marca_registrada_fica_sinalizada(self):
        modelo_id, _ = self.cat.registrar(
            candidato(fonte_id="9", titulo="Chaveiro do Palmeiras", licenca_raw="CC0")
        )
        r = self.cat.obter(modelo_id)
        self.assertEqual(r["risco_nivel"], "alto")
        self.assertNotIn(r["id"], [x["id"] for x in self.cat.listar(so_seguros=True)])

    def test_duplicata_entre_fontes(self):
        a, _ = self.cat.registrar(candidato())
        b, _ = self.cat.registrar(
            candidato(fonte="printables", fonte_id="77", titulo="Porta tempero  churrasco!")
        )
        self.assertEqual(self.cat.obter(b)["duplicado_de"], a)
        self.assertEqual(len(self.cat.listar()), 1, "duplicata some da lista")
        self.assertEqual(len(self.cat.listar(incluir_duplicados=True)), 2)

    def test_chave_dedupe_ignora_ruido(self):
        self.assertEqual(
            chave_dedupe("Porta-Tempero para Churrasco (STL)", "Ana"),
            chave_dedupe("churrasco porta tempero", "ANA"),
        )
        self.assertNotEqual(chave_dedupe("Vaso", "Ana"), chave_dedupe("Vaso", "Bob"))

    def test_mudar_status(self):
        modelo_id, _ = self.cat.registrar(candidato())
        self.assertTrue(self.cat.mudar_status(modelo_id, "aprovado", "testar em preto"))
        r = self.cat.obter(modelo_id)
        self.assertEqual(r["status"], "aprovado")
        self.assertEqual(r["motivo"], "testar em preto")
        with self.assertRaises(ValueError):
            self.cat.mudar_status(modelo_id, "quase", "")
        self.assertFalse(self.cat.mudar_status(9999, "aprovado"))

    def test_filtros_da_listagem(self):
        self.cat.registrar(candidato())
        self.cat.registrar(candidato(fonte_id="2", titulo="Vaso para suculenta", autor="Bob"))
        self.cat.registrar(
            candidato(fonte_id="3", titulo="Espeto bbq", autor="Cid", licenca_raw="CC BY-NC")
        )
        self.assertEqual(len(self.cat.listar(linha="Adultos")), 2)
        self.assertEqual(len(self.cat.listar(texto="suculenta")), 1)
        self.assertEqual(len(self.cat.listar(so_seguros=True)), 2)
        self.assertEqual(len(self.cat.listar(limite=1)), 1)
        self.assertEqual(len(self.cat.listar(fonte="printables")), 0)

    def test_estatisticas(self):
        a, _ = self.cat.registrar(candidato())
        self.cat.registrar(candidato(fonte_id="2", titulo="Escudo do Vasco", autor="Bob"))
        self.cat.mudar_status(a, "aprovado")
        e = self.cat.estatisticas()
        self.assertEqual(e["total"], 2)
        self.assertEqual(e["por_status"]["aprovado"], 1)
        self.assertEqual(e["seguros_para_venda"], 1)
        self.assertEqual(e["bloqueados"], 1)

    def test_salvar_analise(self):
        from morumbi3d.mesh import RelatorioMalha
        from morumbi3d.pricing import orcar

        modelo_id, _ = self.cat.registrar(candidato())
        rel = RelatorioMalha(material_g=30.0, tempo_h=2.0, nota=88, fechada=True)
        self.cat.salvar_analise(modelo_id, rel, orcar(rel, self.cfg), "/tmp/x.stl")
        analise = self.cat.ultima_analise(modelo_id)
        self.assertEqual(analise["nota"], 88)
        self.assertEqual(self.cat.obter(modelo_id)["arquivo_local"], "/tmp/x.stl")

    def test_registrar_busca(self):
        self.cat.registrar_busca("churrasco", ["bbq"], ["thingiverse"], 10, 3, [])
        linha = self.cat.conn.execute("SELECT * FROM buscas").fetchone()
        self.assertEqual(linha["termo"], "churrasco")
        self.assertEqual(linha["novos"], 3)

    def test_reabrir_banco_mantem_dados(self):
        self.cat.registrar(candidato())
        self.cat.fechar()
        with Catalogo(self.cfg) as outro:
            self.assertEqual(len(outro.listar()), 1)


if __name__ == "__main__":
    unittest.main()
