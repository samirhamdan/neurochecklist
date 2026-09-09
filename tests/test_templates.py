# -*- coding: utf-8 -*-
"""Sprint C3 -- o §12: o catalogo de templates sai do codigo e vai para o painel.

Ate o C2 os seis templates eram uma constante dentro de topo.js. Acrescentar
um pedia eu mexer no codigo -- e o §12 do documento existe exatamente para
isso nao ser assim.

A regra que estrutura o sprint inteiro e o §10 cruzado com o §6:

    "separar templates em teste dos publicados"
    "todo template deve ser testado fisicamente antes de venda"

Publicar nao e um botao de arrumacao: e o Samir dizendo "ja imprimi este e ele
passou". Nenhuma linha de codigo pode dizer isso por ele, e por isso todo
template nasce em teste e so a tela publica.

O que este arquivo cobra sao as tres promessas do plano -- template em teste
nao aparece na loja em nenhuma rota, desativar nao quebra pedido antigo,
licenca em branco impede publicar -- e as bordas que apareceram construindo.
"""
from __future__ import annotations

import importlib
import json
import os
import re
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Base(unittest.TestCase):
    def setUp(self):
        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-tmpl-")
        from sistema import dados
        importlib.reload(dados)
        self.d = dados

    def campos(self, **extra):
        base = {"sku": "M3D-TB-100", "modelo": "Teste", "categoria": "Aniversário infantil",
                "resumo": "Um modelo de teste.", "fonte": "luckiest", "forma": "",
                "arco": "0", "base": "1", "limite_nome": "12", "limite_numero": "2",
                "licenca": "própria", "preco": "0", "ativo": "1"}
        base.update(extra)
        return base


class TesteASemente(Base):
    """Os seis do C2 entram como dado, uma vez so."""

    def test_o_banco_nasce_com_os_seis(self):
        self.assertEqual(len(self.d.templates(so_ativos=False)), 6)

    def test_todos_nascem_em_teste(self):
        """§6: nenhum vai para venda antes de sair da impressora."""
        for t in self.d.templates(so_ativos=False):
            with self.subTest(sku=t["sku"]):
                self.assertTrue(t["emTeste"], f"{t['sku']} nasceu publicado")

    def test_a_semente_nao_desfaz_o_que_voce_editou(self):
        """Atualizar a VPS nao pode devolver o template ao original.

        A semente entra por SKU que ainda nao existe. Sem isso, cada deploy
        apagaria o preco e o limite que o Samir tivesse ajustado.
        """
        self.d.salvar_template(self.campos(sku="M3D-TB-001", modelo="Renomeado por mim",
                                           limite_nome="8"),
                               "samir", sku_antigo="M3D-TB-001")
        importlib.reload(self.d)                      # simula outra atualizacao
        t = self.d.template("M3D-TB-001")
        self.assertEqual(t["modelo"], "Renomeado por mim")
        self.assertEqual(t["limite_nome"], 8)
        self.assertEqual(len(self.d.templates(so_ativos=False)), 6, "a semente entrou duas vezes")

    def test_a_semente_e_a_mesma_lista_que_a_ferramenta_le(self):
        """conferir_topos.js roda fora do servidor e le o mesmo arquivo."""
        with open(os.path.join(RAIZ, "web", "nucleo", "templates-iniciais.json"),
                  encoding="utf-8") as f:
            semente = json.load(f)
        self.assertEqual({t["sku"] for t in semente},
                         {t["sku"] for t in self.d.templates(so_ativos=False)})
        for t in semente:
            with self.subTest(sku=t["sku"]):
                for campo in ("modelo", "campos", "fonte", "limite_nome", "licenca"):
                    self.assertIn(campo, t)


