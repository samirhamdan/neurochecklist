# -*- coding: utf-8 -*-
"""Sprint 6 -- o orçamento em PDF, e o link que o cliente aceita sem senha.

Três coisas precisam ser verdade, e são o que este arquivo cobra:

  * **o total do papel é o total do sistema.** O PDF é o que fica com o
    cliente. Um PDF que soma por conta própria é a maneira clássica de o
    papel dizer um número e o sistema outro -- e quem tem razão numa
    discussão dessas é sempre o papel;
  * **o link vale para UM orçamento, e vence.** Preço de três meses atrás
    não vale hoje, porque o filamento subiu;
  * **orçamento aceito não muda mais.** Editar item ou preço depois do
    aceite é mudar o que foi combinado, e o PDF que o cliente guardou
    passaria a discordar do sistema, em silêncio.

O PDF é gerado sem compressão de propósito (`pageCompression=0`): é o que
deixa este arquivo procurar o total DENTRO dos bytes. Sem isso, o teste
provaria que a conta está certa e não que o número chegou no papel.
"""
from __future__ import annotations

import importlib
import os
import re
import tempfile
import unittest


class Base(unittest.TestCase):
    def setUp(self):
        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-orc-")
        os.environ["MORUMBI_USUARIO"] = "samir"
        os.environ["MORUMBI_SENHA"] = "segredo"
        os.environ["MORUMBI_BIND"] = "127.0.0.1:5000"
        os.environ["MORUMBI_HTTPS"] = "0"
        from sistema import auth, dados, orcamento
        importlib.reload(dados)
        importlib.reload(auth)
        importlib.reload(orcamento)
        from sistema import app as modulo
        importlib.reload(modulo)
        self.d = dados
        self.orc = orcamento
        self.app = modulo.criar_app()
        self.app.config["TESTING"] = True
        self.cliente = self.app.test_client()
        self.cliente.post("/entrar", data={"usuario": "samir", "senha": "segredo"})
        self.cid = dados.salvar_cliente({"nome": "Ana Paula Ribeiro",
                                         "canal": "Instagram"}, "samir")

    def pedido(self, desconto=0, **extra):
        id_ = self.d.salvar_pedido(
            {"cliente_id": self.cid, "desconto": desconto, "prazo": "2026-10-08", **extra},
            "samir", itens=[
                {"descricao": "Topo de bolo ANA 18 cm", "cor": "Rosa", "quantidade": 1,
                 "valor_unit": 70, "gramas": 83.7, "horas": 5.77},
                {"descricao": "Chaveiro lembrança", "cor": "Rosa", "quantidade": 30,
                 "valor_unit": 15, "gramas": 270, "horas": 12}])
        return self.d.pedido(id_)

    def pdf(self, id_):
        r = self.cliente.get(f"/pedidos/{id_}/orcamento.pdf")
        self.assertEqual(r.status_code, 200)
        return r.data, r.headers

    def texto_do_pdf(self, pdf: bytes) -> str:
        """O que está ESCRITO no PDF.

        Procurar os bytes crus não serve: dentro do PDF, "ç" sai como a
        sequência de escape `\\347`, e um `assertIn` com o texto acentuado
        falha mesmo com a palavra impressa na página. Aqui as cadeias do fluxo
        de conteúdo são lidas e desescapadas.
        """
        achados = []
        for cadeia in re.findall(rb"\((?:[^()\\]|\\.)*\)", pdf, re.S):
            cru = cadeia[1:-1]
            cru = re.sub(rb"\\([0-7]{1,3})",
                         lambda m: bytes([int(m.group(1), 8)]), cru)
            cru = re.sub(rb"\\(.)", lambda m: m.group(1), cru)
            achados.append(cru.decode("latin-1"))
        return "\n".join(achados)


