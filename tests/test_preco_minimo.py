# -*- coding: utf-8 -*-
"""Sprint P2 — transparencia do custo e preco minimo.

O custo sempre esteve la, mas ninguem sabia de quanto era cada parte. A
composicao visivel (filamento, maquina, maos, insumos, falha) ja existia na
ficha do produto; o que faltava era o PRECO MINIMO — abaixo dele a margem nao
cobre a meta — e os alertas visuais que mostram quando o preco praticado esta
abaixo do custo (prejuizo) ou abaixo do minimo (margem baixa).
"""
from __future__ import annotations

import importlib
import math
import os
import tempfile
import unittest


class Base(unittest.TestCase):
    def setUp(self):
        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-p2-")
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

    def _criar_produto(self, filamento_id, gramas=50, horas=2, preco=None):
        form = {
            "nome": "Peça teste", "sku": "TST-001",
            "filamento_id": str(filamento_id),
            "gramas": str(gramas), "horas": str(horas),
            "ativo": "1",
        }
        if preco is not None:
            form["preco"] = str(preco)
        return self.dados.salvar_produto(form, "samir")


# ---- preco_minimo e nivel_margem no Conta ----

class TestePrecoMinimo(Base):
    def test_formula_basica(self):
        """custo / (1 - margem_minima) arredondado para cima de 5."""
        param = self.dados.parametros()
        conta = self.custo.calcular(50, 2, 80, param=param)
        minimo = conta.preco_minimo(0.30)
        esperado = math.ceil(conta.custo / (1 - 0.30) / 5) * 5
        self.assertEqual(minimo, esperado)

    def test_preco_minimo_arredonda_para_cima_de_5(self):
        param = self.dados.parametros()
        conta = self.custo.calcular(50, 2, 80, param=param)
        minimo = conta.preco_minimo(0.30)
        self.assertEqual(minimo % 5, 0)
        custo_bruto = conta.custo / (1 - 0.30)
        self.assertGreaterEqual(minimo, custo_bruto)

    def test_preco_minimo_maior_com_margem_maior(self):
        param = self.dados.parametros()
        conta = self.custo.calcular(50, 2, 80, param=param)
        self.assertGreater(conta.preco_minimo(0.50), conta.preco_minimo(0.30))

    def test_preco_minimo_conta_incompleta(self):
        """Sem filamento, a conta e incompleta e o minimo e zero."""
        param = self.dados.parametros()
        conta = self.custo.calcular(50, 2, None, param=param)
        self.assertFalse(conta.completo)
        self.assertEqual(conta.preco_minimo(0.30), 0.0)

    def test_preco_minimo_margem_100_porcento(self):
        """Margem de 100% daria divisao por zero — retorna zero."""
        param = self.dados.parametros()
        conta = self.custo.calcular(50, 2, 80, param=param)
        self.assertEqual(conta.preco_minimo(1.0), 0.0)

    def test_preco_minimo_custo_zero(self):
        """Sem gramas, horas e acabamento, o custo e zero e o minimo tambem."""
        param = self.dados.parametros()
        conta = self.custo.calcular(0, 0, 80, minutos=0, param=param)
        self.assertEqual(conta.custo, 0.0)
        self.assertEqual(conta.preco_minimo(0.30), 0.0)


class TesteNivelMargem(Base):
    def test_saudavel(self):
        param = self.dados.parametros()
        conta = self.custo.calcular(50, 2, 80, param=param)
        self.assertGreater(conta.margem_pct, 30)
        self.assertEqual(conta.nivel_margem(), "saudavel")

    def test_prejuizo_quando_preco_menor_que_custo(self):
        param = self.dados.parametros()
        conta = self.custo.calcular(50, 2, 80, param=param)
        conta = conta.com_preco(conta.custo - 1)
        self.assertEqual(conta.nivel_margem(), "prejuizo")

    def test_prejuizo_quando_preco_igual_custo(self):
        param = self.dados.parametros()
        conta = self.custo.calcular(50, 2, 80, param=param)
        conta = conta.com_preco(conta.custo)
        self.assertEqual(conta.nivel_margem(), "prejuizo")

    def test_baixa_quando_margem_abaixo_30(self):
        param = self.dados.parametros()
        conta = self.custo.calcular(50, 2, 80, param=param)
        preco_alvo = conta.custo * 1.15
        conta = conta.com_preco(preco_alvo)
        self.assertLess(conta.margem_pct, 30)
        self.assertEqual(conta.nivel_margem(), "baixa")

    def test_incompleto_retorna_vazio(self):
        param = self.dados.parametros()
        conta = self.custo.calcular(50, 2, None, param=param)
        self.assertEqual(conta.nivel_margem(), "")


# ---- margem_minima nos parametros ----

class TesteParametroMargemMinima(Base):
    def test_padrao_existe(self):
        self.assertIn("margem_minima", self.dados.PADROES)
        self.assertEqual(self.dados.PADROES["margem_minima"], 0.30)

    def test_parametros_traz_margem_minima(self):
        param = self.dados.parametros()
        self.assertIn("margem_minima", param)
        self.assertEqual(param["margem_minima"], 0.30)


# ---- tela da ficha do produto ----

