# -*- coding: utf-8 -*-
"""Sprint U4 -- formularios que perdoam.

Medido a 420 px antes deste sprint, e sao estes os numeros que ele existe
para mudar:

  * para chegar no botao Salvar era preciso rolar **1.665 px** no cadastro de
    produto, 765 no de template e 370 no de pedido. Formulario que exige rolar
    dezessete campos para achar o botao e formulario que se abandona no meio;
  * **nenhum** dos oito formularios avisava antes de perder o que foi digitado;
  * o erro dizia o motivo numa faixa no topo e nada mais -- num cadastro de
    dezessete campos, achar QUAL campo e caca ao tesouro.

Um item do plano nao se confirmou na medida: "teclado numerico nos campos de
numero -- hoje abre o alfabetico". `type="number"` ja abre teclado numerico.
O campo que abria o alfabetico era um so, e era o mais digitado no telefone:
o WhatsApp do cliente.

Os testes de navegador ficam em tests/test_navegador.py -- alcance de botao e
aviso de saida nao se medem lendo HTML.
"""
from __future__ import annotations

import importlib
import os
import re
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = os.path.join(RAIZ, "sistema", "templates")

# As telas onde se digita alguma coisa que vai para o banco.
FORMULARIOS = ("cliente.html", "compra.html", "filamento.html", "insumo.html",
               "pedido.html", "produto.html", "template.html", "canais.html")


def texto(nome):
    with open(os.path.join(TEMPLATES, nome), encoding="utf-8") as fh:
        return fh.read()


class TesteOTecladoQueAbre(unittest.TestCase):
    """O aparelho escolhe o teclado pelo que a marcacao pede. Se ela nao
    pedir, ele chuta -- e o chute do iPhone em `type=number` e um teclado sem
    virgula, numa casa onde quase todo numero tem casa decimal."""

    def test_todo_campo_numerico_diz_qual_teclado_quer(self):
        for nome in sorted(os.listdir(TEMPLATES)):
            if not nome.endswith(".html"):
                continue
            corpo = texto(nome)
            for campo in re.findall(r"<input[^>]*type=\"number\"[^>]*>", corpo):
                self.assertIn("inputmode", campo,
                              f"{nome}: campo numérico sem inputmode -> {campo[:70]}")

    def test_passo_inteiro_pede_teclado_sem_virgula(self):
        """`step=1` e contagem: gramas, minutos, quantidade. Virgula ali e ruido."""
        corpo = texto("filamento.html")
        gramas = re.search(r"<input[^>]*name=\"gramas\"[^>]*>", corpo).group(0)
        preco = re.search(r"<input[^>]*name=\"preco_kg\"[^>]*>", corpo).group(0)
        self.assertIn('inputmode="numeric"', gramas)
        self.assertIn('inputmode="decimal"', preco)

    def test_o_whatsapp_abre_o_teclado_de_discagem(self):
        """Era o unico campo da casa que abria o teclado de LETRAS."""
        campo = re.search(r"<input[^>]*name=\"whatsapp\"[^>]*>", texto("cliente.html"), re.S)
        self.assertIsNotNone(campo)
        self.assertIn('type="tel"', campo.group(0))
        self.assertIn('autocomplete="tel"', campo.group(0))


class TesteOTrabalhoNaoSeperde(unittest.TestCase):
    def test_todo_formulario_de_cadastro_avisa_antes_de_sair(self):
        for nome in FORMULARIOS:
            corpo = texto(nome)
            self.assertTrue("data-avisar" in corpo,
                            f"{nome}: formulário sem aviso de saída")

    def test_o_aviso_mora_na_casca_e_nao_em_cada_tela(self):
        """Escrito por formulário, o próximo cadastro nasceria sem ele."""
        self.assertTrue("beforeunload" in texto("base.html"))
        for nome in FORMULARIOS:
            self.assertTrue("beforeunload" not in texto(nome),
                            f"{nome}: segunda cópia do aviso de saída")

    def test_a_rodinha_do_mouse_nao_pode_mexer_no_numero(self):
        """Com o campo focado, rolar a página troca 83,7 g por 82,7 g."""
        self.assertTrue('type === "number"' in texto("base.html"))
        self.assertTrue("blur()" in texto("base.html"))


class TesteOBotaoAlcancavel(unittest.TestCase):
    def test_cada_formulario_tem_UMA_barra_principal(self):
        """Duas barras grudadas no pé disputariam o mesmo lugar da tela."""
        for nome in FORMULARIOS:
            self.assertEqual(texto(nome).count("acoes principal"), 1, nome)

    def test_a_barra_e_filha_do_formulario(self):
        """`position:sticky` só gruda dentro do próprio pai: numa barra dentro
        de um cartão de 200 px não há para onde grudar."""
        for nome in ("produto.html", "pedido.html"):
            corpo = texto(nome)
            depois = corpo[corpo.index("acoes principal"):]
            entre = depois[:depois.index("</form>")]
            self.assertTrue("<div class=\"cartao" not in entre,
                            f"{nome}: a barra ficou dentro de um cartão")


class Base(unittest.TestCase):
    def setUp(self):
        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-form-")
        os.environ["MORUMBI_USUARIO"] = "samir"
        os.environ["MORUMBI_SENHA"] = "segredo"
        os.environ["MORUMBI_BIND"] = "127.0.0.1:5000"
        os.environ["MORUMBI_HTTPS"] = "0"
        from sistema import auth, dados
        importlib.reload(dados)
        importlib.reload(auth)
        from sistema import app as modulo
        importlib.reload(modulo)
        self.d = dados
        self.app = modulo.criar_app()
        self.app.config["TESTING"] = True
        self.cliente = self.app.test_client()
        self.cliente.post("/entrar", data={"usuario": "samir", "senha": "segredo"})


