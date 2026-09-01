"""Linhas e colecoes do catalogo — espelha o Guia de Produtos Proprios.

Cada candidato encontrado e etiquetado automaticamente por linha/colecao,
para o sistema de busca virar uma extensao natural do catalogo que ja existe
(secao 3.5 da especificacao).
"""

from __future__ import annotations

from .brands import normalizar

# linha -> colecao -> palavras-chave (PT e EN)
TAXONOMIA: dict[str, dict[str, tuple[str, ...]]] = {
    "Infantil": {
        "Festa Infantil": (
            "festa infantil", "lembrancinha", "party favor", "kids party",
            "topo de bolo", "cake topper", "birthday", "aniversario infantil",
        ),
        "Brinquedos": (
            "brinquedo", "toy", "articulado", "flexi", "print in place",
            "fidget", "puzzle", "quebra cabeca", "dinossauro", "dinosaur",
            "unicornio", "unicorn", "dragon", "dragao", "robot", "robo",
        ),
        "Nomes e Letras": (
            "nome", "name", "letras", "letters", "alphabet", "name plate",
        ),
    },
    "Adultos": {
        "Futebol": (
            "futebol", "soccer", "football", "trofeu", "trophy", "medalha",
            "medal", "bola", "estadio", "stadium", "chuteira",
        ),
        "Churrasco": (
            "churrasco", "barbecue", "bbq", "grill", "espeto", "skewer",
            "porta tempero", "spice", "abridor", "bottle opener", "cerveja",
            "beer", "porta copos", "coaster", "tabua", "cutting board",
        ),
        "Pets": (
            "pet", "cachorro", "dog", "gato", "cat", "comedouro", "feeder",
            "coleira", "collar", "aquario", "aquarium",
        ),
        "Games e Geek": (
            "game", "gamer", "controle", "controller", "dado", "dice",
            "rpg", "boardgame", "console", "headset", "fone",
        ),
        "Automotivo": (
            "carro", "car", "automotivo", "moto", "motorcycle", "porta placa",
            "suporte veicular", "car mount",
        ),
    },
    "Social": {
        "Casamento": (
            "casamento", "wedding", "noivos", "bride", "groom", "aliança",
            "alianca", "padrinho",
        ),
        "Datas Comemorativas": (
            "natal", "christmas", "pascoa", "easter", "dia das maes",
            "mothers day", "dia dos pais", "fathers day", "namorados",
            "valentine", "halloween", "festa junina",
        ),
        "Formatura e Homenagem": (
            "formatura", "graduation", "homenagem", "placa", "plaque",
            "troféu", "award", "professor", "diploma",
        ),
        "Bebe": (
            "cha de bebe", "baby shower", "batizado", "baptism", "bebe",
            "baby", "maternidade",
        ),
    },
    "Casa e Decoracao": {
        "Organizacao": (
            "organizador", "organizer", "porta chaves", "key holder",
            "gancho", "hook", "cabide", "hanger", "gaveteiro", "drawer",
            "porta caneta", "pen holder", "cable", "cabo", "prateleira",
            "chaveiro", "keychain", "key ring",
            "shelf", "suporte de celular", "phone stand",
        ),
        "Luminarias": (
            "luminaria", "lamp", "abajur", "lampshade", "litofania",
            "lithophane", "night light", "led",
        ),
        "Vasos e Plantas": (
            "vaso", "vase", "planter", "flower pot", "suculenta", "succulent",
            "jardim", "garden",
        ),
        "Cozinha": (
            "cozinha", "kitchen", "utensilio", "utensil", "porta guardanapo",
            "napkin", "escorredor", "pote", "container", "tampa", "lid",
        ),
        "Decoracao": (
            "decoracao", "decor", "quadro", "wall art", "escultura",
            "sculpture", "porta retrato", "photo frame", "coracao", "heart",
        ),
    },
    "Corporativo": {
        "Brindes": ("brinde", "corporate gift", "logo", "empresa", "promocional"),
        "Trofeus e Placas": ("trofeu", "trophy", "award", "placa", "plaque", "sign"),
        "Escritorio": ("escritorio", "office", "desk", "mesa de trabalho", "bookmark"),
    },
}

LINHAS = tuple(TAXONOMIA)


def colecoes(linha: str) -> tuple[str, ...]:
    return tuple(TAXONOMIA.get(linha, {}))


def classificar(titulo: str = "", descricao: str = "", tags=()) -> tuple[str, str, int]:
    """Sugere (linha, colecao, pontos) para um modelo.

    O titulo pesa mais que a descricao e as tags. Sem nenhuma pista, devolve
    ("Sem linha", "", 0) — a curadoria decide na mao.
    """

    alvo_titulo = f" {normalizar(titulo)} "
    alvo_resto = f" {normalizar(' '.join([descricao, ' '.join(tags)]))} "

    melhor = ("Sem linha", "", 0)
    for linha, cols in TAXONOMIA.items():
        for colecao, chaves in cols.items():
            pontos = 0
            for chave in chaves:
                k = normalizar(chave)
                if not k:
                    continue
                if f" {k} " in alvo_titulo:
                    pontos += 3
                elif f" {k} " in alvo_resto:
                    pontos += 1
            if pontos > melhor[2]:
                melhor = (linha, colecao, pontos)
    return melhor
