# -*- coding: utf-8 -*-
"""Sprint C1 -- o nucleo saiu do HTML, e a fronteira agora tem guarda.

Ate aqui o gerador de letreiros era um arquivo de 8.600 linhas com tudo
dentro: geometria, STL, a mesa de 256 mm, a estimativa de gramas, o preco de
balcao. Util para exatamente um gerador. O plano tem uma dezena pela frente,
e cada um deles ia copiar essas contas -- ate o dia em que alguem corrigisse
uma copia so.

Agora sao tres arquivos, e a divisao e a tabela "plataforma x peca" do plano:

    nucleo.js    poligono, solido, STL, a mesa      -- serve qualquer gerador
    oficina.js   os numeros DESTA casa              -- purga, densidade, preco
    letreiro.js  o desenho do letreiro              -- a unica parte que muda

A prova de que a mudanca nao quebrou nada nao esta neste arquivo: esta em
docs/impressao-digital.txt, um sha256 por peca de uma matriz de vinte casos,
conferido em tests/test_navegador.py. Teste que so olha "malha fechada" passa
feliz com a peca virada do avesso; hash nao.

O que ESTE arquivo cobra e a fronteira -- que ela exista, que nao vaze, e que
os numeros da oficina batam com os do servidor.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NUCLEO = os.path.join(RAIZ, "web", "nucleo")
NODE = shutil.which("node") or "/opt/node22/bin/node"
TEM_NODE = os.path.exists(NODE)
SEM_NODE = "node nao instalado"


def js(codigo: str):
    """Roda um trecho de JS que imprime JSON e devolve o objeto."""
    saida = subprocess.run([NODE, "-e", codigo], capture_output=True, text=True,
                           timeout=60, cwd=NUCLEO)
    if saida.returncode:
        raise AssertionError(f"node falhou:\n{saida.stderr.strip()}")
    return json.loads(saida.stdout)


@unittest.skipUnless(TEM_NODE, SEM_NODE)
class TesteOsModulosCarregam(unittest.TestCase):
    """Fora do navegador tambem: e assim que as ferramentas os usam."""

    def test_nucleo_entrega_a_plataforma(self):
        chaves = js("console.log(JSON.stringify(Object.keys(require('./nucleo.js'))))")
        for peca in ("MESA", "stlBinario", "caixa", "uniao", "diferenca", "pathToPolys"):
            with self.subTest(peca=peca):
                self.assertIn(peca, chaves)

    def test_oficina_entrega_os_numeros_da_casa(self):
        chaves = js("console.log(JSON.stringify(Object.keys(require('./oficina.js'))))")
        for peca in ("estimar", "cabe", "purga", "precoComercial", "nomeDeArquivo",
                     "vistoriar", "ESPESSURAS"):
            with self.subTest(peca=peca):
                self.assertIn(peca, chaves)

    def test_letreiro_entrega_a_peca(self):
        chaves = js("console.log(JSON.stringify(Object.keys(require('./letreiro.js'))))")
        for peca in ("Gerador", "PRODUTOS", "alturaAuto"):
            with self.subTest(peca=peca):
                self.assertIn(peca, chaves)

    def test_os_seis_modelos_continuam_todos_la(self):
        modelos = js("console.log(JSON.stringify("
                     "Object.keys(require('./letreiro.js').PRODUTOS)))")
        self.assertEqual(sorted(modelos),
                         ["cinema", "classico", "futuro", "gamer", "magia", "terror"])


class TesteAFronteiraNaoVaza(unittest.TestCase):
    """O nucleo nao pode saber o que e um letreiro.

    Sem isto a divisao dura um sprint: alguem precisa de um ajuste rapido, poe
    um `if (produto === 'magia')` no nucleo, e o proximo gerador herda uma
    regra que nao e dele. O teste e bobo de proposito -- e uma busca por
    palavra -- e e exatamente por isso que ele nao sai do lugar.
    """

    def ler(self, nome):
        """So o CODIGO: comentario que fala de luminaria e prosa, nao acoplamento.

        A primeira versao deste teste procurava no arquivo inteiro e acusava
        o nucleo por um comentario que dizia "o rasgo do cabo da luminaria e o
        caso classico". Teste que reclama de prosa e teste que sera desligado.
        """
        with open(os.path.join(NUCLEO, nome), encoding="utf-8") as f:
            texto = f.read()
        texto = re.sub(r"/\*.*?\*/", " ", texto, flags=re.S)
        texto = re.sub(r"//[^\n]*", " ", texto)
        return texto.lower()

    def test_o_nucleo_nao_menciona_letreiro(self):
        texto = self.ler("nucleo.js")
        for palavra in ("letreiro", "produtos", "'magia'", "'gamer'", "'terror'",
                        "'cinema'", "luminaria", "opentype", "fontes"):
            with self.subTest(palavra=palavra):
                self.assertTrue(palavra not in texto,
                                f"'{palavra}' e da peca e apareceu no CODIGO do nucleo")

    def test_a_oficina_tambem_nao(self):
        """A oficina e da casa, nao do produto: purga e preco valem para todos."""
        texto = self.ler("oficina.js")
        for palavra in ("'magia'", "'gamer'", "opentype", "gerador("):
            with self.subTest(palavra=palavra):
                self.assertTrue(palavra not in texto,
                                f"'{palavra}' e da peca e apareceu na oficina")

    def test_a_peca_nao_reimplementa_o_que_e_da_plataforma(self):
        """Copiar do nucleo e pior que nao ter extraido: viram duas verdades."""
        texto = self.ler("letreiro.js")
        for copia in ("function stlbinario", "function uniao(", "function caixa(",
                      "function costurarjuntast", "function estimar("):
            with self.subTest(copia=copia):
                self.assertTrue(copia not in texto,
                                f"{copia} foi copiada do nucleo para a peca")

    def test_a_pagina_carrega_os_tres_e_nao_guarda_copia(self):
        with open(os.path.join(RAIZ, "web", "gerador-letreiros.html"), encoding="utf-8") as f:
            pagina = f.read()
        for arquivo in ("nucleo/nucleo.js", "nucleo/oficina.js", "nucleo/letreiro.js"):
            with self.subTest(arquivo=arquivo):
                self.assertTrue(f'src="{arquivo}"' in pagina, f"{arquivo} nao e carregado")
        for copia in ("function estimar(", "function volDe(", "function cabe(",
                      "function stlBinario("):
            with self.subTest(copia=copia):
                self.assertNotIn(copia, pagina, f"{copia} voltou para dentro da tela")


@unittest.skipUnless(TEM_NODE, SEM_NODE)
class TesteParametrosDeclarados(unittest.TestCase):
    """A tela e a declaracao dizem a mesma coisa -- ou uma das duas mente.

    O renderizador generico nao existe ainda, e e proposital: formulario
    generico escrito contra UM formulario acerta por acaso. O C2 traz o
    segundo. Ate la, o que segura a declaracao e este teste: opcao que existe
    na tela e nao esta declarada (ou o contrario) quebra aqui.
    """

    def setUp(self):
        self.spec = js("console.log(JSON.stringify(require('./letreiro.js').PARAMETROS))")
        with open(os.path.join(RAIZ, "web", "gerador-letreiros.html"), encoding="utf-8") as f:
            self.pagina = f.read()

    def por_campo(self, campo):
        achado = [p for p in self.spec if p["campo"] == campo]
        self.assertEqual(len(achado), 1, f"campo {campo} declarado {len(achado)} vezes")
        return achado[0]

    def opcoes_da_tela(self, caixa):
        bloco = re.search(rf'id="{caixa}">(.*?)</div>', self.pagina, re.S)
        self.assertIsNotNone(bloco, f"a caixa {caixa} sumiu da tela")
        return re.findall(r'data-v="([^"]+)"', bloco.group(1))

    def test_os_modelos_declarados_sao_os_da_tela(self):
        self.assertEqual([o["valor"] for o in self.por_campo("produto")["opcoes"]],
                         self.opcoes_da_tela("prod"))

    def test_os_tamanhos_declarados_sao_os_da_tela(self):
        self.assertEqual([str(o["valor"]) for o in self.por_campo("largura")["opcoes"]],
                         self.opcoes_da_tela("tam"))

    def test_as_espessuras_declaradas_sao_as_da_tela(self):
        bloco = re.search(r'id="esp">(.*?)</select>', self.pagina, re.S)
        da_tela = re.findall(r'value="(\d+)"', bloco.group(1))
        self.assertEqual([str(o["valor"]) for o in self.por_campo("esp")["opcoes"]], da_tela)

    def test_todo_parametro_tem_rotulo_e_padrao(self):
        for p in self.spec:
            with self.subTest(campo=p["campo"]):
                self.assertTrue(p.get("rotulo"), f"{p['campo']} sem rotulo")
                self.assertIn("padrao", p, f"{p['campo']} sem padrao")

    def test_o_padrao_declarado_e_o_padrao_da_tela(self):
        achado = re.search(r'const PADRAO = \{([^}]*)\}', self.pagina)
        self.assertIsNotNone(achado, "o estado inicial da tela mudou de forma")
        da_tela = {k: v.strip()
                   for k, v in re.findall(r'(\w+)\s*:\s*"?([^,"]+)"?', achado.group(1))}
        for p in self.spec:
            if p["campo"] == "nome":
                continue
            # json.loads devolve booleano do Python; a tela escreve o do JS.
            declarado = str(p["padrao"]).lower() if isinstance(p["padrao"], bool) \
                else str(p["padrao"])
            with self.subTest(campo=p["campo"]):
                self.assertEqual(declarado, da_tela.get(p["campo"]),
                                 f"{p['campo']}: declarado {declarado}, "
                                 f"tela {da_tela.get(p['campo'])}")


@unittest.skipUnless(TEM_NODE, SEM_NODE)
class TesteVistoria(unittest.TestCase):
    """A unica porta entre a peca e o download.

    Antes do C1 havia duas: uma avisava "saiu em 3 partes soltas, nao imprima
    assim" e a outra, que ligava o botao, olhava so se cabia na mesa. O aviso
    rolava para fora da tela e o arquivo ia para a impressora.
    """

    def vistoriar(self, **peca):
        return js("const O=require('./oficina.js');"
                  f"console.log(JSON.stringify(O.vistoriar({json.dumps(peca)})))")

    def test_peca_inteira_e_que_cabe_passa(self):
        r = self.vistoriar(bb={"w": 200, "h": 100}, corpos=1, esperado=1)
        self.assertTrue(r["ok"])
        self.assertEqual(r["motivos"], [])

    def test_peca_em_partes_soltas_e_reprovada(self):
        r = self.vistoriar(bb={"w": 200, "h": 100}, corpos=3, esperado=1)
        self.assertFalse(r["ok"])
        self.assertTrue(any("partes soltas" in m for m in r["motivos"]), r["motivos"])

    def test_peca_que_nao_cabe_na_mesa_e_reprovada(self):
        r = self.vistoriar(bb={"w": 300, "h": 300}, corpos=1, esperado=1)
        self.assertFalse(r["ok"])
        self.assertTrue(any("Não cabe na mesa" in m for m in r["motivos"]), r["motivos"])

    def test_a_diagonal_salva_a_peca_larga(self):
        """280 x 60 nao cabe reto; virada a 45 graus, cabe."""
        r = self.vistoriar(bb={"w": 280, "h": 60}, corpos=1, esperado=1)
        self.assertTrue(r["ok"])
        self.assertEqual(r["enc"]["ang"], 45)

    def test_peca_sem_esperado_nao_e_cobrada_por_partes(self):
        """A capa sai em um corpo por letra de proposito -- nao e defeito."""
        r = self.vistoriar(bb={"w": 200, "h": 100}, corpos=7)
        self.assertTrue(r["ok"], r["motivos"])


@unittest.skipUnless(TEM_NODE, SEM_NODE)
class TesteOsDoisPrecosSaoOMesmo(unittest.TestCase):
    """O preco de balcao existe em dois lugares, e nao da para evitar.

    O navegador precisa dele para mostrar o preco enquanto a pessoa digita; o
    servidor precisa dele para o pedido. Sao duas linguagens, duas maquinas.
    O que DA para evitar e que os dois discordem -- e ja discordaram: houve um
    tempo em que a mesma peca tinha um preco na tela do gerador e outro no
    cadastro de produto.
    """

    def test_a_formula_da_tela_e_a_do_servidor_dao_o_mesmo_numero(self):
        from sistema import custo
        casos = [0, 1, 9, 9.4, 30, 66.19, 83.7, 100, 250.5, 1000]
        do_js = js("const O=require('./oficina.js');"
                   f"console.log(JSON.stringify({json.dumps(casos)}"
                   ".map(g => O.precoComercial(g, 18, 0.60))))")
        for gramas, preco_js in zip(casos, do_js):
            with self.subTest(gramas=gramas):
                self.assertAlmostEqual(preco_js, custo.preco_comercial(gramas, 18, 0.60),
                                       places=6)

    def test_os_valores_padrao_sao_os_mesmos_dos_dois_lados(self):
        from sistema import dados
        padrao = js("const O=require('./oficina.js');"
                    "console.log(JSON.stringify({piso:O.PISO, grama:O.POR_GRAMA, mesa:O.MESA}))")
        self.assertAlmostEqual(padrao["piso"], dados.PADROES["piso"], places=6)
        self.assertAlmostEqual(padrao["grama"], dados.PADROES["por_grama"], places=6)

    def test_a_purga_e_a_mesma_conta_dos_dois_lados(self):
        """6 g por troca de cor: sai do custo no servidor e do preco na tela."""
        purgas = js("const O=require('./oficina.js');"
                    "console.log(JSON.stringify([1,2,3].map(n => O.purga(n))))")
        self.assertEqual(purgas, [0, 6, 12])
