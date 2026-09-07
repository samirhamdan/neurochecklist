"""Testes das telas de entrada e do painel.

A maior parte olha para a autenticacao: e a unica coisa aqui que, se estiver
errada, expoe dado de cliente.
"""

import importlib
import os
import tempfile
import time
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
                "INSERT INTO filamentos (nome, tipo, cor, gramas, minimo, criado_em)"
                " VALUES ('PLA Vermelho', 'PLA', 'Vermelho', 120, 300, ?)", (agora(),))

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


@unittest.skipUnless(TEM_FLASK, "flask nao instalado")
def _logo_disponivel():
    """O gerador de logo precisa de opencv, trimesh e scipy — 180 MB.

    Quem so quer o painel instala `pip install -e ".[sistema]"` e nao tem
    nada disso. A suite tem que dizer "pulei" nesse caso, e nao quebrar com
    ImportError vindo de dentro de um teste de rota.
    """
    try:
        import sistema.logo.app  # noqa: F401
    except Exception:
        return False
    return True


LOGO_INSTALADO = _logo_disponivel()
SEM_LOGO = "gerador de logo nao instalado (opencv/trimesh)"


class TesteJuncao(unittest.TestCase):
    """O gerador de logo montado em /logo, com uma porta de entrada so.

    O teste que mais importa aqui e o de fora: se a guarda falhar, o gerador
    fica aberto na internet, porque o cadeado Basic dele foi retirado.
    """

    def montar_wsgi(self):
        import importlib

        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-juncao-")
        os.environ["MORUMBI_USUARIO"] = "samir"
        os.environ["MORUMBI_SENHA"] = "segredo"
        os.environ["MORUMBI_BIND"] = "127.0.0.1:5000"
        os.environ["MORUMBI_HTTPS"] = "0"

        from sistema import auth, dados
        importlib.reload(dados)
        importlib.reload(auth)
        from sistema import app as modulo
        importlib.reload(modulo)
        import wsgi
        importlib.reload(wsgi)
        wsgi.sistema.config["TESTING"] = True
        return wsgi

    def setUp(self):
        self.wsgi = self.montar_wsgi()
        self.cliente = self.wsgi.sistema.test_client()

    def test_logo_sem_entrar_manda_para_a_entrada(self):
        r = self.cliente.get("/logo/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/entrar", r.headers["Location"])
        self.assertIn("destino=/logo/", r.headers["Location"])

    def test_api_do_logo_tambem_esta_guardada(self):
        """O cadeado Basic saiu; se a guarda falhar, a API fica aberta."""

        for caminho in ("/logo/api/enviar", "/logo/api/gerar", "/logo/api/baixar/abc"):
            with self.subTest(caminho=caminho):
                r = self.cliente.post(caminho)
                self.assertEqual(r.status_code, 302, f"{caminho} respondeu sem sessao")
                self.assertIn("/entrar", r.headers["Location"])

    @unittest.skipUnless(LOGO_INSTALADO, SEM_LOGO)
    def test_logo_abre_depois_de_entrar(self):
        self.cliente.post("/entrar", data={"usuario": "samir", "senha": "segredo"})
        r = self.cliente.get("/logo/")
        self.assertEqual(r.status_code, 200)
        corpo = r.get_data(as_text=True)
        self.assertIn("gerador de logo", corpo.lower())
        self.assertIn("Solte um logo aqui", corpo)

    @unittest.skipUnless(LOGO_INSTALADO, SEM_LOGO)
    def test_interface_do_logo_usa_prefixo(self):
        """Montado sob /logo, as chamadas nao podem ser absolutas."""

        self.cliente.post("/entrar", data={"usuario": "samir", "senha": "segredo"})
        corpo = self.cliente.get("/logo/").get_data(as_text=True)
        self.assertIn("const BASE = location.pathname", corpo)
        self.assertIn("BASE + '/api/enviar'", corpo)
        self.assertNotIn("fetch('/api/", corpo)

    def test_painel_continua_de_pe(self):
        self.cliente.post("/entrar", data={"usuario": "samir", "senha": "segredo"})
        self.assertEqual(self.cliente.get("/").status_code, 200)
        # /letreiros redireciona para /letreiros/ desde o C1 -- o nucleo e
        # carregado por caminho relativo. Link antigo tem que continuar valendo.
        self.assertEqual(self.cliente.get("/letreiros", follow_redirects=True).status_code, 200)
        self.assertEqual(self.cliente.get("/saude").status_code, 200)

    def test_gerador_quebrado_nao_derruba_o_sistema(self):
        """Dependencia faltando tira /logo do ar, nao o painel."""

        import wsgi

        quebrado = wsgi._com_sessao(wsgi._explicar_falha("ModuleNotFoundError: cv2"))
        from werkzeug.middleware.dispatcher import DispatcherMiddleware

        wsgi.sistema.wsgi_app = DispatcherMiddleware(
            wsgi.criar_app().wsgi_app, {"/logo": quebrado})
        cliente = wsgi.sistema.test_client()
        cliente.post("/entrar", data={"usuario": "samir", "senha": "segredo"})
        self.assertEqual(cliente.get("/").status_code, 200, "o painel tem que continuar")
        r = cliente.get("/logo/")
        self.assertEqual(r.status_code, 503)
        self.assertIn("cv2", r.get_data(as_text=True))