class TesteOErroApontaOCampo(Base):
    """A promessa central do sprint.

    O topo diz que algo deu errado; só o campo diz o quê. E o campo que falta
    pode estar fora da parte visível da tela.
    """

    def test_o_campo_errado_se_marca_e_diz_o_que_falta(self):
        r = self.cliente.post("/filamentos/novo", data={"nome": "PLA X", "cor": "Bordô"})
        corpo = r.get_data(as_text=True)
        self.assertEqual(r.status_code, 400)
        self.assertTrue('id="campo-cor"' in corpo, "o campo precisa ter endereço")
        self.assertTrue("com-erro" in corpo, "o campo precisa se marcar")
        self.assertTrue("cores do catálogo" in corpo, "a mensagem fica no campo")

    def test_o_topo_vira_atalho_ate_o_campo(self):
        corpo = self.cliente.post("/filamentos/novo",
                                  data={"nome": "", "cor": "Rosa"}).get_data(as_text=True)
        self.assertTrue('href="#campo-nome"' in corpo, "o topo precisa levar ao campo")
        self.assertTrue("Não salvei" in corpo)

    def test_o_topo_nao_repete_a_mensagem_do_campo(self):
        """Repetida em dois lugares, a mensagem some no meio do próprio eco."""
        corpo = self.cliente.post("/filamentos/novo",
                                  data={"nome": "", "cor": "Rosa"}).get_data(as_text=True)
        self.assertEqual(corpo.count("Dê um nome ao filamento"), 1)

    def test_o_que_foi_digitado_continua_la(self):
        """A armadilha da sprint 1: voltar com erro apagando o trabalho."""
        corpo = self.cliente.post("/filamentos/novo", data={
            "nome": "PLA Bordô", "cor": "", "gramas": "820", "preco_kg": "137,50",
        }).get_data(as_text=True)
        self.assertTrue('value="PLA Bordô"' in corpo, "o nome digitado sumiu")
        self.assertTrue("820" in corpo, "as gramas digitadas sumiram")

    def test_erro_que_nao_e_de_campo_continua_avisando_no_topo(self):
        """Nem todo erro é de um campo -- e o aviso não pode sumir por isso."""
        cli = self.d.salvar_cliente({"nome": "Ana", "canal": "Balcão"}, "samir")
        r = self.cliente.post("/pedidos/novo", data={
            "cliente_id": str(cli), "status": "invenção", "item_descricao": "Topo",
            "item_qtd": "1", "item_valor": "70"})
        corpo = r.get_data(as_text=True)
        self.assertEqual(r.status_code, 400)
        self.assertTrue("situacao desconhecida" in corpo, "o motivo tem que aparecer")
        self.assertTrue("Ir para o campo" not in corpo, "não há campo para apontar")

    def test_compra_sem_item_aponta_a_tabela(self):
        """O erro é da tabela de itens, e é ela que tem que ganhar linha."""
        r = self.cliente.post("/compras/nova", data={"data": "2026-09-01"})
        corpo = r.get_data(as_text=True)
        self.assertEqual(r.status_code, 400)
        self.assertTrue("pelo menos um item" in corpo)
        self.assertTrue('href="#campo-item_tipo"' in corpo, "o topo precisa levar à tabela")

    def test_cada_campo_que_o_banco_acusa_existe_na_tela(self):
        """A guarda que impede o apontar de virar mentira.

        `ErroDeCampo("cor", …)` não serve de nada se nenhuma tela tem um campo
        chamado `cor`: o atalho do topo levaria a lugar nenhum, e o campo
        nunca se marcaria. Renomear de um lado só fica vermelho aqui.
        """
        with open(os.path.join(RAIZ, "sistema", "dados.py"), encoding="utf-8") as fh:
            fonte = fh.read()
        acusados = set(re.findall(r"ErroDeCampo\(\s*\"(\w+)\"", fonte))
        self.assertGreaterEqual(len(acusados), 8, "poucos campos: o teste perdeu alcance")
        telas = " ".join(texto(n) for n in FORMULARIOS)
        for campo in sorted(acusados):
            self.assertTrue(f'id="campo-{campo}"' in telas,
                            f'nenhuma tela tem o campo "{campo}" que o banco acusa')

    def test_o_pedido_repetido_do_marketplace_aponta_o_numero(self):
        cli = self.d.salvar_cliente({"nome": "Ana", "canal": "Shopee"}, "samir")
        dados_ped = {"cliente_id": cli, "canal": "Shopee", "id_no_canal": "SHP-9911"}
        item = [{"descricao": "Topo", "quantidade": 1, "valor_unit": 70}]
        self.d.salvar_pedido(dados_ped, "samir", itens=item)
        with self.assertRaises(self.d.ErroDeCampo) as ctx:
            self.d.salvar_pedido(dados_ped, "samir", itens=item)
        self.assertEqual(ctx.exception.campo, "id_no_canal")
        self.assertIn("SHP-9911", str(ctx.exception))

    def test_ErroDeCampo_continua_sendo_ValueError(self):
        """Quem já tratava ValueError não pode ter parado de tratar."""
        self.assertTrue(issubclass(self.d.ErroDeCampo, ValueError))


if __name__ == "__main__":
    unittest.main()