class TesteEmTesteNaoVaiParaLoja(Base):
    """A primeira promessa do plano."""

    def test_a_loja_nao_ve_nada_enquanto_tudo_esta_em_teste(self):
        self.assertEqual(self.d.templates(so_publicados=True), [])

    def test_publicar_e_o_que_poe_na_loja(self):
        self.d.publicar_template("M3D-TB-002", True, "samir")
        self.assertEqual([t["sku"] for t in self.d.templates(so_publicados=True)],
                         ["M3D-TB-002"])

    def test_despublicar_tira_de_volta(self):
        self.d.publicar_template("M3D-TB-002", True, "samir")
        self.d.publicar_template("M3D-TB-002", False, "samir")
        self.assertEqual(self.d.templates(so_publicados=True), [])

    def test_desativado_sai_do_gerador_mesmo_publicado(self):
        """Desativar e "parei de vender isto", e vale mesmo depois de publicado."""
        self.d.publicar_template("M3D-TB-002", True, "samir")
        self.d.salvar_template(self.campos(sku="M3D-TB-002", modelo="Só o nome",
                                           ativo="0", publicado="1"),
                               "samir", sku_antigo="M3D-TB-002")
        self.assertEqual(self.d.templates(so_publicados=True), [])
        self.assertEqual(len(self.d.templates(so_ativos=False)), 6, "sumiu do painel tambem")


class TesteLicenca(Base):
    """A terceira promessa: §18 -- publicar sem licenca e o erro caro."""

    def test_nao_publica_sem_licenca(self):
        self.d.salvar_template(self.campos(licenca=""), "samir")
        with self.assertRaises(ValueError):
            self.d.publicar_template("M3D-TB-100", True, "samir")

    def test_nem_salvando_ja_publicado(self):
        with self.assertRaises(ValueError):
            self.d.salvar_template(self.campos(licenca="", publicado="1"), "samir")

    def test_mas_em_teste_sem_licenca_pode(self):
        """Rascunho seu, na sua casa. A licenca e cobrada na porta da loja."""
        sku = self.d.salvar_template(self.campos(licenca=""), "samir")
        self.assertEqual(self.d.template(sku)["licenca"], "")

    def test_com_licenca_publica(self):
        self.d.salvar_template(self.campos(), "samir")
        self.d.publicar_template("M3D-TB-100", True, "samir")
        self.assertTrue(self.d.template("M3D-TB-100")["publicado"])


class TesteOSkuEOsCampos(Base):
    def test_sku_fora_do_padrao_e_recusado(self):
        for ruim in ("", "abc", "M3D-TB-1", "TB-001", "M3D-TB-0001", "M3D-001"):
            with self.subTest(sku=ruim):
                with self.assertRaises(ValueError):
                    self.d.salvar_template(self.campos(sku=ruim), "samir")

    def test_sku_repetido_e_recusado(self):
        self.d.salvar_template(self.campos(), "samir")
        with self.assertRaises(ValueError):
            self.d.salvar_template(self.campos(modelo="Outro"), "samir")

    def test_forma_que_o_gerador_nao_conhece_e_recusada(self):
        """Cartao com forma inventada abre uma tela que ignora a escolha."""
        with self.assertRaises(ValueError):
            self.d.salvar_template(self.campos(forma="unicornio"), "samir")

    def test_limite_de_nome_zero_e_recusado(self):
        """§10 sem limite escrito nao alerta nome nenhum."""
        with self.assertRaises(ValueError):
            self.d.salvar_template(self.campos(limite_nome="0"), "samir")

    def test_o_nome_e_sempre_um_campo(self):
        sku = self.d.salvar_template(self.campos(), "samir")
        self.assertIn("nome", self.d.template(sku)["campos"])

    def test_o_numero_entra_so_quando_marcado(self):
        self.d.salvar_template(self.campos(), "samir")
        self.assertNotIn("numero", self.d.template("M3D-TB-100")["campos"])
        self.d.salvar_template(self.campos(campo_numero="1"), "samir",
                               sku_antigo="M3D-TB-100")
        self.assertIn("numero", self.d.template("M3D-TB-100")["campos"])


