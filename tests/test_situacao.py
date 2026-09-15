# -*- coding: utf-8 -*-
"""Sprint P3 — status evolução, validação de publicação e duplicação.

O produto agora tem um ciclo de vida (rascunho → pronto → publicado). Publicar
exige SKU, filamento, peso, tempo e preço — sem isso o catálogo teria peça sem
dado. Duplicar cria uma cópia limpa, voltando ao rascunho.
"""
from __future__ import annotations

import importlib
import os
import tempfile
import unittest


class Base(unittest.TestCase):
    def setUp(self):
        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-p3-")
        os.environ["MORUMBI_USUARIO"] = "samir"
        os.environ["MORUMBI_SENHA"] = "segredo"
        os.environ["MORUMBI_BIND"] = "127.0.0.1:5000"
        os.environ["MORUMBI_HTTPS"] = "0"
        from sistema import auth, dados
        importlib.reload(dados)
        importlib.reload(auth)
        from sistema import custo, app as modulo
        importlib.reload(custo)
        importlib.reload(modulo)
        self.dados = dados
        self.custo = custo
        self.app = modulo.criar_app()
        self.app.config["TESTING"] = True
        self.cliente = self.app.test_client()
        self.cliente.post("/entrar", data={"usuario": "samir", "senha": "segredo"})

    def _criar_filamento(self, nome="PLA Branco", preco_kg=80):
        return self.dados.salvar_filamento({
            "nome": nome, "cor": "Branco", "tipo": "PLA",
            "preco_kg": str(preco_kg), "estoque_kg": "1",
        }, "samir")

    def _produto_completo(self, filamento_id, situacao="rascunho"):
        return self.dados.salvar_produto({
            "nome": "Peça teste", "sku": "TST-001",
            "filamento_id": str(filamento_id),
            "gramas": "50", "horas": "2", "preco": "45.00",
            "ativo": "1", "situacao": situacao,
        }, "samir")

    def _produto_incompleto(self):
        return self.dados.salvar_produto({
            "nome": "Rascunho", "ativo": "1",
        }, "samir")


# ---- migração ----

class TesteMigracao(Base):
    def test_coluna_situacao_existe(self):
        with self.dados.conectar() as conn:
            colunas = {r[1] for r in conn.execute("PRAGMA table_info(produtos)")}
        self.assertIn("situacao", colunas)

    def test_produto_novo_nasce_rascunho(self):
        prod_id = self._produto_incompleto()
        prod = self.dados.produto(prod_id)
        self.assertEqual(prod["situacao"], "rascunho")

    def test_situacao_invalida_vira_rascunho(self):
        prod_id = self.dados.salvar_produto({
            "nome": "Teste", "situacao": "inventada",
        }, "samir")
        prod = self.dados.produto(prod_id)
        self.assertEqual(prod["situacao"], "rascunho")


# ---- constantes ----

class TesteConstantes(Base):
    def test_situacoes_definidas(self):
        self.assertEqual(self.dados.SITUACOES_PRODUTO,
                         ("rascunho", "pronto", "publicado"))

    def test_rotulos_existem(self):
        for s in self.dados.SITUACOES_PRODUTO:
            self.assertIn(s, self.dados.ROTULOS_SITUACAO)


# ---- validação de publicação ----