class TesteFichaProduto(Base):
    def test_preco_minimo_aparece_na_ficha(self):
        fil_id = self._criar_filamento()
        prod_id = self._criar_produto(fil_id)
        r = self.cliente.get(f"/produtos/{prod_id}")
        self.assertIn("Preço mínimo", r.data.decode())

    def test_alerta_prejuizo_na_ficha(self):
        """Preco fixo abaixo do custo gera alerta vermelho."""
        fil_id = self._criar_filamento()
        param = self.dados.parametros()
        conta = self.custo.calcular(50, 2, 80, param=param)
        preco_prejuizo = round(conta.custo * 0.5, 2)
        prod_id = self._criar_produto(fil_id, preco=preco_prejuizo)
        r = self.cliente.get(f"/produtos/{prod_id}")
        html = r.data.decode()
        self.assertIn("alerta-custo", html)
        self.assertIn("prejuízo", html)

    def test_alerta_margem_baixa_na_ficha(self):
        """Preco entre custo e minimo gera alerta amarelo."""
        fil_id = self._criar_filamento()
        param = self.dados.parametros()
        conta = self.custo.calcular(50, 2, 80, param=param)
        preco_baixo = round(conta.custo * 1.1, 2)
        minimo = conta.preco_minimo(param["margem_minima"])
        if preco_baixo >= minimo:
            preco_baixo = round(conta.custo * 1.02, 2)
        prod_id = self._criar_produto(fil_id, preco=preco_baixo)
        r = self.cliente.get(f"/produtos/{prod_id}")
        html = r.data.decode()
        self.assertIn("alerta-preco-minimo", html)

    def test_sem_alerta_quando_preco_saudavel(self):
        fil_id = self._criar_filamento()
        prod_id = self._criar_produto(fil_id)
        r = self.cliente.get(f"/produtos/{prod_id}")
        html = r.data.decode()
        self.assertNotIn('id="alerta-custo"', html)
        self.assertNotIn('id="alerta-preco-minimo"', html)

    def test_formula_do_minimo_na_nota(self):
        fil_id = self._criar_filamento()
        prod_id = self._criar_produto(fil_id)
        r = self.cliente.get(f"/produtos/{prod_id}")
        html = r.data.decode()
        self.assertIn("Mínimo = custo", html)


# ---- lista de produtos ----

class TesteListaProdutos(Base):
    def test_margem_saudavel_na_lista(self):
        fil_id = self._criar_filamento()
        self._criar_produto(fil_id)
        r = self.cliente.get("/produtos")
        html = r.data.decode()
        self.assertIn("margem-saudavel", html)

    def test_margem_prejuizo_na_lista(self):
        fil_id = self._criar_filamento()
        param = self.dados.parametros()
        conta = self.custo.calcular(50, 2, 80, param=param)
        preco_prejuizo = round(conta.custo * 0.5, 2)
        self._criar_produto(fil_id, preco=preco_prejuizo)
        r = self.cliente.get("/produtos")
        html = r.data.decode()
        self.assertIn("margem-prejuizo", html)

    def test_tooltip_com_custo_e_minimo(self):
        fil_id = self._criar_filamento()
        self._criar_produto(fil_id)
        r = self.cliente.get("/produtos")
        html = r.data.decode()
        self.assertIn("title=", html)
        self.assertIn("Custo", html)
        self.assertIn("Mín.", html)


# ---- API medir_arquivo ----

class TesteAPIMedirIncluiMinimo(Base):
    def test_resposta_tem_preco_minimo(self):
        """O endpoint de medicao retorna preco_minimo e margem_minima."""
        import io
        fil_id = self._criar_filamento()
        stl_minimo = self._stl_basico()
        r = self.cliente.post("/produtos/medir",
            data={"modelo": (io.BytesIO(stl_minimo), "cubo.stl"),
                  "filamento_id": str(fil_id)},
            content_type="multipart/form-data")
        if r.status_code == 200:
            j = r.get_json()
            self.assertIn("preco_minimo", j["conta"])
            self.assertIn("margem_minima", j["conta"])
            self.assertGreater(j["conta"]["margem_minima"], 0)

    def _stl_basico(self):
        """STL binario minimo (cubo)."""
        import struct
        header = b"\0" * 80
        triangulos = []
        faces = [
            ((0,0,0),(1,0,0),(1,1,0)),((0,0,0),(1,1,0),(0,1,0)),
            ((0,0,1),(1,1,1),(1,0,1)),((0,0,1),(0,1,1),(1,1,1)),
            ((0,0,0),(0,0,1),(1,0,1)),((0,0,0),(1,0,1),(1,0,0)),
            ((0,1,0),(1,1,1),(0,1,1)),((0,1,0),(1,1,0),(1,1,1)),
            ((0,0,0),(0,1,0),(0,1,1)),((0,0,0),(0,1,1),(0,0,1)),
            ((1,0,0),(1,1,1),(1,1,0)),((1,0,0),(1,0,1),(1,1,1)),
        ]
        for v1, v2, v3 in faces:
            triangulos.append(struct.pack("<12fH",
                0,0,0, *v1, *v2, *v3, 0))
        return header + struct.pack("<I", len(faces)) + b"".join(triangulos)


if __name__ == "__main__":
    unittest.main()
