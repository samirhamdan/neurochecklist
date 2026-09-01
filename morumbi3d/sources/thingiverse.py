"""Thingiverse — unica fonte grande com API oficial documentada.

A API existe, mas e instavel e tem limite de taxa; por isso o conector
tolera erro e devolve o que conseguiu. Requer uma chave (App Token) criada em
https://www.thingiverse.com/apps/create e exportada em ``THINGIVERSE_TOKEN``.
"""

from __future__ import annotations

import os
import urllib.parse

from ..models import Candidato
from ..net import AcessoNegado, FalhaRede
from .base import API_CHAVE, Conector

BASE = "https://api.thingiverse.com"


class Thingiverse(Conector):
    id = "thingiverse"
    nome = "Thingiverse"
    site = "https://www.thingiverse.com"
    acesso = API_CHAVE
    exige_optin = False
    observacao = "API oficial, porem instavel e com limite de taxa"

    def _token(self) -> str:
        return os.environ.get("THINGIVERSE_TOKEN", "").strip()

    def _pronta(self) -> tuple[bool, str]:
        if not self._token():
            return False, (
                "falta a chave: crie um App em "
                "https://www.thingiverse.com/apps/create e exporte "
                "THINGIVERSE_TOKEN"
            )
        return True, "pronta (API oficial)"

    def buscar(self, termo: str, limite: int = 20) -> list[Candidato]:
        token = self._token()
        if not token:
            return []
        url = (
            f"{BASE}/search/{urllib.parse.quote(termo)}"
            f"?type=things&per_page={min(limite, 30)}&sort=popular"
        )
        try:
            resposta = self.sessao.obter(
                url,
                cabecalhos={"Authorization": f"Bearer {token}"},
                ignorar_robots=True,  # API oficial, nao e o site publico
            )
            dados = resposta.json()
        except (AcessoNegado, FalhaRede, ValueError) as exc:
            raise FalhaRede(f"Thingiverse: {exc}") from exc

        itens = dados.get("hits", dados) if isinstance(dados, dict) else dados
        if not isinstance(itens, list):
            return []

        candidatos = []
        for item in itens[:limite]:
            if not isinstance(item, dict) or item.get("is_nsfw"):
                continue
            criador = item.get("creator") or {}
            candidatos.append(
                Candidato(
                    fonte=self.id,
                    fonte_id=str(item.get("id", "")),
                    titulo=(item.get("name") or "").strip(),
                    url=item.get("public_url") or f"{self.site}/thing:{item.get('id')}",
                    autor=(criador.get("name") or criador.get("first_name") or "").strip(),
                    descricao=(item.get("description") or "")[:2000],
                    tags=[t for t in (item.get("tags") or []) if isinstance(t, str)],
                    formatos=["stl"],
                    licenca_raw=item.get("license") or "",
                    thumb_url=item.get("preview_image") or item.get("thumbnail") or "",
                    gratuito=True,
                    downloads=item.get("download_count"),
                    curtidas=item.get("like_count"),
                    extra={"api": item.get("url", "")},
                )
            )
        return [c for c in candidatos if c.fonte_id and c.titulo]
