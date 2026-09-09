# -*- coding: utf-8 -*-
"""Sprint C4 -- a segunda peca, e o contrato que faz a terceira custar barato.

No C1 eu declarei os parametros do letreiro como dado e NAO escrevi o
renderizador, dizendo: "formulario generico escrito contra UM formulario
acerta por acaso; o C2 traz o segundo". O C2 trouxe o topo de bolo; o C4 traz
o chaveiro. Agora sao dois, e com exigencias que brigam:

    topo de bolo   12 a 20 cm   nome + idade   quebra na CONEXAO das letras
    chaveiro        3 a  7 cm   so o nome      quebra na PAREDE do furo

Uma tela serve as duas. O que difere ficou em web/nucleo/pecas.js; o resto --
a tela, as rotas, o catalogo, a vistoria, a estimativa, o preco, o registro de
geracao -- e da plataforma.

Sobre a ESCOLHA do chaveiro: a regra do Samir e "nao invente nada que nao
tenha demanda de clientes comprovada". Dos dez geradores do plano, o chaveiro
e o unico com demanda dentro do proprio sistema -- esta nos pedidos de
exemplo, no exemplo de custo dos testes, na producao e no modulo de licencas
("Chaveiro do Corinthians"). Os outros nove esperam cliente pedindo.
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


@unittest.skipUnless(TEM_NODE, SEM_NODE)
class TesteORegistroDePecas(unittest.TestCase):
    """O contrato: o que a tela precisa saber para servir uma peca qualquer."""

    def setUp(self):
        self.tipos = js("console.log(JSON.stringify(require('./pecas.js').tipos()))")

    def campo(self, tipo, expr):
        return js("const P=require('./pecas.js');"
                  f"console.log(JSON.stringify(P.peca({json.dumps(tipo)}).{expr}))")

    def test_ha_duas_pecas(self):
        self.assertEqual(sorted(self.tipos), ["chaveiro", "topo"])

    def test_toda_peca_declara_o_que_a_tela_pede(self):
        for tipo in self.tipos:
            for campo in ("nome", "rotulo", "sku", "campos", "chamada", "passo2",
                          "tudoCerto", "aviso"):
                with self.subTest(tipo=tipo, campo=campo):
                    self.assertTrue(self.campo(tipo, campo),
                                    f"{tipo} nao declara {campo}")

    def test_toda_peca_tem_tamanhos_e_geometria(self):
        for tipo in self.tipos:
            with self.subTest(tipo=tipo):
                tamanhos = self.campo(tipo, "tamanhos")
                self.assertTrue(tamanhos, f"{tipo} sem tamanhos")
                self.assertEqual(sorted(tamanhos), tamanhos, "tamanhos fora de ordem")
                tem = js("const P=require('./pecas.js');"
                         f"console.log(JSON.stringify(typeof P.peca({json.dumps(tipo)})"
                         ".geometria.Gerador))")
                self.assertEqual(tem, "function", f"{tipo} sem Gerador")

    def test_cada_peca_tem_o_seu_prefixo_de_sku(self):
        """§11. Prefixo repetido faria M3D-XX-001 significar duas coisas."""
        prefixos = js("console.log(JSON.stringify(require('./pecas.js').prefixos()))")
        self.assertEqual(len(set(prefixos.values())), len(prefixos))
        for p in prefixos.values():
            self.assertRegex(p, r"^[A-Z]{2}$")

    def test_as_pecas_pedem_coisas_diferentes(self):
        """Se as duas pedissem o mesmo, o contrato nao teria sido testado.

        Foi para isto que eu esperei o segundo gerador: uma abstracao escrita
        contra um caso so acerta por acaso.
        """
        self.assertNotEqual(self.campo("topo", "tamanhos"),
                            self.campo("chaveiro", "tamanhos"))
        self.assertNotEqual(self.campo("topo", "campos"),
                            self.campo("chaveiro", "campos"))
        self.assertNotEqual(self.campo("topo", "chamada"),
                            self.campo("chaveiro", "chamada"))

    def test_o_chaveiro_e_menor_que_o_topo(self):
        """Nao e trivia: e o que faz o traco minimo virar o limite que mais
        aparece no chaveiro, e um extremo raro no topo."""
        self.assertLess(max(self.campo("chaveiro", "tamanhos")),
                        min(self.campo("topo", "tamanhos")))


@unittest.skipUnless(TEM_NODE, SEM_NODE)
class TesteChaveiro(unittest.TestCase):
    """A peca nova. A garantia dela e a parede em volta do furo."""

    def med(self, campo):
        return js("const C=require('./chaveiro.js');"
                  f"console.log(JSON.stringify(C.MEDIDAS.{campo}))")

    def test_a_argola_cabe_de_verdade(self):
        """4 mm passa argola de 25 mm folgada. Menos que isso nao entra."""
        self.assertGreaterEqual(self.med("furo"), 3.5)

    def test_a_parede_do_furo_e_maior_que_o_traco_minimo(self):
        """A parede e puxada todo dia por uma chave: nao pode ser o minimo."""
        minimo = js("console.log(JSON.stringify(require('./oficina.js').TRACO_MINIMO))")
        self.assertGreater(self.med("parede"), minimo)

    def test_a_aba_e_desenhada_maior_que_o_furo(self):
        """A parede e garantida pela CONSTRUCAO, e nao medida depois: a aba e
        um disco de raio (furo/2 + parede) que so acrescenta material."""
        raio = self.med("furo") / 2 + self.med("parede")
        area = js("const C=require('./chaveiro.js');"
                  "const p = C.circulo(%s)[0];"
                  "let s = 0; for (let i=0;i<p.length;i++){const a=p[i],b=p[(i+1)%%p.length];"
                  "s += a.X*b.Y - b.X*a.Y;} console.log(JSON.stringify(s/2))" % raio)
        self.assertGreater(area, 0, "o circulo saiu no sentido horario: viraria furo")

    def test_o_circulo_sai_anti_horario(self):
        """Mesma armadilha que o coracao do C2 custou doze arquivos quebrados."""
        area = js("const C=require('./chaveiro.js');"
                  "const p = C.circulo(10)[0];"
                  "let s = 0; for (let i=0;i<p.length;i++){const a=p[i],b=p[(i+1)%p.length];"
                  "s += a.X*b.Y - b.X*a.Y;} console.log(JSON.stringify(s/2))")
        self.assertGreater(area, 0)


class TesteUmaTelaParaTodasAsPecas(unittest.TestCase):
    """A tela nao pode ter voltado a saber o nome de uma peca so."""

    def ler(self, caminho):
        with open(os.path.join(RAIZ, caminho), encoding="utf-8") as f:
            texto = f.read()
        texto = re.sub(r"/\*.*?\*/", " ", texto, flags=re.S)
        texto = re.sub(r"//[^\n]*", " ", texto)
        return texto

    def test_ha_uma_pagina_de_gerador_e_nao_uma_por_peca(self):
        paginas = [n for n in os.listdir(os.path.join(RAIZ, "web"))
                   if n.endswith(".html")]
        self.assertIn("gerador.html", paginas)
        self.assertNotIn("topo-de-bolo.html", paginas,
                         "a pagina do topo voltou: o chaveiro copiaria as 400 linhas dela")

    def test_a_tela_nao_cita_uma_peca_especifica(self):
        """Texto de uma peca dentro da tela e o comeco da segunda copia."""
        texto = self.ler("web/gerador.html").lower()
        for palavra in ("topo de bolo", "haste", "argola", "morumbitopo", "morumbichaveiro"):
            with self.subTest(palavra=palavra):
                self.assertTrue(palavra not in texto,
                                f"'{palavra}' e de uma peca so e apareceu na tela")

    def test_a_tela_carrega_o_registro_e_as_duas_pecas(self):
        pagina = self.ler("web/gerador.html")
        for arquivo in ("nucleo/pecas.js", "nucleo/topo.js", "nucleo/chaveiro.js"):
            with self.subTest(arquivo=arquivo):
                self.assertTrue(f'src="{arquivo}"' in pagina, f"{arquivo} nao e carregado")

    def test_a_tela_esconde_de_verdade_o_que_nao_se_aplica(self):
        """`[hidden]` sozinho nao esconde elemento com `display` de classe.

        Sem esta regra, o chaveiro -- que pede so o nome -- mostrava o campo
        "Idade ou numero" assim mesmo. Mesma armadilha da tela Criar.
        """
        self.assertIn("[hidden]{display:none !important}", self.ler("web/gerador.html"))

    def test_a_peca_nao_reimplementa_o_que_e_da_plataforma(self):
        texto = self.ler("web/nucleo/chaveiro.js").lower()
        for copia in ("function stlbinario", "function uniao(", "function estimar(",
                      "function tracosfinos", "function conexaofragil",
                      "function nomedearquivo"):
            with self.subTest(copia=copia):
                self.assertTrue(copia not in texto,
                                f"{copia} foi copiada para a peca em vez de usada")