class TesteImplantacao(unittest.TestCase):
    """Os arquivos de implantacao apontam para caminhos que existem.

    A juncao moveu o gerador de logo para dentro do sistema e levou o
    wsgi.py e o gunicorn.conf.py para a raiz do repositorio. Duas dessas
    referencias ficaram para tras e eu so achei rodando na mao: o
    atualizar.sh ainda procurava app/requirements.txt, e a mensagem final
    do script de instalacao mandava apontar o ExecStart para a subpasta,
    onde o wsgi.py nao esta mais. As duas so apareceriam no dia do deploy,
    com o site fora do ar. Estes testes existem para isso nao se repetir.
    """

    RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _ler(self, *partes):
        with open(os.path.join(self.RAIZ, *partes), encoding="utf-8") as f:
            return f.read()

    def test_gunicorn_conf_carrega_e_e_sensata(self):
        espaco = {"__file__": os.path.join(self.RAIZ, "gunicorn.conf.py")}
        os.environ["MORUMBI_BIND"] = "172.18.0.1:5000"
        try:
            exec(compile(self._ler("gunicorn.conf.py"), "gunicorn.conf.py", "exec"), espaco)
        finally:
            os.environ.pop("MORUMBI_BIND", None)
        self.assertEqual(espaco["bind"], "172.18.0.1:5000", "tem que obedecer o systemd")
        self.assertEqual(espaco["workers"], 1, "2 GB de RAM nao aguentam mais de um")
        # Gerar STL de logo complexo passa facil dos 30s padrao do gunicorn.
        self.assertGreaterEqual(espaco["timeout"], 120)

    def test_caminhos_citados_pela_implantacao_existem(self):
        """Todo arquivo que os scripts mandam o Samir usar tem que existir."""
        citados = {
            "wsgi.py": "wsgi:app",
            "gunicorn.conf.py": "-c ... gunicorn.conf.py",
            "requirements.txt": "pip install -r",
        }
        for arquivo, onde in citados.items():
            self.assertTrue(
                os.path.isfile(os.path.join(self.RAIZ, arquivo)),
                f"{arquivo} e citado na implantacao ({onde}) e nao esta na raiz")

        # assertTrue e nao assertIn de proposito: assertIn imprime o arquivo
        # inteiro na falha, e sao 100 linhas de shell para dizer uma coisa so.
        atualizar = self._ler("implantar", "atualizar.sh")
        self.assertTrue("-- requirements.txt" in atualizar,
                        "atualizar.sh: o requirements da raiz e o unico que existe"
                        " depois da juncao")
        self.assertTrue("app/requirements.txt" not in atualizar,
                        "atualizar.sh ainda procura o requirements na subpasta app/")
        # A raiz responde 302 para /entrar; um 302 nao prova que o app esta sao.
        self.assertTrue("/saude" in atualizar,
                        "atualizar.sh: a checagem de saude precisa de rota sem senha")

    def test_servico_sobe_o_sistema_inteiro(self):
        """Nao o gerador de logo sozinho, que era o que subia antes."""
        modelo = self._ler("implantar", "morumbi3d.service")
        self.assertTrue("wsgi:app" in modelo,
                        "o servico tem que subir o wsgi da raiz")
        self.assertTrue("WorkingDirectory=/opt/morumbi3d\n" in modelo,
                        "o WorkingDirectory e a raiz: e la que o wsgi.py mora")

    def test_instalador_confere_antes_de_trocar(self):
        """Ele apaga a instalacao que esta rodando. Tem que olhar antes."""
        instalar = self._ler("implantar", "instalar.sh")
        for exigido in ("wsgi.py", "gunicorn.conf.py", "requirements.txt",
                        "sistema/logo/app.py"):
            self.assertTrue(exigido in instalar,
                            f"instalar.sh nao confere se {exigido} veio no clone")
        # O venv custa 180 MB e um pip install que as vezes falha por RAM.
        self.assertTrue("-not -name venv" in instalar,
                        "instalar.sh apagaria o venv junto")
        # Sem isto, deploy quebrado fica quebrado ate o cliente reclamar.
        self.assertTrue("desfazer" in instalar and "/saude" in instalar,
                        "instalar.sh precisa conferir a saude e saber desfazer")

    def test_scripts_liberam_o_repo_antes_de_usar_git(self):
        """Git recusa repositorio de outro dono, e aqui isso e o normal.

        O instalador entrega os arquivos ao usuario do servico (o gunicorn
        roda como ele) e o deploy roda como root. Git 2.35.6+ chama isso de
        "dubious ownership" e para. Aconteceu no servidor de verdade, no
        primeiro atualizar.sh depois da instalacao.
        """
        for arquivo in (("implantar", "atualizar.sh"), ("implantar", "instalar.sh")):
            texto = self._ler(*arquivo)
            nome = arquivo[-1]
            self.assertTrue("safe.directory" in texto,
                            f"{nome} nao libera o repo e vai parar em dubious ownership")
            # --add sozinho repete a linha a cada deploy.
            self.assertTrue("--get-all safe.directory" in texto,
                            f"{nome} precisa conferir antes de adicionar, senao duplica")

        # Ordem importa: liberar depois do primeiro git nao adianta nada.
        texto = self._ler("implantar", "atualizar.sh")
        self.assertLess(texto.index("safe.directory"), texto.index("git rev-parse HEAD"),
                        "atualizar.sh usa git antes de liberar o repo")

    def test_instalador_nao_escreve_segredo_no_servico(self):
        """A senha real so existe na maquina; o repositorio nao a conhece."""
        instalar = self._ler("implantar", "instalar.sh")
        self.assertTrue("MORUMBI_SENHA=" not in instalar,
                        "instalar.sh nao pode escrever senha no servico")
        # A unica linha do servico que ele tem permissao de mexer.
        mexidas = [l for l in instalar.splitlines()
                   if l.strip().startswith("sed -i") and "UNIDADE" in l]
        self.assertEqual(len(mexidas), 1, f"mexeu em mais coisa do servico: {mexidas}")
        self.assertTrue("MORUMBI_WORKERS" in mexidas[0], mexidas[0])

    def test_service_modelo_nao_leva_senha_de_verdade(self):
        modelo = self._ler("implantar", "morumbi3d.service")
        self.assertTrue("MORUMBI_SENHA=TROQUE_ESTA_SENHA" in modelo,
                        "o modelo no git nao pode carregar a senha de verdade")
        # O bind do gateway do Docker: o Caddy roda em container e nao
        # alcanca o 127.0.0.1 do host.
        self.assertTrue("MORUMBI_BIND=172.18.0.1:5000" in modelo,
                        "o modelo tem que trazer o bind do gateway do Docker")


