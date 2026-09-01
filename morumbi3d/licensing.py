"""Classificador de licenca — o filtro critico para uso comercial.

Traduz o texto livre que cada repositorio informa ("Creative Commons -
Attribution - Non-Commercial", "CC BY-SA 4.0", "Standard Digital File
License"...) em respostas objetivas: pode vender? precisa creditar? pode
modificar?

Regra de ouro implementada aqui: **na duvida, ``desconhecido``** — nunca
``permitido``. O fluxo de curadoria trata ``desconhecido`` como bloqueio ate
alguem conferir a mao.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from pathlib import Path

from .brands import detectar, normalizar

PERMITIDO = "permitido"
PROIBIDO = "proibido"
DESCONHECIDO = "desconhecido"

RISCO_NENHUM = "nenhum"
RISCO_MEDIO = "medio"
RISCO_ALTO = "alto"


@dataclass
class Licenca:
    raw: str = ""
    codigo: str = "DESCONHECIDA"
    nome: str = "Licenca nao informada"
    comercial: str = DESCONHECIDO
    atribuicao: bool = False
    share_alike: bool = False
    sem_derivados: bool = False
    observacoes: tuple[str, ...] = ()

    @property
    def pode_vender(self) -> bool:
        return self.comercial == PERMITIDO

    def rotulo(self) -> str:
        marcas = []
        if self.atribuicao:
            marcas.append("exige credito")
        if self.share_alike:
            marcas.append("share-alike")
        if self.sem_derivados:
            marcas.append("sem modificar")
        extra = f" ({', '.join(marcas)})" if marcas else ""
        return f"{self.nome} — uso comercial {self.comercial}{extra}"

    def como_dict(self) -> dict:
        dados = asdict(self)
        dados["observacoes"] = list(self.observacoes)
        return dados


# (regex, codigo, nome, comercial, atribuicao, share_alike, sem_derivados, obs)
_REGRAS: tuple[tuple[str, str, str, str, bool, bool, bool, str], ...] = (
    (r"\bcc0\b|public domain|dominio publico|\bpd\b(?! ?f)",
     "CC0", "CC0 / Dominio publico", PERMITIDO, False, False, False, ""),
    (r"nc.?nd|non ?commercial.*no ?deriv|no ?deriv.*non ?commercial",
     "CC-BY-NC-ND", "CC BY-NC-ND", PROIBIDO, True, False, True,
     "proibe venda e proibe modificar"),
    (r"nc.?sa|non ?commercial.*share ?alike|share ?alike.*non ?commercial",
     "CC-BY-NC-SA", "CC BY-NC-SA", PROIBIDO, True, True, False,
     "uso nao comercial"),
    (r"\bnc\b|non ?commercial|nao ?comercial|noncommercial",
     "CC-BY-NC", "CC BY-NC", PROIBIDO, True, False, False,
     "uso nao comercial: nao pode vender a peca impressa"),
    (r"\bnd\b|no ?deriv|sem ?deriva",
     "CC-BY-ND", "CC BY-ND", PERMITIDO, True, False, True,
     "pode vender a peca como esta, mas NAO pode modificar o modelo"),
    (r"\bsa\b|share ?alike|compartilha ?igual",
     "CC-BY-SA", "CC BY-SA", PERMITIDO, True, True, False,
     "derivados precisam manter a mesma licenca"),
    (r"\bcc[ -]?by\b|creative commons.*attribut|atribuic",
     "CC-BY", "CC BY", PERMITIDO, True, False, False, ""),
    (r"\b(gpl|lgpl|agpl)\b|general public license",
     "GPL", "GPL / LGPL", PERMITIDO, True, True, False,
     "copyleft: derivados devem ser publicados sob a mesma licenca"),
    (r"\b(mit|bsd|apache)\b",
     "PERMISSIVA", "MIT / BSD / Apache", PERMITIDO, True, False, False, ""),
    (r"standard digital file license|thingiverse license|standard license",
     "PADRAO-PLATAFORMA", "Licenca padrao da plataforma", PROIBIDO, True, False, True,
     "licenca padrao de uso pessoal: venda so com autorizacao do autor"),
    (r"royalty ?free",
     "ROYALTY-FREE", "Royalty free", DESCONHECIDO, False, False, False,
     "conferir se a licenca royalty-free cobre venda de pecas fisicas"),
    (r"all rights reserved|todos os direitos reservados|proprietar",
     "RESERVADA", "Todos os direitos reservados", PROIBIDO, False, False, False,
     "sem permissao explicita de uso"),
    (r"uso pessoal|personal use only|nao comercializ",
     "PESSOAL", "Somente uso pessoal", PROIBIDO, False, False, False, ""),
    (r"commercial use allowed|uso comercial (permitido|liberado)|licenc[ae] comercial",
     "COMERCIAL", "Licenca comercial", PERMITIDO, False, False, False, ""),
)


def classificar(texto: str | None) -> Licenca:
    """Interpreta a string de licenca informada pela fonte."""

    bruto = (texto or "").strip()
    if not bruto:
        return Licenca(
            raw="",
            observacoes=("fonte nao informou licenca: conferir na pagina do modelo",),
        )
    alvo = normalizar(bruto)
    for padrao, codigo, nome, comercial, atrib, sa, nd, obs in _REGRAS:
        if re.search(padrao, alvo):
            observacoes = (obs,) if obs else ()
            return Licenca(
                raw=bruto,
                codigo=codigo,
                nome=nome,
                comercial=comercial,
                atribuicao=atrib,
                share_alike=sa,
                sem_derivados=nd,
                observacoes=observacoes,
            )
    return Licenca(
        raw=bruto,
        observacoes=(f"licenca '{bruto}' nao reconhecida: conferir a mao",),
    )


@dataclass
class RiscoMarca:
    nivel: str = RISCO_NENHUM
    termos: tuple[tuple[str, str], ...] = ()
    mensagem: str = ""

    def como_dict(self) -> dict:
        return {
            "nivel": self.nivel,
            "termos": [list(t) for t in self.termos],
            "mensagem": self.mensagem,
        }


def avaliar_risco(
    titulo: str = "",
    descricao: str = "",
    tags: list[str] | tuple[str, ...] = (),
    raiz: Path | None = None,
) -> RiscoMarca:
    """Procura marcas/personagens/times no texto do modelo."""

    achados_titulo = detectar(titulo, raiz)
    achados_resto = detectar(" ".join([descricao, " ".join(tags)]), raiz)
    vistos = {t for t, _ in achados_titulo}
    todos = achados_titulo + [(t, c) for t, c in achados_resto if t not in vistos]
    if not todos:
        return RiscoMarca()
    nivel = RISCO_ALTO if achados_titulo else RISCO_MEDIO
    lista = ", ".join(sorted({t for t, _ in todos}))
    onde = "no titulo" if achados_titulo else "na descricao/tags"
    return RiscoMarca(
        nivel=nivel,
        termos=tuple(todos),
        mensagem=(
            f"Propriedade intelectual de terceiros {onde} ({lista}). "
            "A licenca do arquivo NAO autoriza usar a marca/personagem: "
            "nao vender sem autorizacao do detentor."
        ),
    )


def seguro_para_venda(licenca: Licenca, risco: RiscoMarca) -> bool:
    """Unica porta de entrada para 'pode ir para producao comercial'."""

    return licenca.pode_vender and risco.nivel == RISCO_NENHUM


def motivo_bloqueio(licenca: Licenca, risco: RiscoMarca) -> str:
    if risco.nivel != RISCO_NENHUM:
        return risco.mensagem
    if licenca.comercial == PROIBIDO:
        return f"Licenca {licenca.nome} nao permite venda."
    if licenca.comercial == DESCONHECIDO:
        return "Licenca desconhecida: conferir na pagina do modelo antes de vender."
    return ""
