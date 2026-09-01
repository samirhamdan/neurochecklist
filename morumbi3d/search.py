"""Orquestrador da busca multi-fonte.

Junta tudo: expande o termo para ingles, consulta cada fonte ligada, aplica os
filtros de licenca/risco, joga no catalogo e devolve um resumo. Uma fonte que
falha vira uma linha de erro no resultado — nunca derruba a busca inteira
(secao 2 e 3.1 da especificacao).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import Config
from .db import Catalogo
from .licensing import avaliar_risco, classificar, seguro_para_venda
from .lines import classificar as classificar_linha
from .models import Candidato
from .net import SessaoEducada
from .sources import Conector, instanciar
from .translate import expandir


@dataclass
class Achado:
    """Um candidato ja classificado, pronto para entrar no catalogo."""

    candidato: Candidato
    licenca: object
    risco: object
    linha: str = "Sem linha"
    colecao: str = ""
    modelo_id: int | None = None
    novo: bool = False

    @property
    def seguro(self) -> bool:
        return seguro_para_venda(self.licenca, self.risco)  # type: ignore[arg-type]


@dataclass
class ResultadoBusca:
    termo: str
    variantes: list[str] = field(default_factory=list)
    fontes_consultadas: list[str] = field(default_factory=list)
    fontes_ignoradas: list[tuple[str, str]] = field(default_factory=list)
    erros: list[str] = field(default_factory=list)
    achados: list[Achado] = field(default_factory=list)
    total_bruto: int = 0
    novos: int = 0
    descartados_filtro: int = 0

    def resumo(self) -> str:
        return (
            f"{self.total_bruto} resultado(s) brutos, {len(self.achados)} apos "
            f"filtros, {self.novos} novos no catalogo "
            f"({len(self.fontes_consultadas)} fonte(s), {len(self.erros)} erro(s))"
        )


def _conectores_para(
    cfg: Config, sessao: SessaoEducada, fontes: list[str] | None
) -> tuple[list[Conector], list[tuple[str, str]]]:
    escolhidos: list[Conector] = []
    ignorados: list[tuple[str, str]] = []
    for conector in instanciar(cfg, sessao):
        if fontes and conector.id not in fontes:
            continue
        ok, motivo = conector.disponivel()
        if ok:
            escolhidos.append(conector)
        else:
            ignorados.append((conector.id, motivo))
    return escolhidos, ignorados


def buscar(
    cfg: Config,
    termo: str,
    *,
    limite_por_fonte: int = 20,
    fontes: list[str] | None = None,
    traduzir: bool = True,
    so_comercial: bool = False,
    so_gratuitos: bool = False,
    com_imagem: bool = False,
    formato: str | None = None,
    catalogo: Catalogo | None = None,
    baixar_imagens: bool = False,
    sessao: SessaoEducada | None = None,
) -> ResultadoBusca:
    """Busca ``termo`` em todas as fontes ligadas e registra no catalogo."""

    sessao = sessao or SessaoEducada(cfg)
    resultado = ResultadoBusca(termo=termo)
    resultado.variantes = expandir(termo, cfg.raiz) if traduzir else [termo]

    conectores, ignorados = _conectores_para(cfg, sessao, fontes)
    resultado.fontes_ignoradas = ignorados
    if not conectores:
        resultado.erros.append(
            "nenhuma fonte disponivel — rode `morumbi3d fontes` para ver o motivo"
        )
        return resultado

    vistos: set[tuple[str, str]] = set()
    brutos: list[Candidato] = []

    for conector in conectores:
        resultado.fontes_consultadas.append(conector.id)
        for variante in resultado.variantes:
            try:
                encontrados = conector.buscar(variante, limite_por_fonte)
            except Exception as exc:  # isolamento por fonte: nunca derruba o resto
                resultado.erros.append(f"[{conector.id}] {exc}")
                break  # variantes seguintes provavelmente falham igual
            for candidato in encontrados:
                chave = (candidato.fonte, candidato.fonte_id)
                if chave in vistos:
                    continue
                vistos.add(chave)
                brutos.append(candidato)

    resultado.total_bruto = len(brutos)

    for candidato in brutos:
        licenca = classificar(candidato.licenca_raw)
        risco = avaliar_risco(
            candidato.titulo, candidato.descricao, candidato.tags, cfg.raiz
        )
        if so_comercial and not seguro_para_venda(licenca, risco):
            resultado.descartados_filtro += 1
            continue
        if so_gratuitos and candidato.gratuito is False:
            resultado.descartados_filtro += 1
            continue
        if com_imagem and not candidato.thumb_url:
            resultado.descartados_filtro += 1
            continue
        if formato and formato.lower() not in [f.lower() for f in candidato.formatos]:
            resultado.descartados_filtro += 1
            continue
        linha, colecao, _ = classificar_linha(
            candidato.titulo, candidato.descricao, candidato.tags
        )
        resultado.achados.append(
            Achado(candidato=candidato, licenca=licenca, risco=risco,
                   linha=linha, colecao=colecao)
        )

    if catalogo is not None:
        for achado in resultado.achados:
            modelo_id, novo = catalogo.registrar(
                achado.candidato,
                termo_busca=termo,
                licenca=achado.licenca,  # type: ignore[arg-type]
                risco=achado.risco,  # type: ignore[arg-type]
                linha=achado.linha,
                colecao=achado.colecao,
            )
            achado.modelo_id, achado.novo = modelo_id, novo
            resultado.novos += int(novo)
            if baixar_imagens and achado.candidato.thumb_url:
                caminho = sessao.baixar_imagem(
                    achado.candidato.thumb_url, f"{achado.candidato.fonte}-{modelo_id}"
                )
                if caminho:
                    catalogo.salvar_thumb(modelo_id, str(caminho))
        catalogo.registrar_busca(
            termo,
            resultado.variantes,
            resultado.fontes_consultadas,
            resultado.total_bruto,
            resultado.novos,
            resultado.erros,
        )

    return resultado
