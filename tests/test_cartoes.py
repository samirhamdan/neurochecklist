# -*- coding: utf-8 -*-
"""Sprint U3 -- a linha vira cartao, e nada some no caminho.

Seis telas sao tabelas de cinco a sete colunas. No computador funcionam; no
telefone a coluna que importa e sempre a que fica de fora. Medido a 420 px
antes deste sprint: **75 alvos de toque abaixo de 44 px** e tabela pedindo
mais largura do que a caixa tem em oito das nove telas.

O cartao usa o MESMO DOM da tabela -- nao ha uma marcacao para tela larga e
outra para telefone. Cada celula carrega o rotulo da sua coluna em
`data-rotulo`, e e por isso que este arquivo existe: sem ele o rotulo vira a
segunda copia do cabecalho e envelhece sozinho. O primeiro teste abre TODA
tela com tabela e confere celula por celula.

A largura e o alvo de toque sao cobrados em tests/test_navegador.py, num
navegador de verdade -- nenhum dos dois se mede lendo HTML.
"""
from __future__ import annotations

import importlib
import os
import re
import tempfile
import unittest
from html.parser import HTMLParser


class Tabelas(HTMLParser):
    """Le as tabelas de uma pagina: rotulos do cabecalho e das celulas.

    BeautifulSoup nao entra no projeto por causa de um teste -- o sistema
    inteiro roda sem dependencia de front-end e sem biblioteca de HTML.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tabelas: list[dict] = []
        self._t = None
        self._onde = ""
        self._celula = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            self._t = {"classe": a.get("class", ""), "cabecas": [], "linhas": []}
            self.tabelas.append(self._t)
        elif tag in ("thead", "tbody", "tfoot"):
            self._onde = tag
        elif tag == "tr" and self._onde == "tbody" and self._t is not None:
            self._t["linhas"].append([])
        elif tag == "th" and self._t is not None:
            self._celula = {"texto": "", "rotulo": None}
            self._t["cabecas"].append(self._celula)
        elif tag == "td" and self._onde == "tbody" and self._t is not None and self._t["linhas"]:
            self._celula = {"texto": "", "rotulo": a.get("data-rotulo"),
                            "classe": a.get("class", "")}
            self._t["linhas"][-1].append(self._celula)

    def handle_endtag(self, tag):
        if tag in ("th", "td"):
            self._celula = None
        elif tag == "table":
            self._t = None

    def handle_data(self, dado):
        if self._celula is not None:
            self._celula["texto"] += dado


def tabelas_de(pagina: str) -> list[dict]:
    leitor = Tabelas()
    leitor.feed(pagina)
    for t in leitor.tabelas:
        for c in t["cabecas"]:
            # A seta de ordenacao e enfeite (aria-hidden) e nao faz parte do
            # nome da coluna.
            c["texto"] = re.sub(r"\s+", " ", c["texto"]).strip().rstrip("↑↓ ")
    return [t for t in leitor.tabelas if "tabela" in t["classe"] or "lista" in t["classe"]]


class Base(unittest.TestCase):
    def setUp(self):
        os.environ["MORUMBI_DADOS"] = tempfile.mkdtemp(prefix="morumbi-cartoes-")
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
        self.semear()

    def pagina(self, rota="/"):
        return self.cliente.get(rota).get_data(as_text=True)

    def semear(self):
        d = self.d
        self.rosa = d.salvar_filamento({"nome": "PLA Rosa", "cor": "Rosa", "gramas": 1400,
                                        "minimo": 300, "preco_kg": 118}, "samir")
        self.preto = d.salvar_filamento({"nome": "PLA Preto", "cor": "Preto", "gramas": 240,
                                         "minimo": 300, "preco_kg": 95}, "samir")
        d.salvar_insumo({"nome": "Ímã 8 mm", "quantidade": 140, "valor_unit": 0.35}, "samir")
        d.salvar_produto({"nome": "Chaveiro de nome", "sku": "M3D-CH-001", "gramas": 9,
                          "horas": 0.4, "minutos": 5, "filamento_id": self.rosa}, "samir")
        d.salvar_produto({"nome": "Topo de bolo 18 cm", "sku": "M3D-TB-001", "gramas": 83.7,
                          "horas": 5.77, "minutos": 30, "filamento_id": self.rosa}, "samir")
        d.salvar_produto({"nome": "Letreiro Clássico", "sku": "M3D-LT-001", "gramas": 152,
                          "horas": 9.2, "minutos": 25, "filamento_id": self.preto}, "samir")
        d.salvar_compra({"data": "2026-09-01", "fornecedor": "3D Fila MS", "nota": "NF 4471"},
                        "samir", itens=[{"tipo": "filamento", "alvo_id": self.rosa,
                                         "quantidade": 3000, "valor": 354}])
        for nome, canal, valor in (("Ana Paula Ribeiro", "Instagram", 70),
                                   ("Buffet Estrela", "Morumbi Festas", 690),
                                   ("Escola Girassol", "WhatsApp", 720)):
            cli = d.salvar_cliente({"nome": nome, "canal": canal}, "samir")
            d.salvar_pedido({"cliente_id": cli, "canal": canal, "status": "aprovado"}, "samir",
                            itens=[{"descricao": "Peça", "cor": "Rosa", "quantidade": 1,
                                    "valor_unit": valor, "gramas": 83.7, "horas": 5.77}])
        d.registrar_geracao({"sku": "M3D-TB-001", "nome": "ANA", "tamanho": 180,
                             "gramas": 83.7, "preco": 70,
                             "arquivo": "M3D-TB-001-ANA-18CM.stl"}, "samir")


TELAS = ("/", "/producao", "/pedidos", "/clientes", "/produtos", "/compras",
         "/filamentos", "/insumos", "/templates")


class TesteORotuloSaiDoCabecalho(Base):
    """A guarda que impede o rotulo de envelhecer.

    O cartao mostra "Canal   Instagram" porque cada celula carrega o nome da
    coluna. Escrito a mao, esse nome e a SEGUNDA copia do cabecalho -- e a que
    ninguem lembra de mudar. Aqui os dois sao comparados em toda tabela de
    toda tela.
    """

    def test_toda_celula_tem_o_rotulo_da_sua_coluna(self):
        vistas = 0
        for rota in TELAS:
            for i, t in enumerate(tabelas_de(self.pagina(rota))):
                if not t["linhas"]:
                    continue
                cabecas = [c["texto"] for c in t["cabecas"]]
                for linha in t["linhas"]:
                    self.assertEqual(
                        len(linha), len(cabecas),
                        f"{rota} tabela {i}: {len(linha)} células para {len(cabecas)} colunas")
                    for celula, cabeca in zip(linha, cabecas):
                        vistas += 1
                        papel = celula["classe"]
                        if not cabeca or "acao" in papel or "marca" in papel:
                            continue   # botao e caixa de selecao nao tem rotulo
                        self.assertEqual(
                            celula["rotulo"], cabeca,
                            f"{rota} tabela {i}: célula diz {celula['rotulo']!r}, "
                            f"coluna diz {cabeca!r}")
        self.assertGreater(vistas, 60, "poucas células conferidas: o teste perdeu o alcance")

    def test_toda_tabela_tem_uma_chave(self):
        """Sem `.chave` o cartao abre com um par rotulo/valor qualquer."""
        for rota in TELAS:
            for i, t in enumerate(tabelas_de(self.pagina(rota))):
                if not t["linhas"]:
                    continue
                for linha in t["linhas"]:
                    papeis = " ".join(c["classe"] for c in linha)
                    self.assertIn("chave", papeis, f"{rota} tabela {i} sem célula-chave")

    def test_a_acao_nao_e_um_link_solto_no_meio_do_cartao(self):
        """Abrir/editar vira botao no pe do cartao -- por isso a classe."""
        for rota in ("/pedidos", "/produtos", "/clientes", "/compras",
                     "/filamentos", "/insumos", "/templates"):
            pagina = self.pagina(rota)
            self.assertTrue('class="num acao"' in pagina, f"{rota} sem célula de ação")


class TesteOrdenarNaTela(Base):
    def valores(self, rota, rotulo):
        """Os valores de uma coluna, na ordem em que a tela mostra."""
        t = tabelas_de(self.pagina(rota))[0]
        return [re.sub(r"\s+", " ", c["texto"]).strip()
                for linha in t["linhas"] for c in linha if c["rotulo"] == rotulo]

    def test_clicar_na_coluna_muda_a_ordem(self):
        maior = self.valores("/pedidos?ordem=valor&dir=desc", "Valor")
        menor = self.valores("/pedidos?ordem=valor&dir=asc", "Valor")
        self.assertEqual(maior, list(reversed(menor)))
        self.assertEqual(maior[0], "R$ 720,00")

    def test_ordem_da_url_que_nao_existe_nao_derruba_a_tela(self):
        r = self.cliente.get("/produtos?ordem=;DROP TABLE produtos&dir=desc")
        self.assertEqual(r.status_code, 200)

    def test_ordenar_por_retorno_por_hora(self):
        """O numero do U2, agora ordenavel: qual peca paga melhor a hora."""
        valores = self.valores("/produtos?ordem=hora&dir=desc", "R$/h")
        self.assertEqual(valores[0], "R$ 51,23")

    def test_os_dois_jeitos_de_ordenar_oferecem_as_mesmas_ordens(self):
        """Cabecalho na tela larga, caixa de selecao no telefone.

        Escritos separados, um deles ficaria para tras na primeira coluna
        nova. Os dois saem de `listas.ORDENS_*`.
        """
        from sistema import listas
        for rota, ordens in (("/pedidos", listas.ORDENS_PEDIDOS),
                             ("/produtos", listas.ORDENS_PRODUTOS),
                             ("/templates", listas.ORDENS_GERACOES)):
            pagina = self.pagina(rota)
            no_seletor = re.findall(r'<option value="(\w+)"', pagina)
            nos_cabecalhos = re.findall(r'href="[^"]*ordem=(\w+)', pagina)
            for chave, _, _ in ordens:
                self.assertIn(chave, no_seletor, f"{rota}: {chave} fora da caixa de seleção")
                self.assertIn(chave, nos_cabecalhos, f"{rota}: {chave} fora do cabeçalho")

    def test_o_rotulo_da_ordem_e_o_do_cabecalho(self):
        from sistema import listas
        for rota, ordens in (("/pedidos", listas.ORDENS_PEDIDOS),
                             ("/produtos", listas.ORDENS_PRODUTOS)):
            cabecas = [c["texto"] for c in tabelas_de(self.pagina(rota))[0]["cabecas"]]
            for chave, rotulo, _ in ordens:
                if rota == "/pedidos" and chave == "prazo":
                    continue     # muda de nome na aba de entregues
                self.assertIn(rotulo, cabecas, f"{rota}: {rotulo} não é o nome da coluna")


class TesteBuscarNaTela(Base):
    def linhas(self, rota):
        tabelas = tabelas_de(self.pagina(rota))
        return tabelas[0]["linhas"] if tabelas else []

    def test_a_busca_estreita_a_lista(self):
        self.assertEqual(len(self.linhas("/produtos")), 3)
        self.assertEqual(len(self.linhas("/produtos?q=letreiro")), 1)

    def test_a_busca_ignora_acento(self):
        self.assertEqual(len(self.linhas("/pedidos?q=girassol")), 1)

    def test_o_rodape_conta_o_que_esta_na_tela(self):
        """A promessa do sprint: filtrar nao pode esconder linha sem dizer."""
        for rota in ("/produtos", "/produtos?q=letreiro", "/produtos?q=topo",
                     "/pedidos", "/pedidos?q=ana"):
            pagina = self.pagina(rota)
            mostradas = len(tabelas_de(pagina)[0]["linhas"])
            dito = re.search(r"(\d+) (?:produto|pedido)\(s\)", pagina)
            self.assertIsNotNone(dito, f"{rota} sem contagem no rodapé")
            self.assertEqual(int(dito.group(1)), mostradas, rota)

    def test_busca_sem_resultado_explica_e_oferece_saida(self):
        pagina = self.pagina("/produtos?q=zzzz")
        self.assertTrue("Nada com" in pagina, "a tela precisa dizer que não achou")
        self.assertTrue("Limpar a busca" in pagina, "e como voltar")

    def test_buscar_nao_troca_de_aba(self):
        """Sem o campo escondido, buscar em Entregues voltava para Abertos."""
        pagina = self.pagina("/pedidos?ver=entregues")
        self.assertTrue('name="ver" value="entregues"' in pagina)

    def test_ordenar_guarda_a_busca(self):
        """Cada clique no cabecalho nao pode jogar fora o filtro."""
        pagina = self.pagina("/produtos?q=topo")
        self.assertTrue("q=topo" in pagina, "os links de ordem perderam a busca")


if __name__ == "__main__":
    unittest.main()
