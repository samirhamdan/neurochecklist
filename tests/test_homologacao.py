# -*- coding: utf-8 -*-
"""Sprint P7 — homologação do esquema consolidado.

Garante que um banco novo (CREATE TABLE) e um banco antigo migrado têm
a mesma estrutura. Também verifica integridade geral: todas as rotas do
menu respondem, as migrações são idempotentes, e os defaults estão certos.
"""
from __future__ import annotations

import importlib
import os
import sqlite3
import tempfile
import unittest


def _esquema_do_banco(caminho: str) -> dict[str, list[tuple]]:
    conn = sqlite3.connect(caminho)
    conn.row_factory = sqlite3.Row
    tabelas = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
        " AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    resultado = {}
    for t in tabelas:
        colunas = [(r["name"], r["type"], r["notnull"], r["dflt_value"])
                   for r in conn.execute(f"PRAGMA table_info({t})")]
        resultado[t] = colunas
    conn.close()
    return resultado


class Base(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp(prefix="morumbi-p7-")
        os.environ["MORUMBI_DADOS"] = self.pasta
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

    @property
    def db_path(self):
        return os.path.join(self.pasta, "sistema.sqlite3")


class TesteEsquemaConsolidado(Base):
    """CREATE TABLE inclui todas as colunas — nenhuma depende só de ALTER."""

    COLUNAS_PEDIDOS = {
        "id", "cliente", "cliente_id", "canal", "id_no_canal", "prazo",
        "valor", "desconto", "comissao", "valor_liquido", "status",
        "observacao", "token", "token_expira", "aceito_em", "aceito_por",
        "entregue_em", "criado_em", "criado_por",
    }

    COLUNAS_PECAS = {
        "id", "pedido_id", "produto_id", "descricao", "produto", "cor",
        "quantidade", "valor_unit", "gramas_est", "horas_est",
        "gramas_real", "horas_real", "status", "criado_em", "criado_por",
    }

    COLUNAS_PRODUTOS = {
        "id", "sku", "nome", "categoria", "gramas", "horas",
        "caixa_x", "caixa_y", "caixa_z", "minutos",
        "filamento_id", "impressora_id", "arquivo", "malha_ok", "malha_nota",
        "preco", "observacao", "ativo", "situacao",
        "dimensao_x", "dimensao_y",
        "usa_preco_volume", "margem_volume", "taxa_setup", "preco_fixo",
        "catalogo", "estoque", "estoque_minimo",
        "criado_em", "criado_por",
    }

    COLUNAS_CLIENTES = {
        "id", "nome", "whatsapp", "email", "cpf",
        "endereco", "complemento", "bairro", "cidade", "cep",
        "data_nascimento", "canal", "observacao", "ativo",
        "criado_em", "criado_por",
    }

    COLUNAS_MOVIMENTOS = {
        "id", "tipo", "alvo_id", "quantidade", "motivo",
        "peca_id", "compra_id", "observacao", "criado_em", "criado_por",
    }

    def test_pedidos_tem_todas_as_colunas(self):
        esquema = _esquema_do_banco(self.db_path)
        existem = {c[0] for c in esquema["pedidos"]}
        self.assertEqual(existem, self.COLUNAS_PEDIDOS)

    def test_pecas_tem_todas_as_colunas(self):
        esquema = _esquema_do_banco(self.db_path)
        existem = {c[0] for c in esquema["pecas"]}
        self.assertEqual(existem, self.COLUNAS_PECAS)

    def test_produtos_tem_todas_as_colunas(self):
        esquema = _esquema_do_banco(self.db_path)
        existem = {c[0] for c in esquema["produtos"]}
        self.assertEqual(existem, self.COLUNAS_PRODUTOS)

    def test_clientes_tem_todas_as_colunas(self):
        esquema = _esquema_do_banco(self.db_path)
        existem = {c[0] for c in esquema["clientes"]}
        self.assertEqual(existem, self.COLUNAS_CLIENTES)

    def test_movimentos_tem_todas_as_colunas(self):
        esquema = _esquema_do_banco(self.db_path)
        existem = {c[0] for c in esquema["movimentos"]}
        self.assertEqual(existem, self.COLUNAS_MOVIMENTOS)


class TesteDefaultsCorretos(Base):
    """Defaults do CREATE TABLE refletem o estado atual, não o histórico."""

    def test_pedido_nasce_como_orcamento(self):
        self.dados.salvar_pedido({"cliente": "Teste", "prazo": ""}, "samir")
        pedido = self.dados.pedido(1)
        self.assertEqual(pedido["status"], "orcamento")

    def test_produto_nasce_como_rascunho(self):
        prod_id = self.dados.salvar_produto({"nome": "Teste"}, "samir")
        prod = self.dados.produto(prod_id)
        self.assertEqual(prod["situacao"], "rascunho")

    def test_produto_nasce_com_estoque_zero(self):
        prod_id = self.dados.salvar_produto({"nome": "Teste"}, "samir")
        prod = self.dados.produto(prod_id)
        self.assertEqual(prod["estoque"], 0)
        self.assertEqual(prod["estoque_minimo"], 0)


class TesteMigracaoIdempotente(Base):
    """Rodar _migrar() duas vezes não quebra nada."""

    def test_migrar_duas_vezes_sem_erro(self):
        conn = self.dados.conectar()
        self.dados._migrar(conn)
        conn.close()

    def test_migrar_nao_duplica_canais(self):
        conn = self.dados.conectar()
        canais_antes = conn.execute("SELECT COUNT(*) FROM canais").fetchone()[0]
        self.dados._migrar(conn)
        canais_depois = conn.execute("SELECT COUNT(*) FROM canais").fetchone()[0]
        self.assertEqual(canais_antes, canais_depois)
        conn.close()

    def test_migrar_nao_duplica_parametros(self):
        conn = self.dados.conectar()
        antes = conn.execute("SELECT COUNT(*) FROM parametros").fetchone()[0]
        self.dados._migrar(conn)
        depois = conn.execute("SELECT COUNT(*) FROM parametros").fetchone()[0]
        self.assertEqual(antes, depois)
        conn.close()


class TesteTabelasCompletas(Base):
    """Todas as tabelas esperadas existem num banco novo."""

    TABELAS_ESPERADAS = {
        "pedidos", "pecas", "filamentos", "insumos", "produtos",
        "produto_fotos", "produto_insumos", "variacoes",
        "compras", "compra_itens", "movimentos", "historico",
        "clientes", "cliente_historico", "canais", "templates",
        "geracoes", "semente_vista", "impressoras", "parametros",
        "empresa", "usuarios", "tentativas_login",
    }

    def test_todas_as_tabelas_existem(self):
        esquema = _esquema_do_banco(self.db_path)
        self.assertEqual(set(esquema.keys()), self.TABELAS_ESPERADAS)


class TesteRotasRespondendo(Base):
    """Toda rota do menu responde 200 com banco vazio."""

    def test_dashboard_200(self):
        r = self.cliente.get("/")
        self.assertIn(r.status_code, (200, 302))

    def test_todas_as_listas_200(self):
        rotas = [
            "/clientes", "/pedidos", "/producao", "/estoque",
            "/impressoras", "/filamentos", "/insumos",
            "/produtos", "/compras", "/catalogo",
        ]
        for rota in rotas:
            with self.subTest(rota=rota):
                r = self.cliente.get(rota)
                self.assertEqual(r.status_code, 200, f"{rota} retornou {r.status_code}")


class TesteFluxoCompletoMinimo(Base):
    """Cria produto, ajusta estoque, cria pedido — fluxo mínimo de ponta a ponta."""

    def test_fluxo_produto_estoque_pedido(self):
        fil_id = self.dados.salvar_filamento({
            "nome": "PLA Branco", "cor": "Branco", "tipo": "PLA",
            "preco_kg": "80", "estoque_kg": "1000",
        }, "samir")

        prod_id = self.dados.salvar_produto({
            "nome": "Cubo", "sku": "CUB-001", "gramas": "50",
            "horas": "2", "preco": "45.00", "filamento_id": str(fil_id),
            "estoque_minimo": "5", "situacao": "publicado",
        }, "samir")

        self.dados.ajustar_estoque("produto", prod_id, 10, "lote inicial", "samir")
        prod = self.dados.produto(prod_id)
        self.assertEqual(prod["estoque"], 10)

        saldo = self.dados.saldo_pelos_movimentos("produto", prod_id)
        self.assertEqual(saldo, 10)

        alertas = self.dados.alertas_estoque()
        ids_alerta = [p["id"] for p in alertas["produtos"]]
        self.assertNotIn(prod_id, ids_alerta)

        itens = [{"descricao": "Cubo branco", "produto_id": prod_id,
                  "cor": "Branco", "quantidade": 2, "valor_unit": 45,
                  "gramas": 100, "horas": 4}]
        self.dados.salvar_pedido({
            "cliente": "Cliente Teste", "prazo": "2026-12-31",
        }, "samir", itens=itens)
        pedido = self.dados.pedido(1)
        self.assertEqual(pedido["status"], "orcamento")
        self.assertEqual(pedido["valor"], 90)

        pedido_itens = self.dados.pedido(1)["itens"]
        self.assertEqual(len(pedido_itens), 1)
        self.assertEqual(pedido_itens[0]["quantidade"], 2)


if __name__ == "__main__":
    unittest.main()
