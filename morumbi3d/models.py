"""Estruturas de dados compartilhadas entre conectores, banco e relatorios."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

STATUS_NOVO = "novo"
STATUS_APROVADO = "aprovado"
STATUS_REPROVADO = "reprovado"
STATUS_PRODUCAO = "producao"
STATUS_VALIDOS = (STATUS_NOVO, STATUS_APROVADO, STATUS_REPROVADO, STATUS_PRODUCAO)


@dataclass
class Candidato:
    """Um modelo encontrado numa fonte, antes de entrar no catalogo."""

    fonte: str
    fonte_id: str
    titulo: str
    url: str
    autor: str = ""
    descricao: str = ""
    tags: list[str] = field(default_factory=list)
    formatos: list[str] = field(default_factory=list)
    licenca_raw: str = ""
    thumb_url: str = ""
    gratuito: bool | None = None
    preco: float | None = None
    downloads: int | None = None
    curtidas: int | None = None
    arquivo_url: str = ""
    """Link direto para download, quando a fonte oferece."""

    extra: dict[str, Any] = field(default_factory=dict)

    def texto_completo(self) -> str:
        return " ".join([self.titulo, self.descricao, " ".join(self.tags)])

    def como_dict(self) -> dict:
        return asdict(self)