@unittest.skipUnless(LOGO_INSTALADO, SEM_LOGO)
class TesteFaxinaCompartilhada(unittest.TestCase):
    """A juncao fez os dois apps dividirem a mesma MORUMBI_DADOS.

    O gerador de logo apaga sozinho o que passa da validade, para o disco do
    VPS nao encher. Antes ele era dono da pasta e podia apagar qualquer
    coisa velha; agora o banco de pedidos e a chave que assina os cookies
    moram no mesmo lugar.
    """

    def setUp(self):
        import shutil as _shutil
        from sistema.logo import app as modulo

        self.modulo = modulo
        self.pasta = tempfile.mkdtemp(prefix="morumbi-faxina-")
        self.addCleanup(_shutil.rmtree, self.pasta, ignore_errors=True)

        self.pasta_antiga, modulo.PASTA = modulo.PASTA, self.pasta
        self.validade, modulo.VALIDADE_H = modulo.VALIDADE_H, 12.0

    def tearDown(self):
        self.modulo.PASTA = self.pasta_antiga
        self.modulo.VALIDADE_H = self.validade

    def _criar(self, nome, pasta=True, velho=True):
        alvo = os.path.join(self.pasta, nome)
        if pasta:
            os.makedirs(alvo)
        else:
            with open(alvo, "w") as f:
                f.write("x")
        if velho:
            antigo = time.time() - 48 * 3600
            os.utime(alvo, (antigo, antigo))
        return alvo

    def test_apaga_upload_vencido_e_so_ele(self):
        vencido = self._criar("a1b2c3d4e5f6")
        recente = self._criar("0123456789ab", velho=False)
        banco = self._criar("sistema.sqlite3", pasta=False)
        chave = self._criar("chave_sessao", pasta=False)
        # MPLCONFIGDIR, que o morumbi3d.service aponta para dentro daqui.
        matplotlib = self._criar(".mpl")
        # Espaco para o painel crescer sem tropecar na faxina alheia.
        pedidos = self._criar("pedidos")

        self.modulo.faxina()

        self.assertFalse(os.path.exists(vencido), "upload vencido tinha que sair")
        for sobrevivente in (recente, banco, chave, matplotlib, pedidos):
            self.assertTrue(os.path.exists(sobrevivente),
                            f"a faxina do gerador de logo comeu {os.path.basename(sobrevivente)}")