class TesteOTotalDoPapel(Base):
    """O PDF é o que fica com o cliente. Ele não pode somar por conta própria."""

    def test_sem_desconto_o_total_e_a_soma_dos_itens(self):
        p = self.pedido()
        conteudo = self.orc.linhas(p, self.d.empresa())
        self.assertEqual(conteudo["subtotal"], 70 + 30 * 15)
        self.assertEqual(conteudo["total"], 520.0)
        self.assertEqual(conteudo["desconto"], 0)

    def test_com_desconto_o_total_e_a_soma_MENOS_o_desconto(self):
        p = self.pedido(desconto=40)
        conteudo = self.orc.linhas(p, self.d.empresa())
        self.assertEqual(conteudo["subtotal"], 520.0)
        self.assertEqual(conteudo["desconto"], 40.0)
        self.assertEqual(conteudo["total"], 480.0)

    def test_o_total_sai_da_MESMA_funcao_que_a_tela_usa(self):
        """Regra do U2: número que a tela também mostra sai de uma função só."""
        p = self.pedido(desconto=40)
        self.assertEqual(self.orc.linhas(p, self.d.empresa())["total"],
                         self.d.total_do_pedido(p))

    def test_o_numero_CHEGA_no_papel(self):
        """A conta certa num PDF que não a imprime não serve de nada."""
        p = self.pedido(desconto=40)
        texto = self.texto_do_pdf(self.pdf(p["id"])[0])
        self.assertIn("R$ 480,00", texto, "o total não está no PDF")
        self.assertIn("R$ 520,00", texto, "o subtotal não está no PDF")
        self.assertIn("R$ 40,00", texto, "o desconto não está no PDF")

    def test_sem_desconto_o_papel_nao_mostra_linha_de_desconto(self):
        """"Desconto R$ 0,00" faz o cliente procurar o que a linha quer dizer."""
        texto = self.texto_do_pdf(self.pdf(self.pedido()["id"])[0])
        self.assertTrue("Desconto" not in texto, "linha de desconto sem desconto")
        self.assertTrue("Subtotal" not in texto, "linha de subtotal sem desconto")

    def test_o_papel_leva_a_marca_e_o_cliente(self):
        self.d.salvar_empresa({"nome": "Morumbi 3D", "documento": "12.345.678/0001-90",
                               "telefone": "(67) 99999-0000", "cor": "#0040F0",
                               "validade_dias": 7}, "samir")
        pdf, cabecalhos = self.pdf(self.pedido()["id"])
        texto = self.texto_do_pdf(pdf)
        for esperado in ("Morumbi 3D", "12.345.678/0001-90", "Ana Paula Ribeiro",
                         "Topo de bolo ANA 18 cm", "08/10/2026"):
            self.assertIn(esperado, texto, esperado)
        self.assertEqual(cabecalhos["Content-Type"], "application/pdf")
        self.assertIn("Orcamento-", cabecalhos["Content-Disposition"])

    def test_o_acento_do_portugues_sobrevive(self):
        """Helvetica cobre o português inteiro pela codificação WinAnsi.

        Se um dia entrar uma fonte sem essa codificação, "Orçamento" vira
        "Or amento" no papel do cliente -- e ninguém olha o PDF de novo.
        """
        texto = self.texto_do_pdf(self.pdf(self.pedido()["id"])[0])
        self.assertIn("Orçamento", texto)
        self.assertIn("lembrança", texto)

    def test_o_nome_do_arquivo_nao_leva_acento(self):
        """Nome com acento quebra quando o arquivo passa por WhatsApp Web."""
        cid = self.d.salvar_cliente({"nome": "José Antônio Gonçalves"}, "samir")
        p = self.d.pedido(self.d.salvar_pedido({"cliente_id": cid}, "samir", itens=[
            {"descricao": "X", "quantidade": 1, "valor_unit": 10}]))
        nome = self.orc.nome_do_arquivo(p)
        self.assertEqual(nome, f"Orcamento-{p['id']}-Jose-Antonio-Goncalves.pdf")