class TesteValidacaoPublicacao(Base):
    def test_publicar_completo_funciona(self):
        fil_id = self._criar_filamento()
        prod_id = self._produto_completo(fil_id, situacao="publicado")
        prod = self.dados.produto(prod_id)
        self.assertEqual(prod["situacao"], "publicado")
        self.assertEqual(prod["catalogo"], 1)

    def test_publicar_sem_sku_falha(self):
        fil_id = self._criar_filamento()
        with self.assertRaises(ValueError) as ctx:
            self.dados.salvar_produto({
                "nome": "Peça", "filamento_id": str(fil_id),
                "gramas": "50", "horas": "2", "preco": "45.00",
                "situacao": "publicado",
            }, "samir")
        self.assertIn("sku", getattr(ctx.exception, "campo", ""))

    def test_publicar_sem_filamento_falha(self):
        with self.assertRaises(ValueError) as ctx:
            self.dados.salvar_produto({
                "nome": "Peça", "sku": "TST-002",
                "gramas": "50", "horas": "2", "preco": "45.00",
                "situacao": "publicado",
            }, "samir")
        self.assertIn("filamento", getattr(ctx.exception, "campo", ""))

    def test_publicar_sem_gramas_falha(self):
        fil_id = self._criar_filamento()
        with self.assertRaises(ValueError) as ctx:
            self.dados.salvar_produto({
                "nome": "Peça", "sku": "TST-003",
                "filamento_id": str(fil_id),
                "horas": "2", "preco": "45.00",
                "situacao": "publicado",
            }, "samir")
        self.assertIn("gramas", getattr(ctx.exception, "campo", ""))

    def test_publicar_sem_horas_falha(self):
        fil_id = self._criar_filamento()
        with self.assertRaises(ValueError) as ctx:
            self.dados.salvar_produto({
                "nome": "Peça", "sku": "TST-004",
                "filamento_id": str(fil_id),
                "gramas": "50", "preco": "45.00",
                "situacao": "publicado",
            }, "samir")
        self.assertIn("horas", getattr(ctx.exception, "campo", ""))

    def test_publicar_sem_preco_falha(self):
        fil_id = self._criar_filamento()
        with self.assertRaises(ValueError) as ctx:
            self.dados.salvar_produto({
                "nome": "Peça", "sku": "TST-005",
                "filamento_id": str(fil_id),
                "gramas": "50", "horas": "2",
                "situacao": "publicado",
            }, "samir")
        self.assertIn("preco", getattr(ctx.exception, "campo", ""))

    def test_pronto_nao_exige_validacao(self):
        """Marcar como pronto não exige todos os campos."""
        prod_id = self.dados.salvar_produto({
            "nome": "Rascunho avançado", "situacao": "pronto",
        }, "samir")
        prod = self.dados.produto(prod_id)
        self.assertEqual(prod["situacao"], "pronto")

    def test_despublicar_remove_do_catalogo(self):
        fil_id = self._criar_filamento()
        prod_id = self._produto_completo(fil_id, situacao="publicado")
        prod = self.dados.produto(prod_id)
        self.assertEqual(prod["catalogo"], 1)
        self.dados.salvar_produto({
            "nome": "Peça teste", "sku": "TST-001",
            "filamento_id": str(fil_id),
            "gramas": "50", "horas": "2", "preco": "45.00",
            "situacao": "pronto",
        }, "samir", prod_id)
        prod = self.dados.produto(prod_id)
        self.assertEqual(prod["situacao"], "pronto")
        self.assertEqual(prod["catalogo"], 0)


# ---- duplicação ----

class TesteDuplicacao(Base):
    def test_duplicar_cria_copia(self):
        fil_id = self._criar_filamento()
        orig_id = self._produto_completo(fil_id)
        novo_id = self.dados.duplicar_produto(orig_id, "samir")
        novo = self.dados.produto(novo_id)
        self.assertNotEqual(novo_id, orig_id)
        self.assertIn("(Cópia)", novo["nome"])

    def test_copia_nasce_rascunho(self):
        fil_id = self._criar_filamento()
        orig_id = self._produto_completo(fil_id, situacao="publicado")
        novo_id = self.dados.duplicar_produto(orig_id, "samir")
        novo = self.dados.produto(novo_id)
        self.assertEqual(novo["situacao"], "rascunho")
        self.assertEqual(novo["catalogo"], 0)

    def test_copia_nao_tem_sku(self):
        fil_id = self._criar_filamento()
        orig_id = self._produto_completo(fil_id)
        novo_id = self.dados.duplicar_produto(orig_id, "samir")
        novo = self.dados.produto(novo_id)
        self.assertIsNone(novo["sku"])

    def test_copia_preserva_dados(self):
        fil_id = self._criar_filamento()
        orig_id = self._produto_completo(fil_id)
        novo_id = self.dados.duplicar_produto(orig_id, "samir")
        orig = self.dados.produto(orig_id)
        novo = self.dados.produto(novo_id)
        self.assertEqual(novo["gramas"], orig["gramas"])
        self.assertEqual(novo["horas"], orig["horas"])
        self.assertEqual(novo["filamento_id"], orig["filamento_id"])

    def test_copia_preserva_insumos(self):
        fil_id = self._criar_filamento()
        insumo_id = self.dados.salvar_insumo({
            "nome": "Cola", "unidade": "un", "valor_manual": "5.00",
        }, "samir")
        orig_id = self.dados.salvar_produto({
            "nome": "Com insumo", "sku": "TST-INS",
            "filamento_id": str(fil_id),
            "gramas": "50", "horas": "2", "preco": "45.00",
        }, "samir", vinculos=[(insumo_id, 2.0)])
        novo_id = self.dados.duplicar_produto(orig_id, "samir")
        novo = self.dados.produto(novo_id)
        self.assertEqual(len(novo["insumos"]), 1)
        self.assertEqual(novo["insumos"][0]["id"], insumo_id)
        self.assertAlmostEqual(novo["insumos"][0]["quantidade"], 2.0)

    def test_duplicar_inexistente_falha(self):
        with self.assertRaises(ValueError):
            self.dados.duplicar_produto(9999, "samir")


