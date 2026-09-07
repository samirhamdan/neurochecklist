# -*- coding: utf-8 -*-
"""Sprint C0 -- a tela Criar: o catalogo do que da para fazer.

Dois links soltos no menu ("Gerar letreiro", "Gerar logo") escondiam duas
coisas: que dentro do gerador de letreiros moram SEIS modelos diferentes, e
que a lista vai crescer para uma dezena. Uma tela so, com filtro, resolve as
duas -- e o menu volta a caber na largura da tela.

O risco de um catalogo e virar vitrine de mentira: cartao bonito para coisa
que nao existe, ou botao que leva a lugar nenhum. Os testes deste arquivo
sao quase todos sobre isso.

O que fica de fora, e por que: o filtro em si e JavaScript de quinze linhas
no navegador. O que da para provar aqui e o CONTRATO de que ele depende --
que todo cartao carrega os data-* certos, e que toda opcao de filtro
oferecida existe em pelo menos um cartao. Filtro para gaveta vazia e o outro
jeito de a tela mentir.
"""
from __future__ import annotations

import importlib
import os
import re
import tempfile
import unittest


class TesteCatalogo(unittest.TestCase):
    def setUp(self):
        from sistema import criar
        self.c = criar

    def test_todo_modelo_tem_o_minimo_para_aparecer(self):
        for m in self.c.MODELOS:
            with self.subTest(modelo=m.slug):
                self.assertTrue(m.nome and m.resumo and m.categoria and m.gerador,
                                f"{m.slug} sem nome, resumo, categoria ou gerador")
                self.assertTrue(m.resumo.endswith("."), f"{m.slug}: resumo sem ponto final")

    def test_nao_existe_slug_repetido(self):
        slugs = [m.slug for m in self.c.MODELOS]
        self.assertEqual(len(slugs), len(set(slugs)), "slug repetido no catalogo")

    def test_status_sai_da_rota_e_nao_de_um_campo_a_parte(self):
        """Dois campos para a mesma verdade viram duas verdades diferentes."""
        for m in self.c.MODELOS:
            with self.subTest(modelo=m.slug):
                esperado = self.c.NO_AR if m.rota else self.c.EM_OBRA
                self.assertEqual(m.status, esperado)

    def test_modelo_em_construcao_nao_tem_para_onde_mandar(self):
        for m in self.c.MODELOS:
            if m.status == self.c.EM_OBRA:
                self.assertEqual(m.rota, "", f"{m.slug} promete rota e nao esta pronto")

    def test_as_categorias_oferecidas_existem_em_algum_modelo(self):
        usadas = {m.categoria for m in self.c.MODELOS}
        self.assertEqual(set(self.c.categorias()), usadas)

    def test_as_cores_oferecidas_existem_em_algum_modelo(self):
        usadas = {n for m in self.c.MODELOS for n in m.cores}
        self.assertEqual(set(self.c.cores_possiveis()), usadas)

    def test_a_conta_bate_com_a_lista(self):
        conta = self.c.contagem()
        self.assertEqual(conta["total"], len(self.c.MODELOS))
        self.assertEqual(conta["no_ar"] + conta["em_obra"], conta["total"])
        self.assertEqual(conta["no_ar"],
                         sum(1 for m in self.c.MODELOS if m.status == self.c.NO_AR))

    def test_a_busca_acha_pelo_tema_e_nao_so_pelo_nome(self):
        """Ninguem procura "letreiro terror". Procura "halloween"."""
        casos = {"halloween": "letreiro-terror", "princesa": "letreiro-magia",
                 "bolo": "topo-de-bolo", "empresa": "logo-3d"}
        for termo, esperado in casos.items():
            achados = [m.slug for m in self.c.MODELOS if termo in m.procuravel]
            with self.subTest(termo=termo):
                self.assertIn(esperado, achados)


class TesteCartaoBateComOGerador(unittest.TestCase):
    """O cartao promete um modelo. O gerador tem que conhecer ele.

    `/letreiros?modelo=xyz` com um xyz que a tela nao conhece nao da erro:
    ela ignora e abre no Classico. Um cartao errado ficaria anos assim, e a
    unica pista seria a pessoa achando que clicou errado.
    """

    def setUp(self):
        from sistema import criar
        self.c = criar
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.pagina = open(os.path.join(raiz, "web", "gerador-letreiros.html"),
                           encoding="utf-8").read()

    def modelos_do_gerador(self) -> set[str]:
        bloco = re.search(r'id="prod">(.*?)</div>', self.pagina, re.S)
        self.assertIsNotNone(bloco, "os botoes de modelo sumiram do gerador")
        return set(re.findall(r'data-v="([^"]+)"', bloco.group(1)))

    def test_todo_letreiro_do_catalogo_existe_no_gerador(self):
        do_gerador = self.modelos_do_gerador()
        for m in self.c.MODELOS:
            if m.gerador == "Gerador de letreiros":
                with self.subTest(modelo=m.slug):
                    self.assertIn(m.rota.split("modelo=")[-1], do_gerador)

    def test_todo_modelo_do_gerador_esta_no_catalogo(self):
        """O caminho contrario: modelo que existe e nao aparece e venda parada."""
        no_catalogo = {m.rota.split("modelo=")[-1] for m in self.c.MODELOS
                       if m.gerador == "Gerador de letreiros"}
        self.assertEqual(self.modelos_do_gerador(), no_catalogo)

    def test_o_gerador_le_o_modelo_da_url(self):
        self.assertTrue('URLSearchParams(location.search).get("modelo")' in self.pagina,
                        "o gerador parou de ler o modelo escolhido no cartao")