class TesteOLinkDoCliente(Base):
    """Vale para um orçamento só, e vence."""

    def test_o_pdf_ja_nasce_com_o_link(self):
        """PDF que manda abrir uma página inexistente é pior do que PDF nenhum."""
        p = self.pedido()
        self.assertIsNone(p["token"])
        self.pdf(p["id"])
        self.assertIsNotNone(self.d.pedido(p["id"])["token"])

    def test_um_token_abre_UM_orcamento(self):
        a, b = self.pedido(), self.pedido()
        ta = self.d.token_do_orcamento(a["id"])["token"]
        tb = self.d.token_do_orcamento(b["id"])["token"]
        self.assertNotEqual(ta, tb)
        self.assertEqual(self.d.pedido_por_token(ta)["id"], a["id"])
        self.assertEqual(self.d.pedido_por_token(tb)["id"], b["id"])

    def test_token_inventado_nao_abre_nada(self):
        self.assertIsNone(self.d.pedido_por_token("nao-existe"))
        self.assertIsNone(self.d.pedido_por_token(""))
        self.assertEqual(self.cliente.get("/orcamento/nao-existe").status_code, 404)

    def test_o_link_vence(self):
        """Preço de três meses atrás não vale hoje: o filamento subiu."""
        p = self.pedido()
        token = self.d.token_do_orcamento(p["id"], dias=7)["token"]
        self.assertIsNotNone(self.d.pedido_por_token(token))
        with self.d.conectar() as conn:
            conn.execute("UPDATE pedidos SET token_expira = '2020-01-01' WHERE id = ?",
                         (p["id"],))
            conn.commit()
        self.assertIsNone(self.d.pedido_por_token(token), "link vencido continuou abrindo")
        self.assertEqual(self.cliente.get(f"/orcamento/{token}").status_code, 404)

    def test_a_tela_do_vencido_nao_conta_QUAL_dos_dois_foi(self):
        """Para quem tenta adivinhar endereços, as duas respostas são pista."""
        corpo = self.cliente.get("/orcamento/nao-existe").get_data(as_text=True)
        self.assertIn("não está mais valendo", corpo)
        self.assertNotIn("não existe", corpo)

    def test_o_link_abre_SEM_senha(self):
        p = self.pedido()
        token = self.d.token_do_orcamento(p["id"])["token"]
        anonimo = self.app.test_client()          # sem entrar
        r = anonimo.get(f"/orcamento/{token}")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Ana Paula Ribeiro", r.get_data(as_text=True))

    def test_a_tela_do_cliente_nao_leva_para_dentro_do_sistema(self):
        p = self.pedido()
        token = self.d.token_do_orcamento(p["id"])["token"]
        corpo = self.app.test_client().get(f"/orcamento/{token}").get_data(as_text=True)
        # Marcas que só a casca do sistema tem. "Sair" solto não serve de
        # agulha: a palavra aparece num comentário do script da casca.
        for dentro in ('action="/sair"', 'id="lateral"', 'class="lateral"',
                       'href="/pedidos"', 'href="/produtos"'):
            self.assertTrue(dentro not in corpo, f"a folha do cliente mostra {dentro}")

    def test_o_pdf_exige_senha(self):
        """O papel é do cliente; a rota que o gera é da casa."""
        p = self.pedido()
        r = self.app.test_client().get(f"/pedidos/{p['id']}/orcamento.pdf")
        self.assertEqual(r.status_code, 302)


