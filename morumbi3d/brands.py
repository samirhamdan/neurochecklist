"""Lista de termos sensiveis (marcas, times, personagens, franquias).

A licenca do ARQUIVO nao decide a propriedade intelectual do DESIGN: um STL
"CC-BY" de um escudo de time continua sendo uso de marca registrada. Estes
termos disparam alerta automatico na curadoria (secao 3.2 e 6 da spec).

Para adicionar termos da sua operacao sem mexer no codigo, crie
``termos_sensiveis.txt`` na raiz de dados (``~/.morumbi3d``) com um termo por
linha, no formato ``categoria: termo``.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

TERMOS: dict[str, tuple[str, ...]] = {
    "time de futebol": (
        "corinthians", "palmeiras", "sao paulo fc", "spfc", "santos fc",
        "flamengo", "vasco", "fluminense", "botafogo", "gremio", "internacional",
        "cruzeiro", "atletico mineiro", "galo", "athletico paranaense", "coritiba",
        "bahia", "vitoria", "sport recife", "nautico", "ceara", "fortaleza",
        "goias", "atletico goianiense", "bragantino", "cuiaba", "juventude",
        "america mg", "chapecoense", "ponte preta", "guarani", "portuguesa",
        "real madrid", "barcelona fc", "fc barcelona", "manchester united",
        "manchester city", "liverpool fc", "chelsea fc", "arsenal fc",
        "juventus", "milan", "inter de milao", "psg", "bayern", "borussia",
        "boca juniors", "river plate", "selecao brasileira", "cbf", "fifa",
        "libertadores", "champions league", "brasileirao", "nba", "nfl",
    ),
    "personagem / franquia": (
        "disney", "mickey", "minnie", "pixar", "toy story", "frozen", "elsa",
        "moana", "stitch", "homem aranha", "spider man", "spiderman", "batman",
        "superman", "marvel", "vingadores", "avengers", "hulk", "thor",
        "capitao america", "iron man", "homem de ferro", "dc comics",
        "star wars", "baby yoda", "grogu", "mandalorian", "darth vader",
        "harry potter", "hogwarts", "senhor dos aneis", "lord of the rings",
        "pokemon", "pikachu", "mario", "super mario", "luigi", "zelda",
        "nintendo", "sonic", "minecraft", "roblox", "among us", "fortnite",
        "hello kitty", "sanrio", "peppa", "patrulha canina", "paw patrol",
        "galinha pintadinha", "turma da monica", "monica", "cebolinha",
        "bob esponja", "spongebob", "naruto", "dragon ball", "goku",
        "one piece", "demon slayer", "stranger things", "barbie", "lol surprise",
        "masha", "ursinho pooh", "winnie the pooh", "snoopy", "garfield",
        "looney tunes", "pernalonga", "scooby", "simpsons", "rick and morty",
        "game of thrones", "witcher", "halo", "call of duty", "god of war",
        "sonic the hedgehog", "gravity falls", "encanto", "cocomelon",
    ),
    "marca registrada": (
        "coca cola", "pepsi", "nike", "adidas", "puma", "apple", "iphone",
        "samsung", "playstation", "xbox", "ferrari", "lamborghini", "porsche",
        "bmw", "mercedes", "volkswagen", "harley davidson", "lego", "starbucks",
        "mcdonalds", "burger king", "netflix", "spotify", "youtube", "tiktok",
        "instagram", "whatsapp", "google", "microsoft", "bambu lab",
        "heineken", "brahma", "skol", "budweiser", "jack daniels",
    ),
    "simbolo oficial": (
        "brasao da republica", "policia militar", "policia civil", "exercito brasileiro",
        "marinha do brasil", "forca aerea", "bombeiros", "oab", "crea", "cfp",
    ),
}

_EXTRA_ENV = "termos_sensiveis.txt"


def normalizar(texto: str) -> str:
    """Minusculas, sem acento e sem pontuacao — para casar termos com robustez."""

    if not texto:
        return ""
    sem_acento = "".join(
        c
        for c in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(c)
    )
    return re.sub(r"[^a-z0-9]+", " ", sem_acento.lower()).strip()


def carregar_extras(raiz: Path | None) -> dict[str, tuple[str, ...]]:
    """Le termos adicionais do arquivo do usuario, se existir."""

    if raiz is None:
        return {}
    arquivo = Path(raiz) / _EXTRA_ENV
    if not arquivo.is_file():
        return {}
    extras: dict[str, list[str]] = {}
    for linha in arquivo.read_text(encoding="utf-8", errors="replace").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        categoria, _, termo = linha.partition(":")
        if not termo.strip():
            categoria, termo = "personalizado", categoria
        extras.setdefault(categoria.strip() or "personalizado", []).append(termo.strip())
    return {k: tuple(v) for k, v in extras.items()}


def detectar(texto: str, raiz: Path | None = None) -> list[tuple[str, str]]:
    """Devolve [(termo, categoria)] encontrados no texto."""

    alvo = f" {normalizar(texto)} "
    if alvo.strip() == "":
        return []
    achados: list[tuple[str, str]] = []
    tabelas = [TERMOS, carregar_extras(raiz)]
    vistos: set[str] = set()
    for tabela in tabelas:
        for categoria, termos in tabela.items():
            for termo in termos:
                chave = normalizar(termo)
                if not chave or chave in vistos:
                    continue
                if f" {chave} " in alvo:
                    vistos.add(chave)
                    achados.append((termo, categoria))
    return achados
