"""Motor de traducao PT<->EN para busca.

A maioria dos modelos bons esta catalogada em ingles. Este modulo expande um
termo em portugues para as variantes que realmente aparecem nos repositorios
("churrasco" -> "barbecue", "bbq", "grill"), sem depender de servico externo:
e um dicionario do nicho, editavel, mais uma expansao por palavra.

Para acrescentar termos sem mexer no codigo, crie ``dicionario.txt`` na raiz
de dados (``~/.morumbi3d``) com linhas ``termo pt = termo en, outro termo``.
"""

from __future__ import annotations

from pathlib import Path

from .brands import normalizar

# Dicionario do nicho: termo em portugues -> variantes de busca.
DICIONARIO: dict[str, tuple[str, ...]] = {
    # churrasco / cozinha
    "churrasco": ("barbecue", "bbq", "grill", "grilling"),
    "churrasqueira": ("barbecue", "bbq grill", "grill accessories"),
    "espeto": ("skewer", "bbq skewer"),
    "tabua de corte": ("cutting board", "chopping board"),
    "porta tempero": ("spice rack", "spice holder", "seasoning holder"),
    "abridor de garrafa": ("bottle opener",),
    "porta copos": ("coaster", "cup holder", "drink coaster"),
    "cerveja": ("beer", "beer holder"),
    "cozinha": ("kitchen", "kitchen gadget"),
    "utensilio": ("utensil", "kitchen tool"),
    "caneca": ("mug", "cup"),
    "garrafa": ("bottle",),
    "faca": ("knife", "knife holder"),
    # casa / organizacao
    "porta chaves": ("key holder", "key hanger", "keychain holder", "key rack"),
    "chaveiro": ("keychain", "key ring", "key fob"),
    "organizador": ("organizer", "desk organizer", "storage"),
    "suporte": ("holder", "stand", "mount", "bracket"),
    "suporte de celular": ("phone stand", "phone holder", "smartphone stand"),
    "suporte de fone": ("headphone stand", "headset holder"),
    "gancho": ("hook", "wall hook"),
    "cabide": ("hanger", "coat hanger"),
    "vaso": ("vase", "planter", "pot"),
    "vaso de planta": ("planter", "flower pot", "plant pot"),
    "luminaria": ("lamp", "lithophane lamp", "night light", "lampshade"),
    "abajur": ("lampshade", "lamp shade"),
    "porta retrato": ("photo frame", "picture frame"),
    "porta guardanapo": ("napkin holder", "napkin ring"),
    "porta papel higienico": ("toilet paper holder",),
    "escorredor": ("drainer", "drying rack"),
    "prateleira": ("shelf", "wall shelf"),
    "caixa": ("box", "storage box", "container"),
    "tampa": ("lid", "cap"),
    "porta escova": ("toothbrush holder",),
    "banheiro": ("bathroom",),
    "decoracao": ("decor", "decoration", "home decor"),
    "parede": ("wall art", "wall mount"),
    # festa / social
    "topo de bolo": ("cake topper", "cake decoration"),
    "lembrancinha": ("party favor", "party favour", "giveaway", "souvenir"),
    "festa infantil": ("kids party", "birthday party", "party decoration"),
    "aniversario": ("birthday",),
    "casamento": ("wedding", "bride and groom"),
    "noivos": ("wedding cake topper", "bride groom"),
    "batizado": ("baptism", "christening"),
    "formatura": ("graduation",),
    "cha de bebe": ("baby shower",),
    "dia das maes": ("mothers day",),
    "dia dos pais": ("fathers day",),
    "natal": ("christmas", "xmas", "christmas ornament"),
    "pascoa": ("easter", "easter egg"),
    "presente": ("gift", "gift idea"),
    "coracao": ("heart", "love"),
    "letras": ("letters", "alphabet", "3d letters"),
    "nome": ("name", "custom name", "name plate"),
    "frase": ("quote", "text sign", "word art"),
    "placa": ("sign", "plaque", "door sign"),
    # esporte / times
    "futebol": ("soccer", "football"),
    "trofeu": ("trophy", "award"),
    "medalha": ("medal",),
    "bola": ("ball",),
    "academia": ("gym", "fitness"),
    "bicicleta": ("bike", "bicycle"),
    # infantil
    "brinquedo": ("toy", "kids toy"),
    "quebra cabeca": ("puzzle", "3d puzzle"),
    "dinossauro": ("dinosaur", "dino"),
    "carrinho": ("toy car", "car toy"),
    "boneco": ("figure", "figurine", "action figure"),
    "articulado": ("articulated", "flexi", "print in place"),
    "fidget": ("fidget toy", "fidget"),
    "unicornio": ("unicorn",),
    "dragao": ("dragon",),
    "foguete": ("rocket", "spaceship"),
    "avião": ("airplane", "plane"),
    "aviao": ("airplane", "plane"),
    "trem": ("train",),
    "robo": ("robot",),
    # pets
    "pet": ("pet", "dog", "cat"),
    "cachorro": ("dog", "puppy"),
    "gato": ("cat", "kitty"),
    "comedouro": ("pet bowl", "feeder", "food bowl"),
    "coleira": ("collar", "pet tag"),
    # escritorio / utilidades
    "escritorio": ("office", "desk"),
    "porta caneta": ("pen holder", "pencil holder", "desk tidy"),
    "marcador de pagina": ("bookmark",),
    "suporte notebook": ("laptop stand", "notebook stand"),
    "organizador de cabos": ("cable organizer", "cable holder", "cable clip"),
    "ferramenta": ("tool", "tool holder"),
    "gaveteiro": ("drawer", "parts drawer"),
    "automotivo": ("car accessory", "car mount"),
    "carro": ("car", "automotive"),
    "moto": ("motorcycle", "motorbike"),
    # tecnicos
    "engrenagem": ("gear",),
    "parafuso": ("screw", "bolt"),
    "adaptador": ("adapter",),
    "calibracao": ("calibration", "test print"),
}