class TesteGeracoes(Base):
    """§12: acompanhar geracoes -- e a segunda promessa do plano."""

    def gerar(self, sku="M3D-TB-001", nome="MARIA"):
        return self.d.registrar_geracao(
            {"sku": sku, "nome": nome, "numero": "5", "tamanho": 180,
             "arquivo": f"{sku}_{nome}_5_18CM.stl", "gramas": 32, "preco": 40}, "samir")

    def test_a_geracao_guarda_a_configuracao(self):
        self.gerar()
        g = self.d.geracoes()[0]
        self.assertEqual((g["sku"], g["nome"], g["numero"], g["tamanho"]),
                         ("M3D-TB-001", "MARIA", "5", 180))
        self.assertEqual(g["modelo"], "Nome + idade", "nao guardou de qual modelo veio")

    def test_desativar_o_template_nao_apaga_a_geracao(self):
        self.gerar()
        self.d.salvar_template(self.campos(sku="M3D-TB-001", modelo="Nome + idade",
                                           ativo="0"),
                               "samir", sku_antigo="M3D-TB-001")
        self.assertEqual(len(self.d.geracoes(sku="M3D-TB-001")), 1)

    def test_apagar_o_template_tambem_nao(self):
        """O que foi entregue a um cliente nao some porque o modelo saiu de linha."""
        self.gerar()
        self.d.apagar_template("M3D-TB-001")
        self.assertIsNone(self.d.template("M3D-TB-001"))
        g = self.d.geracoes(sku="M3D-TB-001")
        self.assertEqual(len(g), 1)
        self.assertEqual(g[0]["modelo"], "Nome + idade",
                         "sem o template, o registro perdeu de que modelo era")

    def test_renomear_o_sku_leva_as_geracoes_junto(self):
        self.gerar()
        self.d.salvar_template(self.campos(sku="M3D-TB-900", modelo="Nome + idade"),
                               "samir", sku_antigo="M3D-TB-001")
        self.assertEqual(len(self.d.geracoes(sku="M3D-TB-900")), 1)
        self.assertEqual(len(self.d.geracoes(sku="M3D-TB-001")), 0)

    def test_a_conta_de_geracoes_aparece_no_template(self):
        self.gerar(); self.gerar(nome="ANA")
        self.assertEqual(self.d.template("M3D-TB-001")["geracoes"], 2)

    def test_geracao_sem_nome_e_recusada(self):
        with self.assertRaises(ValueError):
            self.d.registrar_geracao({"sku": "M3D-TB-001", "nome": "", "tamanho": 180},
                                     "samir")


