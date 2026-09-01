"""Repositorios abertos no GitHub.

Volume menor, mas e a fonte com a licenca mais clara de todas: a API devolve
o SPDX do repositorio. Otimo para modelos tecnicos e colecoes open source.

``GITHUB_TOKEN`` e opcional — sem ele a API publica permite poucas buscas por
hora.
"""

from __future__ import annotations

import os
import urllib.parse

from ..models import Candidato
from ..net import AcessoNegado, FalhaRede
from .base import API_OFICIAL, Conector

BASE = "https://api.github.com"


class GitHubModelos(Conector):
    id = "github"
    nome = "GitHub (repositorios abertos)"
    site = "https://github.com"
    acesso = API_OFICIAL
    exige_optin = False
    observacao = "licenca explicita (SPDX); volume menor que os marketplaces"

    def _pronta(self) -> tuple[bool, str]:
        if os.environ.get("GITHUB_TOKEN"):
            return True, "pronta (com GITHUB_TOKEN)"
        return True, "pronta (API publica, poucas buscas por hora sem GITHUB_TOKEN)"

    def buscar(self, termo: str, limite: int = 20) -> list[Candidato]:
        consulta = f"{termo} stl in:name,description,readme"
        url = (
            f"{BASE}/search/repositories?q={urllib.parse.quote(consulta)}"
            f"&per_page={min(limite, 30)}&sort=stars&order=desc"
        )
        cabecalhos = {"Accept": "application/vnd.github+json"}
        token = os.environ.get("GITHUB_TOKEN", "").strip()
        if token:
            cabecalhos["Authorization"] = f"Bearer {token}"
        try:
            dados = self.sessao.obter(
                url, cabecalhos=cabecalhos, ignorar_robots=True
            ).json()
        except (AcessoNegado, FalhaRede, ValueError) as exc:
            raise FalhaRede(f"GitHub: {exc}") from exc

        itens = (dados or {}).get("items") or []
        candidatos = []
        for item in itens[:limite]:
            licenca = item.get("license") or {}
            candidatos.append(
                Candidato(
                    fonte=self.id,
                    fonte_id=str(item.get("id", "")),
                    titulo=item.get("full_name") or item.get("name") or "",
                    url=item.get("html_url") or "",
                    autor=(item.get("owner") or {}).get("login", ""),
                    descricao=(item.get("description") or "")[:2000],
                    tags=[t for t in (item.get("topics") or []) if isinstance(t, str)],
                    formatos=["stl"],
                    licenca_raw=licenca.get("spdx_id") or licenca.get("name") or "",
                    gratuito=True,
                    curtidas=item.get("stargazers_count"),
                    arquivo_url=(item.get("html_url") or "") + "/archive/refs/heads/"
                    + (item.get("default_branch") or "main") + ".zip",
                    extra={"linguagem": item.get("language") or ""},
                )
            )
        return [c for c in candidatos if c.fonte_id and c.titulo]
