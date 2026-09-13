# -*- coding: utf-8 -*-
"""Melhoria 2 -- catálogo de produtos com fotos.

Produto marcado como "catalogo" aparece na página /catalogo.
Até 3 fotos por produto, guardadas em MORUMBI_DADOS/fotos/<id>/.
"""
from __future__ import annotations

import importlib
import io
import os
import tempfile
import unittest


class Base(unittest.TestCase):
    def setUp(self):
        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-cat-")
        os.environ["MORUMBI_USUARIO"] = "samir"
        os.environ["MORUMBI_SENHA"] = "segredo"
        os.environ["MORUMBI_BIND"] = "127.0.0.1:5000"
        os.environ["MORUMBI_HTTPS"] = "0"
        from sistema import auth, dados
        importlib.reload(dados)
        importlib.reload(auth)
        from sistema import app as modulo
        importlib.reload(modulo)
        self.dados = dados
        self.app = modulo.criar_app()
        self.app.config["TESTING"] = True
        self.cliente = self.app.test_client()
        self.cliente.post("/entrar", data={"usuario": "samir", "senha": "segredo"})


class TesteMigracao(Base):
    def test_campo_catalogo_existe_no_produto(self):
        with self.dados.conectar() as conn:
            colunas = {r[1] for r in conn.execute("PRAGMA table_info(produtos)")}
        self.assertIn("catalogo", colunas)

    def test_tabela_produto_fotos_existe(self):
        with self.dados.conectar() as conn:
            tabelas = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'")}
        self.assertIn("produto_fotos", tabelas)


class TesteCatalogo(Base):
    def _produto(self, nome="Topo ANA", catalogo=False):
        dados_p = {"nome": nome}
        if catalogo:
            dados_p["catalogo"] = "1"
        return self.dados.salvar_produto(dados_p, "samir")

    def test_produto_fora_do_catalogo_nao_aparece(self):
        self._produto("Topo fora")
        self.assertEqual(len(self.dados.produtos_catalogo()), 0)

    def test_produto_no_catalogo_aparece(self):
        self._produto("Topo dentro", catalogo=True)
        cats = self.dados.produtos_catalogo()
        self.assertEqual(len(cats), 1)
        self.assertEqual(cats[0]["nome"], "Topo dentro")

    def test_produto_inativo_nao_aparece_no_catalogo(self):
        pid = self._produto("Inativo", catalogo=True)
        self.dados.salvar_produto({"nome": "Inativo", "catalogo": "1", "ativo": "0"},
                                  "samir", pid)
        self.assertEqual(len(self.dados.produtos_catalogo()), 0)

    def test_tela_catalogo_vazia(self):
        r = self.cliente.get("/catalogo")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Nenhum produto no catálogo", r.get_data(as_text=True))

    def test_tela_catalogo_com_produto(self):
        self._produto("Topo Rosa", catalogo=True)
        corpo = self.cliente.get("/catalogo").get_data(as_text=True)
        self.assertIn("Topo Rosa", corpo)


class TesteFotos(Base):
    def setUp(self):
        super().setUp()
        self.pid = self.dados.salvar_produto(
            {"nome": "Peça foto", "catalogo": "1"}, "samir")

    def _foto_fake(self, nome="foto.jpg"):
        """1x1 JPEG mínimo."""
        conteudo = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01'
            b'\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07'
            b'\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14'
            b'\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f'
            b"'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
            b'\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08'
            b'\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03'
            b'\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12'
            b'!1A\x06\x13Qa\x07"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1'
            b'\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&\'()*456789:CDEFGHIJST'
            b'UVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93'
            b'\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9'
            b'\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6'
            b'\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2'
            b'\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7'
            b'\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd2\x8a'
            b'+\xff\xd9'
        )
        return io.BytesIO(conteudo), nome

    def test_upload_foto(self):
        dados_f, nome = self._foto_fake()
        r = self.cliente.post(f"/produtos/{self.pid}/fotos",
                              data={"foto": (dados_f, nome)},
                              content_type="multipart/form-data")
        self.assertEqual(r.status_code, 201)
        fotos = self.dados.fotos_produto(self.pid)
        self.assertEqual(len(fotos), 1)

    def test_maximo_3_fotos(self):
        for i in range(3):
            dados_f, _ = self._foto_fake()
            self.cliente.post(f"/produtos/{self.pid}/fotos",
                              data={"foto": (dados_f, f"foto{i}.jpg")},
                              content_type="multipart/form-data")
        dados_f, _ = self._foto_fake()
        r = self.cliente.post(f"/produtos/{self.pid}/fotos",
                              data={"foto": (dados_f, "foto4.jpg")},
                              content_type="multipart/form-data")
        self.assertEqual(r.status_code, 400)
        self.assertIn("3", r.get_data(as_text=True))

    def test_apagar_foto(self):
        dados_f, nome = self._foto_fake()
        r = self.cliente.post(f"/produtos/{self.pid}/fotos",
                              data={"foto": (dados_f, nome)},
                              content_type="multipart/form-data")
        foto_id = r.get_json()["id"]
        r = self.cliente.delete(f"/produtos/{self.pid}/fotos/{foto_id}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(self.dados.fotos_produto(self.pid)), 0)

    def test_extensao_invalida_recusada(self):
        r = self.cliente.post(f"/produtos/{self.pid}/fotos",
                              data={"foto": (io.BytesIO(b"fake"), "virus.exe")},
                              content_type="multipart/form-data")
        self.assertEqual(r.status_code, 400)

    def test_foto_guardada_no_disco(self):
        dados_f, nome = self._foto_fake()
        self.cliente.post(f"/produtos/{self.pid}/fotos",
                          data={"foto": (dados_f, nome)},
                          content_type="multipart/form-data")
        pasta = self.dados.pasta_fotos(self.pid)
        arquivos = list(pasta.iterdir())
        self.assertEqual(len(arquivos), 1)

    def test_foto_servida_pela_rota(self):
        dados_f, nome = self._foto_fake()
        self.cliente.post(f"/produtos/{self.pid}/fotos",
                          data={"foto": (dados_f, nome)},
                          content_type="multipart/form-data")
        fotos = self.dados.fotos_produto(self.pid)
        r = self.cliente.get(f"/fotos/{self.pid}/{fotos[0]['arquivo']}")
        self.assertEqual(r.status_code, 200)

    def test_catalogo_mostra_fotos(self):
        dados_f, nome = self._foto_fake()
        self.cliente.post(f"/produtos/{self.pid}/fotos",
                          data={"foto": (dados_f, nome)},
                          content_type="multipart/form-data")
        corpo = self.cliente.get("/catalogo").get_data(as_text=True)
        self.assertIn("fotos-slide", corpo)
        self.assertIn("Peça foto", corpo)


if __name__ == "__main__":
    unittest.main()