class TesteTela(unittest.TestCase):
    def setUp(self):
        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-criar-")
        os.environ["MORUMBI_USUARIO"] = "samir"
        os.environ["MORUMBI_SENHA"] = "segredo"
        os.environ["MORUMBI_BIND"] = "127.0.0.1:5000"
        os.environ["MORUMBI_HTTPS"] = "0"
        from sistema import auth, criar, dados
        importlib.reload(dados)
        importlib.reload(auth)
        from sistema import app as modulo
        importlib.reload(modulo)
        # Pelo wsgi, e nao pelo criar_app(): o gerador de logo e montado la,
        # e um cartao que promete /logo/ so e verdade no app inteiro. Foi
        # este teste que mostrou a diferenca -- /logo/ dava 404 no outro.
        import wsgi
        importlib.reload(wsgi)
        wsgi.sistema.config["TESTING"] = True
        self.c = criar
        self.app = wsgi.sistema
        self.cliente = self.app.test_client()
        self.cliente.post("/entrar", data={"usuario": "samir", "senha": "segredo"})
        self.pagina = self.cliente.get("/criar").get_data(as_text=True)

    def test_a_tela_abre(self):
        self.assertEqual(self.cliente.get("/criar").status_code, 200)

    def test_sem_sessao_nao_abre(self):
        r = self.app.test_client().get("/criar")
        self.assertEqual(r.status_code, 302)
        self.assertTrue("/entrar" in r.headers["Location"], r.headers["Location"])

    def test_todo_modelo_do_catalogo_aparece_na_tela(self):
        for m in self.c.MODELOS:
            with self.subTest(modelo=m.slug):
                self.assertTrue(m.nome in self.pagina, f"{m.nome} nao apareceu na tela")

    def test_cada_cartao_leva_os_dados_que_o_filtro_usa(self):
        cartoes = re.findall(r'<article class="modelo[^"]*"\s*([^>]*)>', self.pagina)
        self.assertEqual(len(cartoes), len(self.c.MODELOS))
        for atributos in cartoes:
            for chave in ("data-nome", "data-categoria", "data-cores", "data-status"):
                self.assertTrue(f'{chave}="' in atributos, f"cartao sem {chave}")

    def test_o_cartao_de_um_modelo_de_duas_cores_nao_passa_no_filtro_de_uma(self):
        """O filtro pergunta "consigo fazer sem trocar filamento?"."""
        achado = re.search(r'data-nome="letreiro terror[^"]*"[^>]*data-cores="([^"]*)"',
                           self.pagina)
        self.assertIsNotNone(achado, "o cartao do Terror mudou de forma")
        self.assertEqual(achado.group(1).split(), ["2"])

    def test_modelo_em_construcao_nao_ganha_botao(self):
        bloco = re.search(r'<article class="modelo planejado".*?</article>',
                          self.pagina, re.S)
        self.assertIsNotNone(bloco, "nenhum cartao marcado como planejado")
        self.assertNotIn('class="botao"', bloco.group(0))

    def test_toda_rota_prometida_como_no_ar_responde(self):
        """A promessa do cartao verde, cobrada uma por uma."""
        for m in self.c.MODELOS:
            if m.status != self.c.NO_AR:
                continue
            with self.subTest(modelo=m.slug):
                r = self.cliente.get(m.rota)
                self.assertEqual(r.status_code, 200, f"{m.slug}: {m.rota} devolveu {r.status_code}")

    def test_o_menu_tem_criar_e_perdeu_os_dois_links_soltos(self):
        painel = self.cliente.get("/").get_data(as_text=True)
        self.assertTrue('href="/criar"' in painel, "Criar nao entrou no menu")
        self.assertNotIn("Gerar letreiro</a>", painel)
        self.assertNotIn("Gerar logo</a>", painel)

    def test_os_geradores_tem_volta_para_o_catalogo(self):
        for rota in ("/letreiros/", "/logo/"):
            with self.subTest(rota=rota):
                pagina = self.cliente.get(rota).get_data(as_text=True)
                self.assertTrue('href="/criar"' in pagina,
                                f"{rota} nao tem como voltar para o catalogo")

    def test_o_link_antigo_do_letreiro_continua_chegando(self):
        """Alguem tem /letreiros salvo no navegador. Nao pode virar 404."""
        r = self.cliente.get("/letreiros")
        self.assertEqual(r.status_code, 308)
        self.assertTrue(r.headers["Location"].endswith("/letreiros/"), r.headers["Location"])

    def test_a_pagina_carrega_o_nucleo_e_o_servidor_entrega(self):
        """Caminho relativo so funciona com a barra no fim -- e sem o nucleo a
        tela abre em branco, sem erro nenhum na aba de rede do usuario."""
        pagina = self.cliente.get("/letreiros/").get_data(as_text=True)
        self.assertTrue('src="nucleo/nucleo.js"' in pagina, "a pagina parou de pedir o nucleo")
        self.assertTrue('src="nucleo/letreiro.js"' in pagina, "a pagina parou de pedir a peca")
        for arquivo in ("nucleo.js", "letreiro.js"):
            with self.subTest(arquivo=arquivo):
                r = self.cliente.get(f"/letreiros/nucleo/{arquivo}")
                self.assertEqual(r.status_code, 200, f"{arquivo} nao e servido")
                self.assertIn(b"MorumbiNucleo", r.data)

    def test_o_nucleo_nao_esta_aberto_para_quem_nao_entrou(self):
        r = self.app.test_client().get("/letreiros/nucleo/nucleo.js")
        self.assertEqual(r.status_code, 302)
