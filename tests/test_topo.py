# -*- coding: utf-8 -*-
"""Sprint C2 -- o topo de bolo, e a prova de que a plataforma do C1 servia.

O documento do Samir (docs/topo-de-bolo-requisitos.md) e a fonte. O §6 dele
concentra toda a engenharia: "conexoes entre letras, decoracao e haste devem
ser estruturalmente seguras". Um topo de bolo e uma peca fina, espetada num
bolo, carregada por criança -- letra solta cai, decoracao solta cai, e nao ha
aviso na tela que conserte isso depois.

O que este arquivo cobra e o que da para cobrar sem impressora: as regras, os
limites, a nomenclatura do §11, e a fronteira -- que a peca nova nao tenha
copiado nada da plataforma. A malha de verdade e conferida em
tests/test_navegador.py, gerando os STL num navegador e passando cada um pelo
analisador do pacote, que e o §16 traduzido.

O que NAO da para cobrar aqui esta no §6 do Samir e continua valendo:
**todo template precisa ser impresso antes de ir para venda.** Por isso todos
nascem `emTeste`.
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
    saida = subprocess.run([NODE, "-e", codigo], capture_output=True, text=True,
                           timeout=60, cwd=NUCLEO)
    if saida.returncode:
        raise AssertionError(f"node falhou:\n{saida.stderr.strip()}")
    return json.loads(saida.stdout)


class TesteASemente(unittest.TestCase):
    """A lista dos seis, que agora e SEMENTE do banco e nao mais codigo.

    No C3 os templates sairam de dentro de topo.js e viraram linhas de banco,
    editadas pela tela. O que sobrou aqui e o arquivo com que o banco NASCE --
    e a ferramenta conferir_topos.js, que roda fora do servidor, le o mesmo.

    As regras de cadastro (SKU valido, licenca para publicar, limite de nome
    maior que zero) sao cobradas onde passaram a morar: tests/test_templates.py,
    contra o banco, onde sao IMPEDIDAS e nao apenas observadas.
    """

    def setUp(self):
        with open(os.path.join(RAIZ, "web", "nucleo", "templates-iniciais.json"),
                  encoding="utf-8") as f:
            self.t = json.load(f)

    def test_a_semente_tem_os_seis_do_c2(self):
        self.assertEqual(len(self.t), 6)

    def test_todo_template_da_semente_tem_o_que_o_banco_exige(self):
        for t in self.t:
            with self.subTest(sku=t.get("sku")):
                for campo in ("sku", "modelo", "categoria", "campos", "licenca",
                              "fonte", "limite_nome"):
                    self.assertTrue(t.get(campo), f"{t.get('sku')} sem {campo}")

    def test_o_sku_segue_o_padrao_do_documento(self):
        """§7: M3D-TB-001."""
        for t in self.t:
            with self.subTest(sku=t["sku"]):
                self.assertRegex(t["sku"], r"^M3D-TB-\d{3}$")

    def test_todos_nascem_em_teste(self):
        """§6: nenhum vai para venda antes de sair da impressora."""
        for t in self.t:
            with self.subTest(sku=t["sku"]):
                self.assertEqual(t["publicado"], 0, f"{t['sku']} nasceu publicado")

    def test_template_que_pede_numero_limita_o_numero(self):
        for t in self.t:
            if "numero" in t["campos"]:
                with self.subTest(sku=t["sku"]):
                    self.assertGreater(t["limite_numero"], 0)

    def test_a_licenca_e_propria_em_todos(self):
        """§18: prioriza modelo criado pela Morumbi 3D. Nenhum destes tem
        arquivo de terceiro -- sao desenho parametrico feito aqui."""
        for t in self.t:
            with self.subTest(sku=t["sku"]):
                self.assertEqual(t["licenca"], "própria")

    def test_toda_forma_da_semente_existe_no_gerador(self):
        """Forma inventada na semente vira template que abre e ignora a escolha."""
        for t in self.t:
            with self.subTest(sku=t["sku"]):
                self.assertIn(t["forma"], ("", "coracao", "estrela"))


@unittest.skipUnless(TEM_NODE, SEM_NODE)
class TesteNomeDeArquivo(unittest.TestCase):
    """§11: M3D-TB-001_MARIA_5_18CM.3mf"""

    def nome(self, *args):
        return js("const T=require('./topo.js');"
                  f"console.log(JSON.stringify(T.nomeDeArquivo(...{json.dumps(list(args))})))")

    def test_o_exemplo_do_documento_sai_igual(self):
        self.assertEqual(self.nome("M3D-TB-001", "MARIA", 5, 180, "3mf"),
                         "M3D-TB-001_MARIA_5_18CM.3mf")

    def test_acento_e_espaco_viram_arquivo_utilizavel(self):
        self.assertEqual(self.nome("M3D-TB-002", "José Antônio", "", 120, "stl"),
                         "M3D-TB-002_JOSE-ANTONIO_12CM.stl")

    def test_sem_numero_o_campo_some(self):
        self.assertEqual(self.nome("M3D-TB-002", "ANA", "", 150, "stl"),
                         "M3D-TB-002_ANA_15CM.stl")

    def test_dois_tamanhos_diferentes_nao_viram_o_mesmo_arquivo(self):
        """O nome leva o tamanho PEDIDO, nao a largura medida.

        Com a largura medida, 180 mm e 175 mm arredondavam os dois para 17CM e
        um sobrescrevia o outro na pasta de downloads, sem aviso nenhum.
        """
        nomes = {self.nome("M3D-TB-001", "MM", 5, t, "stl") for t in (120, 150, 180, 200)}
        self.assertEqual(len(nomes), 4, f"nomes colidiram: {sorted(nomes)}")

    def test_nome_vazio_nao_produz_arquivo_sem_nome(self):
        self.assertEqual(self.nome("M3D-TB-002", "", "", 120, "stl"),
                         "M3D-TB-002_SEM-NOME_12CM.stl")


@unittest.skipUnless(TEM_NODE, SEM_NODE)
class TesteFormas(unittest.TestCase):
    """Toda forma sai no sentido anti-horario. Nao e detalhe.

    O coracao saia no sentido horario, e com preenchimento NonZero o Clipper
    trata caminho horario como FURO: unir o coracao ao nome estava SUBTRAINDO
    ele. O desenho na tela parecia certo (canvas ignora sentido), a peca saia
    em dois corpos, e doze arquivos foram parar no disco com aresta
    nao-manifold.
    """

    # A area com sinal, calculada aqui mesmo. O `area` do nucleo depende do
    # ClipperLib, que so existe no navegador; e o sentido de um poligono e
    # propriedade da lista de pontos, entao da para conferir sem biblioteca --
    # e melhor, porque o teste passa a nao depender do que esta sendo testado.
    SHOELACE = ("const sinal = p => { let s = 0;"
                " for (let i = 0; i < p.length; i++) {"
                "   const a = p[i], b = p[(i+1) % p.length];"
                "   s += a.X * b.Y - b.X * a.Y; } return s / 2; };")

    def area(self, expr):
        return js("const T=require('./topo.js'), N=require('./nucleo.js');"
                  + self.SHOELACE +
                  f"console.log(JSON.stringify(sinal(({expr})[0])))")

    def test_o_coracao_e_solido_e_nao_furo(self):
        self.assertGreater(self.area("T.coracao(40, 38)"), 0)

    def test_a_estrela_tambem(self):
        self.assertGreater(self.area("T.estrela(20)"), 0)

    def test_o_retangulo_do_nucleo_ja_era_assim(self):
        """A convencao nao e minha: e a que o nucleo ja usava."""
        self.assertGreater(self.area("N.retangulo(0, 0, 10, 10)"), 0)

    def test_toda_forma_do_topo_segue_a_convencao(self):
        formas = js("const T=require('./topo.js'), N=require('./nucleo.js');"
                    + self.SHOELACE +
                    "console.log(JSON.stringify({"
                    " coracao: sinal(T.coracao(30,28)[0]),"
                    " estrela: sinal(T.estrela(15)[0]),"
                    " barra: sinal(T.barra(0,10,0,4)[0]) }))")
        for nome, a in formas.items():
            with self.subTest(forma=nome):
                self.assertGreater(a, 0, f"{nome} saiu no sentido horario: vira furo")

    def test_o_coracao_e_largo_em_cima_e_fino_embaixo(self):
        """Coracao, e nao circulo: e essa proporcao que o cliente reconhece.

        Cobrada como largura por faixa de altura, e nao contando pontos do
        bico -- a curva tem varios pontos juntos ali, e a primeira versao
        deste teste reprovou o desenho certo por causa disso.
        """
        pts = js("const T=require('./topo.js');"
                 "console.log(JSON.stringify(T.coracao(40, 38)[0]))")
        ys = [p["Y"] for p in pts]
        alto, baixo = max(ys), min(ys)
        def largura(de, ate):
            faixa = [p["X"] for p in pts
                     if baixo + (alto-baixo)*de <= p["Y"] <= baixo + (alto-baixo)*ate]
            return max(faixa) - min(faixa) if faixa else 0
        self.assertGreater(largura(0.6, 0.9), largura(0.0, 0.2) * 3,
                           "os lobos de cima nao sao mais largos que o bico")
        self.assertLess(largura(0.0, 0.1), (max(p["X"] for p in pts) -
                                            min(p["X"] for p in pts)) * 0.25,
                        "o bico de baixo esta largo demais: virou um circulo")


class TesteAPecaNaoCopiouAPlataforma(unittest.TestCase):
    """O C1 partiu o codigo em plataforma e peca. O C2 e o teste dessa divisao.

    Se o topo de bolo tivesse reescrito a estimativa, o preco, ou o que cabe na
    mesa, a divisao nao teria servido para nada -- e no dia de corrigir um
    numero a casa passaria a ter dois.
    """

    def ler(self, nome):
        with open(os.path.join(NUCLEO, nome), encoding="utf-8") as f:
            texto = f.read()
        texto = re.sub(r"/\*.*?\*/", " ", texto, flags=re.S)
        texto = re.sub(r"//[^\n]*", " ", texto)
        return texto.lower()

    def test_o_topo_nao_reimplementa_nada_da_plataforma(self):
        texto = self.ler("topo.js")
        for copia in ("function stlbinario", "function uniao(", "function caixa(",
                      "function estimar(", "function precocomercial", "function cabe(",
                      "function linhaencaixada", "function empilhar("):
            with self.subTest(copia=copia):
                self.assertTrue(copia not in texto,
                                f"{copia} foi copiada para a peca em vez de usada")

    def test_o_nucleo_continua_sem_saber_o_que_e_um_topo(self):
        texto = self.ler("nucleo.js")
        # "topo" ficou de fora: e palavra comum em geometria ("topo da
        # camada"), e teste que reclama de prosa e teste que sera desligado.
        for palavra in ("bolo", "haste", "coracao", "template", "m3d-tb"):
            with self.subTest(palavra=palavra):
                self.assertTrue(palavra not in texto,
                                f"'{palavra}' e da peca e apareceu no nucleo")

    def test_a_oficina_tambem_nao(self):
        texto = self.ler("oficina.js")
        for palavra in ("bolo", "haste", "coracao", "m3d-tb"):
            with self.subTest(palavra=palavra):
                self.assertTrue(palavra not in texto)

    def test_a_regra_de_conexao_ficou_na_plataforma(self):
        """O proximo gerador herda o que os oito topos quebrados ensinaram."""
        oficina = self.ler("oficina.js")
        self.assertIn("function conexaofragil", oficina)
        self.assertIn("traco_minimo", oficina)

    def test_a_pagina_do_topo_carrega_a_plataforma_e_nao_uma_copia(self):
        with open(os.path.join(RAIZ, "web", "topo-de-bolo.html"), encoding="utf-8") as f:
            pagina = f.read()
        for arquivo in ("libs/libs.js", "fontes/fontes.js", "nucleo/nucleo.js",
                        "nucleo/texto.js", "nucleo/oficina.js", "nucleo/topo.js"):
            with self.subTest(arquivo=arquivo):
                self.assertTrue(f'src="{arquivo}"' in pagina, f"{arquivo} nao e carregado")

    def test_as_duas_paginas_usam_as_mesmas_fontes_e_bibliotecas(self):
        """§4: "fontes previamente testadas". Sao as do letreiro, que ja
        passaram pela mesa -- e uma copia so, num arquivo so."""
        for nome in ("gerador-letreiros.html", "topo-de-bolo.html"):
            with open(os.path.join(RAIZ, "web", nome), encoding="utf-8") as f:
                pagina = f.read()
            with self.subTest(pagina=nome):
                self.assertTrue('src="fontes/fontes.js"' in pagina)
                self.assertTrue('src="libs/libs.js"' in pagina)
                self.assertNotIn('type="text/plain"', pagina,
                                 "fonte em base64 voltou para dentro da pagina")
