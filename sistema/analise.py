# -*- coding: utf-8 -*-
"""Ler um arquivo 3D e devolver o que o cadastro de produto precisa.

Nao ha geometria nova aqui. Isto e uma ponte para o analisador de malha do
pacote morumbi3d, que ja mede peso, tempo, caixa envolvente e se a peca cabe
na mesa -- e que ja pegou junta em T, malha aberta e erro de preco de 9x.

A regra de ouro do CLAUDE.md vale igual: o sistema CHAMA o analisador, nunca
reimplementa a medicao.
"""
from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

from morumbi3d.config import Config
from morumbi3d.mesh import analisar_arquivo

PASTA_ARQUIVOS = "produtos"
EXTENSOES = {".stl", ".3mf", ".obj"}
TAMANHO_MAX = 25 * 1024 * 1024


class ArquivoRecusado(Exception):
    """O arquivo nao serve, e o motivo cabe na tela."""


def _pasta(raiz: Path) -> Path:
    destino = raiz / PASTA_ARQUIVOS
    destino.mkdir(parents=True, exist_ok=True)
    return destino


def nome_seguro(nome: str) -> str:
    """So o basename, sem acento e sem nada que ande para fora da pasta."""
    nome = os.path.basename(nome or "")
    nome = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    nome = re.sub(r"[^A-Za-z0-9._-]+", "-", nome).strip("-._")
    return nome[:80] or "modelo.stl"


def guardar(arquivo, raiz: Path) -> Path:
    """Grava o upload e devolve o caminho. Recusa antes de gravar."""
    nome = nome_seguro(getattr(arquivo, "filename", ""))
    if Path(nome).suffix.lower() not in EXTENSOES:
        raise ArquivoRecusado(
            f"Formato nao suportado. Aceito {', '.join(sorted(EXTENSOES))}.")
    destino = _pasta(raiz) / nome
    tronco, sufixo, n = destino.stem, destino.suffix, 1
    while destino.exists():
        destino = destino.with_name(f"{tronco}-{n}{sufixo}")
        n += 1
    arquivo.save(str(destino))
    if destino.stat().st_size > TAMANHO_MAX:
        destino.unlink(missing_ok=True)
        raise ArquivoRecusado("Arquivo maior que 25 MB.")
    if destino.stat().st_size == 0:
        destino.unlink(missing_ok=True)
        raise ArquivoRecusado("Arquivo vazio.")
    return destino


def medir(caminho: Path, cfg: Config | None = None) -> dict:
    """Peso, tempo, caixa e estado da malha, prontos para o formulario."""
    try:
        r = analisar_arquivo(caminho, cfg or Config())
    except Exception as erro:                      # arquivo corrompido ou truncado
        raise ArquivoRecusado(f"Nao consegui ler o arquivo: {erro}") from erro

    x, y, z = r.dimensoes_mm
    return {
        "arquivo": caminho.name,
        "gramas": round(r.material_g, 1),
        "horas": round(r.tempo_h, 2),
        "caixa_x": round(x, 1),
        "caixa_y": round(y, 1),
        "caixa_z": round(z, 1),
        "malha_ok": 1 if (r.fechada and not r.arestas_nao_manifold) else 0,
        "malha_nota": r.nota,
        "fechada": r.fechada,
        "arestas_abertas": r.arestas_abertas,
        "partes_soltas": r.partes_soltas,
        "cabe_na_mesa": r.cabe_na_mesa,
        "cabe_girando": r.cabe_girando,
        "suporte": r.suporte,
        "problemas": list(r.problemas),
        "alertas": list(r.alertas),
        "resumo": r.resumo(),
    }
