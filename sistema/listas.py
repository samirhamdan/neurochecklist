# -*- coding: utf-8 -*-
"""Ordenar e buscar nas listas que crescem.

Tres telas crescem sem parar: pedidos, produtos e geracoes. Numa lista de
oito linhas a ordem do banco basta; em oitenta, a pergunta muda toda semana
-- "qual pedido esta mais atrasado" hoje, "qual produto paga melhor a hora"
depois -- e rolar procurando e o que faz o sistema deixar de ser usado.

Duas decisoes que valem a pena explicar:

**Ordena em Python, e nao em SQL.** Sao algumas centenas de linhas, ja lidas.
Montar `ORDER BY` com texto que veio da URL e o jeito classico de abrir uma
injecao, e a lista de campos permitidos aqui embaixo e a mesma coisa sem o
risco: chave que nao esta nela simplesmente nao ordena.

**A lista de ordens e DADO, num lugar so.** A tela larga ordena clicando no
cabecalho; o telefone, onde o cabecalho nao existe (a linha virou cartao),
ordena por uma caixa de selecao. Sao duas interfaces para a mesma coisa, e
escrever a lista duas vezes garantiria que uma delas ficaria para tras. As
duas saem daqui, e ha teste que compara as duas.
"""
from __future__ import annotations

import unicodedata


def sem_acento(texto: str) -> str:
    """"Girassol" acha "girassol"; "acucar" acha "açúcar".

    Quem digita no telefone, com uma mao, no meio de uma festa, nao vai por
    o acento -- e a busca que exige acento e a busca que nao encontra.
    """
    cru = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in cru if not unicodedata.combining(c)).casefold()


def filtrar(itens: list[dict], termo: str, campos: tuple) -> list[dict]:
    """Fica quem tem o termo em algum dos campos. Termo vazio nao filtra."""
    termo = sem_acento(termo or "").strip()
    if not termo:
        return itens
    def combina(item):
        for campo in campos:
            valor = campo(item) if callable(campo) else item.get(campo)
            if valor is not None and termo in sem_acento(valor):
                return True
        return False
    return [i for i in itens if combina(i)]


def _valor(item: dict, campo):
    return campo(item) if callable(campo) else item.get(campo)


def ordenar(itens: list[dict], chave: str, invertido: bool, ordens: tuple) -> list[dict]:
    """Ordena por uma das ordens PERMITIDAS. Chave desconhecida nao ordena."""
    campo = dict((c, f) for c, _, f in ordens).get(chave)
    if campo is None:
        return itens

    # Vazio vai para o fim NOS DOIS SENTIDOS. "Sem prazo" nao e o prazo mais
    # urgente nem o menos: ele nao tem prazo, e no meio da lista ele esconde
    # os que tem. Por isso sao duas listas, e nao uma chave com truque --
    # `reverse=True` viraria a ordem dos vazios junto.
    cheios, vazios = [], []
    for item in itens:
        (vazios if _valor(item, campo) in (None, "") else cheios).append(item)

    def peso(item):
        v = _valor(item, campo)
        return (0, float(v), "") if isinstance(v, (int, float)) else (1, 0.0, sem_acento(v))

    return sorted(cheios, key=peso, reverse=invertido) + vazios


def pedido_da_url(args, ordens: tuple, padrao: str = "") -> tuple[str, bool]:
    """(chave, invertido) a partir de ?ordem= e ?dir=. So aceita o que existe."""
    chaves = {c for c, _, _ in ordens}
    chave = args.get("ordem", padrao)
    return (chave if chave in chaves else padrao, args.get("dir") == "desc")


# ------------------------------------------------------------ o que cada tela ordena
#
# (chave na URL, rotulo na tela, de onde sai o valor). O rotulo e o mesmo do
# cabecalho da coluna -- ha teste que compara os dois na pagina renderizada.

ORDENS_PEDIDOS = (
    ("cliente", "Cliente", "cliente"),
    ("canal", "Canal", "canal"),
    ("situacao", "Situação", "status"),
    ("prazo", "Prazo", "prazo"),
    ("itens", "Itens", "itens"),
    # Ordena pelo que o cliente PAGA, que e o que a coluna mostra -- ordenar
    # pelo preco de tabela poria um pedido de R$ 800 com R$ 300 de desconto na
    # frente de um de R$ 700 inteiro.
    ("valor", "Valor", lambda p: (p.get("valor") or 0) - (p.get("desconto") or 0)),
    ("liquido", "Líquido", lambda p: p.get("valor_liquido")),
)
BUSCA_PEDIDOS = ("cliente", "canal", "id_no_canal")

ORDENS_PRODUTOS = (
    ("nome", "Produto", "nome"),
    ("filamento", "Filamento", "filamento_nome"),
    ("gramas", "Peso", "gramas"),
    ("horas", "Tempo", "horas"),
    ("custo", "Custo", lambda p: p["conta"].custo if p["conta"].completo else None),
    ("preco", "Preço", lambda p: p["conta"].preco),
    ("margem", "Margem", lambda p: p["conta"].margem_pct if p["conta"].completo else None),
    ("hora", "R$/h", lambda p: p["conta"].por_hora if p["conta"].completo else None),
)
BUSCA_PRODUTOS = ("nome", "sku", "filamento_nome", "categoria")

ORDENS_GERACOES = (
    ("quando", "Quando", "criado_em"),
    ("modelo", "Modelo", "modelo"),
    ("nome", "Nome", "nome"),
    ("tamanho", "Tamanho", "tamanho"),
    ("gramas", "Peso", "gramas"),
    ("preco", "Preço", "preco"),
)
BUSCA_GERACOES = ("nome", "modelo", "sku", "arquivo")