class TesteMarca(unittest.TestCase):
    """O logotipo e um arquivo que pode nao estar la.

    <img> com arquivo inexistente nao falha: mostra o icone de imagem
    quebrada, que numa tela de entrada e pior do que nao ter logotipo.
    Entao as telas escrevem o nome quando o arquivo falta.

    Cada teste aponta o modulo para uma pasta propria. A primeira versao
    olhava a pasta de verdade e passou enquanto ela estava vazia; no dia
    em que o arquivo chegou, o teste quebrou sem que nada estivesse
    errado -- ele estava medindo o repositorio, e nao o comportamento.
    """

    def setUp(self):
        import importlib
        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-marca-")
        os.environ["MORUMBI_USUARIO"] = "samir"
        os.environ["MORUMBI_SENHA"] = "segredo"
        os.environ["MORUMBI_BIND"] = "127.0.0.1:5000"
        os.environ["MORUMBI_HTTPS"] = "0"
        from sistema import auth, dados
        importlib.reload(dados); importlib.reload(auth)
        from sistema import app as modulo
        importlib.reload(modulo)
        self.modulo = modulo

        self.estaticos = tempfile.mkdtemp(prefix="morumbi-static-")
        modulo.ESTATICOS = self.estaticos
        self.app = modulo.criar_app()
        self.app.config["TESTING"] = True
        self.cliente = self.app.test_client()

    def _por_arquivo(self, nome):
        with open(os.path.join(self.estaticos, nome), "wb") as f:
            f.write(b"x")

    def test_sem_arquivo_escreve_o_nome(self):
        corpo = self.cliente.get("/entrar").get_data(as_text=True)
        self.assertTrue('class="simbolo"' not in corpo, "mostrou <img> sem arquivo")
        self.assertTrue('class="tres">3<' in corpo, "faltou o 3 laranja")
        self.assertTrue('class="de">D<' in corpo, "faltou o D azul")

    def test_com_arquivo_usa_a_imagem(self):
        self._por_arquivo("marca-simbolo.webp")
        corpo = self.cliente.get("/entrar").get_data(as_text=True)
        self.assertTrue("marca-simbolo.webp" in corpo, "nao usou o arquivo que existe")
        # O nome vem escrito logo abaixo, entao o simbolo e decorativo: um
        # alt repetindo "Morumbi 3D" faria o leitor de tela dizer duas vezes.
        self.assertTrue('class="simbolo" src' in corpo and 'alt=""' in corpo,
                        "o simbolo precisa de alt vazio, e nao repetido")
        # O nome e o lema ficam em texto sempre: na trava inteira eles sao
        # grafite escuro e sumiriam neste fundo.
        self.assertTrue('class="nome"' in corpo, "sumiu o nome escrito")
        self.assertTrue('class="lema"' in corpo, "sumiu o lema escrito")

    def test_prefere_svg_a_bitmap(self):
        self._por_arquivo("marca-simbolo.png")
        self._por_arquivo("marca-simbolo.svg")
        self.assertEqual(self.modulo.arquivo_da_marca("marca-simbolo"),
                         "marca-simbolo.svg")

    def test_aparece_sem_reiniciar(self):
        """Basta soltar o arquivo na pasta; nao pode exigir restart."""
        corpo = self.cliente.get("/entrar").get_data(as_text=True)
        self.assertTrue("marca-simbolo" not in corpo)
        self._por_arquivo("marca-simbolo.webp")
        corpo = self.cliente.get("/entrar").get_data(as_text=True)
        self.assertTrue("marca-simbolo.webp" in corpo,
                        "so achou a marca depois de reiniciar o servico")