# Termos que ja funcionam em ingles e nao devem ser "traduzidos".
_JA_EM_INGLES = {"bbq", "gift", "toy", "vase", "box", "gear", "cosplay"}

# Conectivos que so atrapalham a busca em ingles.
_CONECTIVOS = {
    "de", "da", "do", "das", "dos", "para", "pra", "com", "sem", "em", "no",
    "na", "nos", "nas", "e", "o", "a", "os", "as", "um", "uma", "ao",
}


def _carregar_extras(raiz: Path | None) -> dict[str, tuple[str, ...]]:
    if raiz is None:
        return {}
    arquivo = Path(raiz) / "dicionario.txt"
    if not arquivo.is_file():
        return {}
    extras: dict[str, tuple[str, ...]] = {}
    for linha in arquivo.read_text(encoding="utf-8", errors="replace").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valores = linha.partition("=")
        variantes = tuple(v.strip() for v in valores.split(",") if v.strip())
        if variantes:
            extras[normalizar(chave)] = variantes
    return extras


def expandir(termo: str, raiz: Path | None = None, maximo: int = 6) -> list[str]:
    """Devolve as variantes de busca para um termo, comecando pelo original.

    Casa primeiro a frase inteira ("porta chaves"), depois palavra a palavra,
    e por fim monta uma combinacao traduzida da frase completa.
    """

    original = (termo or "").strip()
    if not original:
        return []

    tabela = {**DICIONARIO, **_carregar_extras(raiz)}
    variantes: list[str] = [original]

    def adicionar(valor: str) -> None:
        valor = valor.strip()
        if valor and normalizar(valor) not in {normalizar(v) for v in variantes}:
            variantes.append(valor)

    alvo = normalizar(original)
    for candidato in tabela.get(alvo, ()):
        adicionar(candidato)

    palavras = alvo.split()
    # Frases de duas palavras dentro do termo (ex.: "porta chaves de parede").
    for tamanho in (3, 2):
        for i in range(len(palavras) - tamanho + 1):
            trecho = " ".join(palavras[i : i + tamanho])
            for candidato in tabela.get(trecho, ()):
                adicionar(candidato)

    traduzido: list[str] = []
    for palavra in palavras:
        if palavra in _CONECTIVOS and len(palavras) > 1:
            continue
        if palavra in _JA_EM_INGLES:
            traduzido.append(palavra)
            continue
        candidatos = tabela.get(palavra)
        traduzido.append(candidatos[0] if candidatos else palavra)
        if candidatos and len(palavras) == 1:
            for extra in candidatos[1:]:
                adicionar(extra)
    frase = " ".join(traduzido)
    if len(palavras) > 1:
        adicionar(frase)

    return variantes[:maximo]