class TesteOAceite(Base):
    def aceitar(self, id_, nome="Ana Paula Ribeiro"):
        token = self.d.token_do_orcamento(id_)["token"]
        r = self.app.test_client().post(f"/orcamento/{token}/aceitar", data={"nome": nome})
        return token, r

    def test_aceitar_grava_quem_e_quando_e_poe_na_fila(self):
        p = self.pedido()
        self.aceitar(p["id"])
        depois = self.d.pedido(p["id"])
        self.assertTrue(depois["aceito_em"])
        self.assertEqual(depois["aceito_por"], "Ana Paula Ribeiro")
        self.assertEqual(depois["status"], "aprovado")
        self.assertEqual(depois["itens"][0]["status"], self.d.ETAPAS[0])

    def test_aceitar_duas_vezes_nao_muda_a_data(self):
        """O cliente recarrega a página. Isso não é um segundo acordo."""
        p = self.pedido()
        token, _ = self.aceitar(p["id"])
        primeira = self.d.pedido(p["id"])["aceito_em"]
        self.app.test_client().post(f"/orcamento/{token}/aceitar", data={"nome": "Outro"})
        depois = self.d.pedido(p["id"])
        self.assertEqual(depois["aceito_em"], primeira)
        self.assertEqual(depois["aceito_por"], "Ana Paula Ribeiro")

    def test_orcamento_aceito_nao_pode_mais_ser_editado(self):
        """A promessa do sprint. O PDF que o cliente guardou não pode passar
        a discordar do sistema em silêncio."""
        p = self.pedido()
        self.aceitar(p["id"])
        with self.assertRaises(ValueError) as ctx:
            self.d.salvar_pedido({"cliente_id": self.cid}, "samir", id_=p["id"], itens=[
                {"descricao": "Outra coisa", "quantidade": 1, "valor_unit": 5}])
        self.assertIn("já foi aceito", str(ctx.exception))
        self.assertEqual(self.d.pedido(p["id"])["valor"], 520.0, "o valor mudou mesmo assim")

    def test_a_tela_do_pedido_avisa_que_esta_travado(self):
        p = self.pedido()
        self.aceitar(p["id"])
        corpo = self.cliente.get(f"/pedidos/{p['id']}").get_data(as_text=True)
        self.assertIn("não pode mais ser editado", corpo)

    def test_o_link_de_um_aceito_continua_abrindo(self):
        """O cliente volta nele para conferir o que combinou."""
        p = self.pedido()
        token, _ = self.aceitar(p["id"])
        with self.d.conectar() as conn:
            conn.execute("UPDATE pedidos SET token_expira = '2020-01-01' WHERE id = ?",
                         (p["id"],))
            conn.commit()
        r = self.app.test_client().get(f"/orcamento/{token}")
        self.assertEqual(r.status_code, 200, "quem aceitou perdeu o comprovante")
        self.assertIn("Orçamento aceito", r.get_data(as_text=True))

    def test_renovar_o_link_de_um_aceito_nao_reabre_o_acordo(self):
        p = self.pedido()
        token, _ = self.aceitar(p["id"])
        self.assertEqual(self.d.token_do_orcamento(p["id"])["token"], token)

    def test_o_papel_de_um_aceito_diz_que_foi_aceito(self):
        p = self.pedido()
        self.aceitar(p["id"])
        texto = self.texto_do_pdf(self.pdf(p["id"])[0])
        self.assertIn("Aceito em", texto)
        self.assertTrue("vale até" not in texto, "aceito não tem mais validade")


class TesteODesconto(Base):
    def test_desconto_nao_passa_do_valor(self):
        """Pedido negativo entraria no "a receber" DIMINUINDO o total."""
        p = self.pedido(desconto=99999)
        self.assertEqual(p["desconto"], 520.0)
        self.assertEqual(self.d.total_do_pedido(p), 0.0)

    def test_desconto_negativo_vira_zero(self):
        self.assertEqual(self.pedido(desconto=-50)["desconto"], 0)

    def test_a_comissao_incide_sobre_o_que_o_cliente_paga(self):
        """Marketplace cobra sobre a venda, e a venda é depois do desconto."""
        p = self.pedido(desconto=20, comissao=10)
        self.assertEqual(p["valor"], 520.0)
        self.assertAlmostEqual(p["valor_liquido"], (520 - 20) * 0.9, places=2)

    def test_o_painel_conta_o_que_entra_no_caixa(self):
        self.pedido(desconto=120)
        self.d.mudar_situacao(1, "aprovado", "samir")
        self.assertEqual(self.d.resumo()["a_receber"], 400.0)


if __name__ == "__main__":
    unittest.main()
