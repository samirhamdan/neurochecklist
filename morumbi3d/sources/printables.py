"""Printables (Prusa) — acervo grande e de boa qualidade, sem API publica.

O site expoe um endpoint GraphQL para o proprio front-end. Nao e documentado
nem estavel: este conector so roda se voce ligar em ``morumbi3d.toml`` depois
de conferir os termos de uso do Printables.
"""

from __future__ import annotations

import json

from ..models import Candidato
from ..net import AcessoNegado, FalhaRede
from .base import ConectorNaoOficial, achar_lista, primeiro

ENDPOINT = "https://api.printables.com/graphql/"

CONSULTA = """
query BuscaMorumbi($query: String!, $limit: Int!) {
  result: searchPrints(query: $query, limit: $limit, offset: 0) {
    items {
      id
      name
      slug
      summary
      license { name }
      user { publicUsername }
      image { filePath }
      likesCount
      downloadCount
    }
  }
}
"""


class Printables(ConectorNaoOficial):
    id = "printables"
    nome = "Printables (Prusa)"
    site = "https://www.printables.com"
    observacao = "otimo acervo; endpoint nao documentado, pode mudar sem aviso"

    def buscar(self, termo: str, limite: int = 20) -> list[Candidato]:
        corpo = json.dumps(
            {
                "query": CONSULTA,
                "variables": {"query": termo, "limit": min(limite, 30)},
            }
        ).encode("utf-8")
        try:
            dados = self.sessao.obter(
                ENDPOINT,
                cabecalhos={"Content-Type": "application/json"},
                dados=corpo,
            ).json()
        except (AcessoNegado, FalhaRede, ValueError) as exc:
            raise FalhaRede(f"Printables: {exc}") from exc

        if isinstance(dados, dict) and dados.get("errors"):
            raise FalhaRede(
                "Printables: a consulta GraphQL foi recusada — o endpoint "
                "mudou. Ajuste CONSULTA em sources/printables.py ou desligue "
                "a fonte."
            )

        itens = achar_lista(dados, "data.result.items", "data.result")
        candidatos = []
        for item in itens[:limite]:
            ident = str(primeiro(item, "id", padrao=""))
            slug = primeiro(item, "slug", padrao=ident)
            imagem = primeiro(item, "image.filePath", "image", padrao="")
            candidatos.append(
                Candidato(
                    fonte=self.id,
                    fonte_id=ident,
                    titulo=str(primeiro(item, "name", "title", padrao="")),
                    url=f"{self.site}/model/{slug}",
                    autor=str(primeiro(item, "user.publicUsername", "user.handle", padrao="")),
                    descricao=str(primeiro(item, "summary", "description", padrao=""))[:2000],
                    formatos=["stl", "3mf"],
                    licenca_raw=str(primeiro(item, "license.name", "license", padrao="")),
                    thumb_url=(
                        f"https://media.printables.com/{imagem}"
                        if imagem and not str(imagem).startswith("http")
                        else str(imagem)
                    ),
                    gratuito=True,
                    downloads=primeiro(item, "downloadCount"),
                    curtidas=primeiro(item, "likesCount"),
                )
            )
        return [c for c in candidatos if c.fonte_id and c.titulo]