class TesteAsRotas(unittest.TestCase):
    """A promessa "em nenhuma rota" cobrada nas rotas."""

    def setUp(self):
        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-tr-")
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
        self.anonimo = self.app.test_client()

    def test_as_telas_abrem(self):
        for rota in ("/templates", "/templates/novo", "/templates/M3D-TB-001"):
            with self.subTest(rota=rota):
                self.assertEqual(self.cliente.get(rota).status_code, 200)

    def test_sem_sessao_o_painel_nao_abre(self):
        for rota in ("/templates", "/templates/M3D-TB-001"):
            with self.subTest(rota=rota):
                r = self.anonimo.get(rota)
                self.assertEqual(r.status_code, 302)
                self.assertTrue("/entrar" in r.headers["Location"])

    def test_a_vitrine_nao_ve_o_que_esta_em_teste(self):
        """A porta que a sprint 8 vai usar, cobrada desde ja.

        Sem sessao, a rota entrega so o publicado. Este e o teste que a
        promessa "nao aparece na loja, em NENHUMA rota" pede -- e o dia em
        que existir vitrine ela ja nasce obedecendo.
        """
        r = self.anonimo.get("/topo/templates")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["templates"], [])
        self.assertFalse(r.get_json()["painel"])

    def test_publicado_aparece_para_quem_nao_entrou(self):
        self.d.publicar_template("M3D-TB-003", True, "samir")
        dados_ = self.anonimo.get("/topo/templates").get_json()
        self.assertEqual([t["sku"] for t in dados_["templates"]], ["M3D-TB-003"])

    def test_de_dentro_do_painel_o_gerador_ve_tudo(self):
        """Voce precisa gerar para TESTAR antes de publicar. Senao a regra do
        §6 vira impossivel: so publica quem imprimiu, e so imprime quem gera."""
        d = self.cliente.get("/topo/templates").get_json()
        self.assertEqual(len(d["templates"]), 6)
        self.assertTrue(d["painel"])
        self.assertTrue(all(t["emTeste"] for t in d["templates"]))

    def test_publicar_pela_tela(self):
        r = self.cliente.post("/templates/M3D-TB-002/publicar", data={"publicar": "1"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(self.d.template("M3D-TB-002")["publicado"])

    def test_publicar_sem_licenca_devolve_erro_na_tela_e_nao_500(self):
        self.d.salvar_template({"sku": "M3D-TB-200", "modelo": "Sem licenca",
                                "licenca": "", "limite_nome": "10"}, "samir")
        r = self.cliente.post("/templates/M3D-TB-200/publicar", data={"publicar": "1"})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(self.d.template("M3D-TB-200")["publicado"])

    def test_cadastrar_pelo_formulario(self):
        r = self.cliente.post("/templates/novo", data={
            "sku": "m3d-tb-300", "modelo": "Nome + lua", "categoria": "Chá revelação",
            "licenca": "própria", "fonte": "futuro", "forma": "estrela",
            "limite_nome": "10", "limite_numero": "2", "base": "1", "ativo": "1"})
        self.assertEqual(r.status_code, 302)
        t = self.d.template("M3D-TB-300")           # o SKU sobe para maiuscula
        self.assertIsNotNone(t, "nao cadastrou")
        self.assertEqual(t["fonte"], "futuro")
        self.assertTrue(t["emTeste"], "cadastrou ja publicado")

    def test_formulario_invalido_devolve_400_e_nao_cadastra(self):
        antes = len(self.d.templates(so_ativos=False))
        r = self.cliente.post("/templates/novo", data={"sku": "errado", "modelo": "X"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(len(self.d.templates(so_ativos=False)), antes)

    def test_template_que_nao_existe_da_404(self):
        for rota in ("/templates/M3D-TB-999", "/templates/M3D-TB-999/publicar",
                     "/templates/M3D-TB-999/apagar"):
            with self.subTest(rota=rota):
                metodo = self.cliente.get if rota.count("/") == 2 else self.cliente.post
                self.assertEqual(metodo(rota).status_code, 404)

    def test_registrar_geracao_pela_api(self):
        r = self.cliente.post("/topo/geracao", json={
            "sku": "M3D-TB-001", "nome": "BEATRIZ", "numero": "7", "tamanho": 180,
            "arquivo": "M3D-TB-001_BEATRIZ_7_18CM.stl", "gramas": 33, "preco": 40})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.d.template("M3D-TB-001")["geracoes"], 1)

    def test_a_api_de_geracao_exige_sessao(self):
        """Sem isto, qualquer um enche a tabela de geracoes da rua."""
        r = self.anonimo.post("/topo/geracao", json={"sku": "M3D-TB-001", "nome": "X",
                                                    "tamanho": 180})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.d.geracoes(), [])

    def test_geracao_sem_nome_devolve_400(self):
        r = self.cliente.post("/topo/geracao", json={"sku": "M3D-TB-001", "tamanho": 180})
        self.assertEqual(r.status_code, 400)

    def test_o_menu_leva_para_templates(self):
        painel = self.cliente.get("/").get_data(as_text=True)
        self.assertTrue('href="/templates"' in painel, "Templates nao entrou no menu")

    def test_a_tela_oferece_so_fontes_que_o_gerador_tem(self):
        """Fonte na tela que o gerador nao carrega vira template que nao desenha."""
        from sistema.app import _fontes_do_gerador
        pagina = self.cliente.get("/templates/novo").get_data(as_text=True)
        for f in _fontes_do_gerador():
            with self.subTest(fonte=f):
                self.assertTrue(f'value="{f}"' in pagina, f"{f} nao esta na tela")


class TesteOCodigoNaoGuardaMaisTemplates(unittest.TestCase):
    """A mudanca de fundo do C3, cobrada onde ela pode voltar atras."""

    def test_topo_js_nao_tem_mais_catalogo(self):
        with open(os.path.join(RAIZ, "web", "nucleo", "topo.js"), encoding="utf-8") as f:
            codigo = f.read()
        # Tira comentario de bloco TAMBEM: o §11 esta documentado ali com um
        # SKU de exemplo, e isso e prosa, nao catalogo. E `assertTrue` com
        # mensagem curta, nunca `assertNotIn` -- num arquivo de 400 linhas o
        # assertNotIn despeja o arquivo inteiro no relatorio de falha.
        codigo = re.sub(r"/\*.*?\*/", " ", codigo, flags=re.S)
        codigo = re.sub(r"//[^\n]*", " ", codigo)
        self.assertTrue("M3D-TB-" not in codigo,
                        "voltou a haver template escrito dentro do codigo")
        self.assertTrue("const TEMPLATES" not in codigo,
                        "a constante de templates voltou para o codigo")

    def test_a_pagina_busca_os_templates_do_servidor(self):
        with open(os.path.join(RAIZ, "web", "topo-de-bolo.html"), encoding="utf-8") as f:
            pagina = f.read()
        self.assertIn('fetch("templates")', pagina)
        self.assertIn('fetch("geracao"', pagina)
