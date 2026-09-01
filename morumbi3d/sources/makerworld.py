"""MakerWorld (Bambu Lab) — a fonte mais alinhada a impressora da casa.

Modelos ja vem com perfil da Bambu, o que reduz o trabalho de fatiamento.
Nao ha API publica documentada: este conector usa o mesmo endpoint de busca
que o site chama no navegador e so roda se ligado na configuracao.
"""

from __future__ import annotations

import urllib.parse

from ..models import Candidato
from ..net import AcessoNegado, FalhaRede
from .base import ConectorNaoOficial, achar_lista, primeiro

ENDPOINT = "https://makerworld.com/api/v1/search/models"


class MakerWorld(ConectorNaoOficial):
    id = "makerworld"
    nome = "MakerWorld (Bambu Lab)"
    site = "https://makerworld.com"
    observacao = "perfis prontos para a Bambu; endpoint nao documentado"

    def buscar(self, termo: str, limite: int = 20) -> list[Candidato]:
        url = (
            f"{ENDPOINT}?keyword={urllib.parse.quote(termo)}"
            f"&limit={min(limite, 30)}&offset=0"
        )
        try:
            dados = self.sessao.obter(url).json()
        except (AcessoNegado, FalhaRede, ValueError) as exc:
            raise FalhaRede(f"MakerWorld: {exc}") from exc

        itens = achar_lista(dados, "hits", "data.hits", "data.list", "list")
        candidatos = []
        for item in itens[:limite]:
            ident = str(primeiro(item, "id", "designId", "modelId", padrao=""))
            licenca = primeiro(item, "license", "licenseType", "copyright", padrao="")
            candidatos.append(
                Candidato(
                    fonte=self.id,
                    fonte_id=ident,
                    titulo=str(primeiro(item, "title", "name", padrao="")),
                    url=str(primeiro(item, "url", padrao=f"{self.site}/models/{ident}")),
                    autor=str(
                        primeiro(item, "designCreator.name", "creator.name", "user.name", padrao="")
                    ),
                    descricao=str(primeiro(item, "summary", "description", padrao=""))[:2000],
                    formatos=["3mf", "stl"],
                    licenca_raw=str(licenca),
                    thumb_url=str(primeiro(item, "cover", "coverUrl", "thumbnail", padrao="")),
                    gratuito=not bool(primeiro(item, "isPaid", "paid", padrao=False)),
                    downloads=primeiro(item, "downloadCount", "downloads"),
                    curtidas=primeiro(item, "likeCount", "likes"),
                )
            )
        return [c for c in candidatos if c.fonte_id and c.titulo]
