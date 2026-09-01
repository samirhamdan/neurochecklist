"""Thangs — o diferencial aqui e busca por geometria, nao so por texto.

Este conector cobre a busca por palavra-chave. A busca por forma (enviar uma
foto/modelo de referencia) e a funcionalidade de segunda fase prevista na
secao 4 da especificacao; o gancho ``buscar_por_geometria`` ja esta marcado
abaixo para quando ela for implementada.
"""

from __future__ import annotations

import urllib.parse

from ..models import Candidato
from ..net import AcessoNegado, FalhaRede
from .base import ConectorNaoOficial, achar_lista, primeiro

ENDPOINT = "https://thangs.com/api/models/search"


class Thangs(ConectorNaoOficial):
    id = "thangs"
    nome = "Thangs"
    site = "https://thangs.com"
    observacao = "busca por similaridade de forma (2a fase); API parcial"

    def buscar(self, termo: str, limite: int = 20) -> list[Candidato]:
        url = (
            f"{ENDPOINT}?searchTerm={urllib.parse.quote(termo)}"
            f"&pageSize={min(limite, 30)}&page=0"
        )
        try:
            dados = self.sessao.obter(url).json()
        except (AcessoNegado, FalhaRede, ValueError) as exc:
            raise FalhaRede(f"Thangs: {exc}") from exc

        itens = achar_lista(dados, "results", "models", "data.results")
        candidatos = []
        for item in itens[:limite]:
            ident = str(primeiro(item, "modelId", "id", padrao=""))
            candidatos.append(
                Candidato(
                    fonte=self.id,
                    fonte_id=ident,
                    titulo=str(primeiro(item, "name", "title", padrao="")),
                    url=str(primeiro(item, "url", padrao=f"{self.site}/m/{ident}")),
                    autor=str(primeiro(item, "owner.username", "ownerUsername", padrao="")),
                    descricao=str(primeiro(item, "description", padrao=""))[:2000],
                    formatos=["stl"],
                    licenca_raw=str(primeiro(item, "license", "licenseType", padrao="")),
                    thumb_url=str(primeiro(item, "thumbnailUrl", "thumbnail", padrao="")),
                    gratuito=True,
                    downloads=primeiro(item, "downloadCount"),
                    curtidas=primeiro(item, "likeCount"),
                )
            )
        return [c for c in candidatos if c.fonte_id and c.titulo]

    def buscar_por_geometria(self, arquivo: str, limite: int = 20) -> list[Candidato]:
        """Reservado para a 2a fase (busca por forma a partir de um arquivo)."""

        raise NotImplementedError(
            "busca por geometria e funcionalidade da segunda fase (secao 4 da "
            "especificacao) — ainda nao implementada"
        )
