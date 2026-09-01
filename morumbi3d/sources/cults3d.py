"""Cults3D — acervo misto (gratuito e pago), muitos modelos com licenca restrita.

Como boa parte do acervo e paga e de licenca limitada, o conector marca o
preco quando a fonte informa, e o filtro de licenca faz o resto do trabalho.
Sem API publica documentada: fonte opt-in.
"""

from __future__ import annotations

import urllib.parse

from ..models import Candidato
from ..net import AcessoNegado, FalhaRede
from .base import ConectorNaoOficial, achar_lista, primeiro

ENDPOINT = "https://cults3d.com/en/search"


class Cults3D(ConectorNaoOficial):
    id = "cults3d"
    nome = "Cults3D"
    site = "https://cults3d.com"
    observacao = "misto gratuito/pago; filtrar por licenca e essencial"

    def buscar(self, termo: str, limite: int = 20) -> list[Candidato]:
        url = f"{ENDPOINT}?q={urllib.parse.quote(termo)}&only_free=true"
        try:
            resposta = self.sessao.obter(url)
        except (AcessoNegado, FalhaRede) as exc:
            raise FalhaRede(f"Cults3D: {exc}") from exc

        try:
            dados = resposta.json()
        except ValueError as exc:
            raise FalhaRede(
                "Cults3D: a busca devolveu HTML, nao JSON. O site nao oferece "
                "endpoint de busca em JSON — use a API oficial com chave "
                f"(https://cults3d.com/en/pages/api) ou desligue a fonte. ({exc})"
            ) from exc

        itens = achar_lista(dados, "results", "creations", "data")
        candidatos = []
        for item in itens[:limite]:
            ident = str(primeiro(item, "id", "slug", padrao=""))
            preco = primeiro(item, "price.cents", "price")
            candidatos.append(
                Candidato(
                    fonte=self.id,
                    fonte_id=ident,
                    titulo=str(primeiro(item, "name", "title", padrao="")),
                    url=str(primeiro(item, "url", padrao=f"{self.site}/en/3d-model/{ident}")),
                    autor=str(primeiro(item, "creator.nick", "creator.name", padrao="")),
                    descricao=str(primeiro(item, "description", padrao=""))[:2000],
                    formatos=["stl"],
                    licenca_raw=str(primeiro(item, "license", padrao="")),
                    thumb_url=str(primeiro(item, "illustrationImageUrl", "image", padrao="")),
                    gratuito=not bool(preco),
                    preco=float(preco) / 100.0 if isinstance(preco, (int, float)) and preco else None,
                )
            )
        return [c for c in candidatos if c.fonte_id and c.titulo]
