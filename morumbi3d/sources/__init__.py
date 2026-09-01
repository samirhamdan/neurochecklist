"""Registro de conectores de fonte."""

from __future__ import annotations

from ..config import Config
from ..net import SessaoEducada
from .base import API_CHAVE, API_OFICIAL, SEM_API, Conector, ConectorNaoOficial
from .cults3d import Cults3D
from .github_repo import GitHubModelos
from .makerworld import MakerWorld
from .printables import Printables
from .thangs import Thangs
from .thingiverse import Thingiverse

CLASSES: tuple[type[Conector], ...] = (
    Thingiverse,
    MakerWorld,
    Printables,
    Thangs,
    Cults3D,
    GitHubModelos,
)

__all__ = [
    "API_CHAVE", "API_OFICIAL", "SEM_API", "Conector", "ConectorNaoOficial",
    "CLASSES", "instanciar", "disponiveis", "por_id",
]


def instanciar(cfg: Config, sessao: SessaoEducada | None = None) -> list[Conector]:
    sessao = sessao or SessaoEducada(cfg)
    return [classe(cfg, sessao) for classe in CLASSES]


def por_id(cfg: Config, ident: str, sessao: SessaoEducada | None = None) -> Conector | None:
    for conector in instanciar(cfg, sessao):
        if conector.id == ident:
            return conector
    return None


def disponiveis(cfg: Config, sessao: SessaoEducada | None = None) -> list[Conector]:
    """So os conectores ligados e prontos para uso."""

    return [c for c in instanciar(cfg, sessao) if c.disponivel()[0]]