class TestePreparoDaMarca(unittest.TestCase):
    """O recorte do M depende de um detalhe do arquivo original.

    Ele tem um halo de alfa 1..8 na imagem inteira. O getbbox() do Pillow
    corta em alfa>0, entao sem limpar o halo o M sai com 1135 de largura em
    vez de 693 -- proporcao 1,84 no lugar de 1,16, um M esticado. Isso nao
    da erro em lugar nenhum: so sai torto na tela.
    """

    def setUp(self):
        try:
            import numpy  # noqa: F401
            from PIL import Image  # noqa: F401
        except ImportError:
            self.skipTest("preparar_marca precisa de Pillow e numpy")
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.original = os.path.join(raiz, "marca", "morumbi3d-original.png")
        if not os.path.exists(self.original):
            self.skipTest("o original da marca nao esta no repositorio")
        import importlib.util
        caminho = os.path.join(raiz, "ferramentas", "preparar_marca.py")
        spec = importlib.util.spec_from_file_location("preparar_marca", caminho)
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)

    def _simbolo(self, limpar):
        from PIL import Image
        img = Image.open(self.original)
        if limpar:
            img = self.mod.sem_halo(img)
        return self.mod.apara(img.crop((0, 0, img.width, self.mod.FIM_DO_SIMBOLO)))

    def test_o_M_sai_na_proporcao_certa(self):
        s = self._simbolo(limpar=True)
        prop = s.width / s.height
        self.assertAlmostEqual(prop, 1.16, delta=0.04,
                               msg=f"o M saiu {s.width}x{s.height} (proporcao {prop:.2f})")

    def test_sem_limpar_o_halo_o_M_sai_esticado(self):
        """Se este teste parar de falhar, o halo sumiu do original."""
        s = self._simbolo(limpar=False)
        self.assertGreater(s.width / s.height, 1.5,
                           "o halo nao esta mais no original: sem_halo() virou opcional")