# ---- tela da ficha do produto ----

class TesteTelaFicha(Base):
    def test_situacao_aparece_na_ficha(self):
        prod_id = self._produto_incompleto()
        r = self.cliente.get(f"/produtos/{prod_id}")
        html = r.data.decode()
        self.assertIn("Situação", html)
        self.assertIn("Rascunho", html)

    def test_botao_duplicar_aparece(self):
        prod_id = self._produto_incompleto()
        r = self.cliente.get(f"/produtos/{prod_id}")
        html = r.data.decode()
        self.assertIn("Duplicar produto", html)

    def test_botao_duplicar_nao_aparece_em_novo(self):
        r = self.cliente.get("/produtos/novo")
        html = r.data.decode()
        self.assertNotIn("Duplicar produto", html)

    def test_publicar_por_formulario_valida(self):
        """Tentar publicar sem dados retorna erro 400."""
        prod_id = self._produto_incompleto()
        r = self.cliente.post(f"/produtos/{prod_id}", data={
            "nome": "Rascunho", "situacao": "publicado",
        })
        self.assertEqual(r.status_code, 400)

    def test_publicar_completo_por_formulario(self):
        fil_id = self._criar_filamento()
        prod_id = self._produto_completo(fil_id)
        r = self.cliente.post(f"/produtos/{prod_id}", data={
            "nome": "Peça teste", "sku": "TST-001",
            "filamento_id": str(fil_id),
            "gramas": "50", "horas": "2", "preco": "45.00",
            "situacao": "publicado",
        }, follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        prod = self.dados.produto(prod_id)
        self.assertEqual(prod["situacao"], "publicado")


# ---- rota de duplicação ----

class TesteRotaDuplicar(Base):
    def test_duplicar_por_rota(self):
        fil_id = self._criar_filamento()
        orig_id = self._produto_completo(fil_id)
        r = self.cliente.post(f"/produtos/{orig_id}/duplicar",
                              follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        html = r.data.decode()
        self.assertIn("(Cópia)", html)

    def test_duplicar_inexistente_404(self):
        r = self.cliente.post("/produtos/9999/duplicar")
        self.assertEqual(r.status_code, 404)


# ---- lista de produtos com situação ----

class TesteListaComSituacao(Base):
    def test_badge_rascunho_na_lista(self):
        self._produto_incompleto()
        r = self.cliente.get("/produtos")
        html = r.data.decode()
        self.assertIn("Rascunho", html)

    def test_badge_publicado_na_lista(self):
        fil_id = self._criar_filamento()
        self._produto_completo(fil_id, situacao="publicado")
        r = self.cliente.get("/produtos")
        html = r.data.decode()
        self.assertIn("Publicado", html)

    def test_badge_pronto_na_lista(self):
        prod_id = self.dados.salvar_produto({
            "nome": "Quase pronto", "situacao": "pronto",
        }, "samir")
        r = self.cliente.get("/produtos")
        html = r.data.decode()
        self.assertIn("Pronto", html)


if __name__ == "__main__":
    unittest.main()
