"""Contrato comum dos conectores de fonte.

Cada repositorio tem um modulo proprio (secao 2 da especificacao: o acesso
muda de site para site). O orquestrador so conhece esta interface, entao uma
fonte fora do ar nao derruba as outras.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..config import Config
from ..models import Candidato
from ..net import SessaoEducada

# Rotulos de tipo de acesso, usados no comando `fontes`.
API_OFICIAL = "API oficial"
API_CHAVE = "API oficial (exige chave)"
SEM_API = "sem API publica oficial"


class Conector(ABC):
    """Uma fonte de modelos 3D."""

    id: str = ""
    nome: str = ""
    site: str = ""
    acesso: str = SEM_API
    exige_optin: bool = False
    """True para fontes sem API publica: so rodam se ligadas na configuracao."""

    observacao: str = ""

    def __init__(self, cfg: Config, sessao: SessaoEducada) -> None:
        self.cfg = cfg
        self.sessao = sessao

    # ------------------------------------------------------------------
    def ligada(self) -> bool:
        return bool(getattr(self.cfg.fontes, self.id, False))

    def disponivel(self) -> tuple[bool, str]:
        """(pode_usar, motivo). Motivo sempre preenchido, para o usuario ler."""

        if not self.ligada():
            if self.exige_optin:
                return False, (
                    f"desligada: {self.acesso}. Ligue em morumbi3d.toml "
                    f"([fontes] {self.id} = true) so depois de conferir os "
                    f"termos de uso de {self.site}"
                )
            return False, f"desligada em morumbi3d.toml ([fontes] {self.id})"
        return self._pronta()

    def _pronta(self) -> tuple[bool, str]:
        """Checagens especificas da fonte (chave de API, etc.)."""

        return True, "pronta"

    @abstractmethod
    def buscar(self, termo: str, limite: int = 20) -> list[Candidato]:
        """Busca por palavra-chave. Deve devolver lista (vazia se nada)."""

    def __repr__(self) -> str:  # pragma: no cover - conveniencia
        return f"<Conector {self.id}>"


def primeiro(dado: dict, *chaves: str, padrao=None):
    """Primeiro valor nao vazio entre varias chaves possiveis.

    As fontes sem API documentada mudam nomes de campo sem aviso; procurar em
    varias chaves deixa o conector mais resistente a essas mudancas.
    """

    for chave in chaves:
        atual: object = dado
        for parte in chave.split("."):
            if not isinstance(atual, dict):
                atual = None
                break
            atual = atual.get(parte)
        if atual not in (None, "", [], {}):
            return atual
    return padrao


def achar_lista(dado, *caminhos: str) -> list:
    """Encontra a lista de resultados dentro de um JSON de formato incerto."""

    for caminho in caminhos:
        valor = primeiro(dado, caminho) if isinstance(dado, dict) else None
        if isinstance(valor, list):
            return valor
    if isinstance(dado, list):
        return dado
    # Ultimo recurso: a maior lista de dicionarios em qualquer nivel.
    melhor: list = []
    pilha = [dado]
    while pilha:
        atual = pilha.pop()
        if isinstance(atual, dict):
            pilha.extend(atual.values())
        elif isinstance(atual, list):
            if atual and all(isinstance(i, dict) for i in atual) and len(atual) > len(melhor):
                melhor = atual
            pilha.extend(i for i in atual if isinstance(i, (dict, list)))
    return melhor


class ConectorNaoOficial(Conector):
    """Base das fontes sem API publica documentada.

    Estes conectores usam os mesmos endpoints que o site abre no navegador.
    Consequencias assumidas de proposito:

    * ficam DESLIGADOS ate alguem ligar na configuracao, depois de conferir
      os termos de uso;
    * passam pelo robots.txt como qualquer outro acesso;
    * podem quebrar quando o site mudar — nesse caso o conector devolve um
      erro claro em vez de resultado errado, e a busca segue nas outras fontes.
    """

    exige_optin = True
    acesso = SEM_API

    def _pronta(self) -> tuple[bool, str]:
        return True, (
            f"ligada por sua conta e risco: {self.site} nao tem API publica "
            "documentada; confira os termos de uso"
        )
