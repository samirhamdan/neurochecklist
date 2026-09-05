"""Testes das telas de entrada e do painel.

A maior parte olha para a autenticacao: e a unica coisa aqui que, se estiver
errada, expoe dado de cliente.
"""

import importlib
import os
import tempfile
import unittest

try:
    import flask  # noqa: F401
    TEM_FLASK = True
except ImportError:
    TEM_FLASK = False


def montar(senha="segredo", usuario="samir", bind="127.0.0.1:5000"):
    """Sobe um app limpo com as variaveis pedidas.

    auth.py le as variaveis no import, entao nao basta trocar o ambiente:
    os modulos precisam ser recarregados.
    """

    os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-teste-")
    os.environ["MORUMBI_USUARIO"] = usuario
    os.environ["MORUMBI_SENHA"] = senha
    os.environ["MORUMBI_BIND"] = bind
    os.environ["MORUMBI_HTTPS"] = "0"   # o cliente de teste fala http

    from sistema import auth, dados
    importlib.reload(dados)
    importlib.reload(auth)
    from sistema import app as modulo
    importlib.reload(modulo)

    aplicacao = modulo.criar_app()
    aplicacao.config["TESTING"] = True
    return aplicacao


@unittest.skipUnless(TEM_FLASK, "flask nao instalado")
class TesteEntrada(unittest.TestCase):
    def setUp(self):
        self.app = montar()
        self.cliente = self.app.test_client()

    def test_tela_de_entrada_aparece(self):
        r = self.cliente.get("/entrar")
        self.assertEqual(r.status_code, 200)
        corpo = r.get_data(as_text=True)
        self.assertIn("Entrar", corpo)
        self.assertIn('name="usuario"', corpo)
        self.assertIn('type="password"', corpo)

    def test_painel_exige_entrar(self):
        r = self.cliente.get("/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/entrar", r.headers["Location"])

    def test_senha_certa_entra(self):
        r = self.cliente.post("/entrar", data={"usuario": "samir", "senha": "segredo"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.cliente.get("/").status_code, 200)

    def test_senha_errada_recusa(self):
        r = self.cliente.post("/entrar", data={"usuario": "samir", "senha": "errada"})
        self.assertEqual(r.status_code, 401)
        self.assertEqual(self.cliente.get("/").status_code, 302)

    def test_mensagem_nao_entrega_quem_existe(self):
        """Usuario inexistente e senha errada dizem a MESMA coisa."""

        a = self.cliente.post("/entrar", data={"usuario": "samir", "senha": "x"})
        b = self.cliente.post("/entrar", data={"usuario": "ninguem", "senha": "x"})
        self.assertIn("não conferem", a.get_data(as_text=True))
        self.assertIn("não conferem", b.get_data(as_text=True))

    def test_sair_derruba_a_sessao(self):
        self.cliente.post("/entrar", data={"usuario": "samir", "senha": "segredo"})
        self.assertEqual(self.cliente.get("/").status_code, 200)
        self.cliente.post("/sair")
        self.assertEqual(self.cliente.get("/").status_code, 302)

    def test_cookie_de_sessao_e_protegido(self):
        r = self.cliente.post("/entrar", data={"usuario": "samir", "senha": "segredo"})
        cookie = r.headers.get("Set-Cookie", "")
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)

    def test_tentativas_demais_travam(self):
        for _ in range(5):
            self.cliente.post("/entrar", data={"usuario": "samir", "senha": "errada"})
        r = self.cliente.post("/entrar", data={"usuario": "samir", "senha": "errada"})
        self.assertEqual(r.status_code, 429)
        # Trava mesmo com a senha certa: quem esta adivinhando nao passa
        # por sorte na sexta tentativa.
        r = self.cliente.post("/entrar", data={"usuario": "samir", "senha": "segredo"})
        self.assertEqual(r.status_code, 429)

    def test_entrar_certo_limpa_as_tentativas(self):
        for _ in range(3):
            self.cliente.post("/entrar", data={"usuario": "samir", "senha": "errada"})
        self.cliente.post("/entrar", data={"usuario": "samir", "senha": "segredo"})
        self.cliente.post("/sair")
        for _ in range(3):
            r = self.cliente.post("/entrar", data={"usuario": "samir", "senha": "errada"})
        self.assertEqual(r.status_code, 401, "o contador deveria ter zerado")

    def test_destino_externo_e_ignorado(self):
        """//site.fora seria um jeito de usar a tela de login para levar embora."""

        r = self.cliente.post(
            "/entrar?destino=//exemplo.invalido/x",
            data={"usuario": "samir", "senha": "segredo"},
        )
        self.assertEqual(r.status_code, 302)
        self.assertNotIn("exemplo.invalido", r.headers["Location"])

    def test_destino_interno_e_respeitado(self):
        r = self.cliente.post(
            "/entrar?destino=/letreiros",
            data={"usuario": "samir", "senha": "segredo"},
        )
        self.assertTrue(r.headers["Location"].endswith("/letreiros"))

    def test_saude_nao_pede_senha(self):
        r = self.cliente.get("/saude")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["ok"])


@unittest.skipUnless(TEM_FLASK, "flask nao instalado")
class TesteConfiguracao(unittest.TestCase):
    def test_sem_senha_em_endereco_publico_nao_sobe(self):
        # Comparar pela classe nao serve aqui: montar() recarrega o modulo, e
        # a recarga cria um objeto de classe NOVO — o `except` da classe
        # importada antes nao pegaria a excecao levantada depois.
        try:
            montar(senha="", bind="172.18.0.1:5000")
        except Exception as erro:
            self.assertEqual(type(erro).__name__, "ConfiguracaoInsegura")
            self.assertIn("MORUMBI_SENHA", str(erro))
        else:
            self.fail("deveria ter recusado subir sem senha em endereco publico")

    def test_sem_senha_local_sobe_aberto(self):
        app = montar(senha="", bind="127.0.0.1:5000")
        cliente = app.test_client()
        painel = cliente.get("/")
        self.assertEqual(painel.status_code, 200)
        # O aviso mora no painel, nao na tela de entrada: sem senha ninguem
        # chega a ver a tela de entrada.
        self.assertIn("MORUMBI_SENHA", painel.get_data(as_text=True))

    def test_chave_de_sessao_sobrevive_ao_restart(self):
        app = montar()
        primeira = app.secret_key
        from sistema import app as modulo
        importlib.reload(modulo)
        self.assertEqual(modulo.criar_app().secret_key, primeira)


@unittest.skipUnless(TEM_FLASK, "flask nao instalado")
class TestePainel(unittest.TestCase):
    def setUp(self):
        self.app = montar()
        self.cliente = self.app.test_client()
        self.cliente.post("/entrar", data={"usuario": "samir", "senha": "segredo"})

    def test_painel_vazio_ensina_o_proximo_passo(self):
        corpo = self.cliente.get("/").get_data(as_text=True)
        self.assertIn("Ainda não há nada registrado", corpo)
        self.assertIn("canal de origem", corpo)

    def test_painel_com_dados_mostra_fila_e_pedidos(self):
        from sistema.dados import agora, conectar

        with conectar() as conn:
            conn.execute(
                "INSERT INTO pedidos (id, cliente, canal, prazo, valor, status, criado_em)"
                " VALUES (1, 'Ana Paula', 'Instagram', '2030-01-01', 180.0, 'novo', ?)",
                (agora(),))
            for cor, horas in (("Vermelho", 3.4), ("Vermelho", 2.1), ("Branco", 1.8)):
                conn.execute(
                    "INSERT INTO pecas (pedido_id, descricao, cor, horas_est, status, criado_em)"
                    " VALUES (1, ?, ?, ?, 'na fila', ?)",
                    (f"Letreiro {cor}", cor, horas, agora()))
            conn.execute(
                "INSERT INTO filamento (cor, gramas, minimo) VALUES ('Vermelho', 120, 300)")

        corpo = self.cliente.get("/").get_data(as_text=True)
        self.assertIn("Ana Paula", corpo)
        self.assertIn("Fila de produção", corpo)
        self.assertIn("7.3 h", corpo)          # 3,4 + 2,1 + 1,8
        self.assertIn("6 g de purga", corpo)   # duas cores = uma troca
        self.assertIn("abaixo do mínimo", corpo)
        self.assertNotIn("Ainda não há nada", corpo)


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(TEM_FLASK, "flask nao instalado")
class TesteFila(unittest.TestCase):
    """A fila existe para gastar menos purga. Se ela nao agrupa, nao serve."""

    def setUp(self):
        self.app = montar()
        self.cliente = self.app.test_client()
        self.cliente.post("/entrar", data={"usuario": "samir", "senha": "segredo"})

    def semear(self, pecas):
        from sistema.dados import agora, conectar

        with conectar() as conn:
            for i, (cliente, prazo) in enumerate(
                    [("A", "2030-01-01"), ("B", "2030-01-05"), ("C", "2030-01-09")], 1):
                conn.execute(
                    "INSERT INTO pedidos (id, cliente, canal, prazo, status, criado_em)"
                    " VALUES (?, ?, 'teste', ?, 'novo', ?)", (i, cliente, prazo, agora()))
            for pedido, cor in pecas:
                conn.execute(
                    "INSERT INTO pecas (pedido_id, descricao, cor, horas_est, status, criado_em)"
                    " VALUES (?, ?, ?, 1.0, 'na fila', ?)",
                    (pedido, f"peca {cor} do pedido {pedido}", cor, agora()))

    def test_mesma_cor_em_pedidos_diferentes_nao_se_separa(self):
        # Branco no pedido 1 e no 3, Azul no 2: ordenar so por prazo daria
        # Branco, Azul, Branco — duas trocas onde basta uma.
        self.semear([(1, "Branco"), (2, "Azul"), (3, "Branco")])
        from sistema.dados import resumo

        r = resumo()
        self.assertEqual(len(r["fila_por_cor"]["Branco"]), 2)
        self.assertEqual(r["trocas_de_cor"], 1)
        self.assertEqual(r["purga_g"], 6)
        cores_na_ordem = [p["cor"] for p in r["fila"]]
        self.assertEqual(cores_na_ordem, ["Branco", "Branco", "Azul"])

    def test_cor_com_a_peca_mais_urgente_vem_primeiro(self):
        self.semear([(3, "Preto"), (1, "Verde")])
        from sistema.dados import resumo

        # Verde esta no pedido de prazo mais curto, entao abre a fila.
        self.assertEqual(list(resumo()["fila_por_cor"]), ["Verde", "Preto"])

    def test_uma_cor_so_nao_tem_troca(self):
        self.semear([(1, "Preto"), (2, "Preto")])
        from sistema.dados import resumo

        r = resumo()
        self.assertEqual(r["trocas_de_cor"], 0)
        self.assertEqual(r["purga_g"], 0)
