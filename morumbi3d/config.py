"""Configuracao central do sistema.

A configuracao vem, nesta ordem de precedencia:

1. variaveis de ambiente (``MORUMBI3D_*``);
2. arquivo ``morumbi3d.toml`` na raiz do projeto (ou o apontado por
   ``MORUMBI3D_CONFIG``);
3. os padroes abaixo.

Os numeros de custo/tempo sao PADROES EDITAVEIS: ajuste-os no
``morumbi3d.toml`` com os valores reais da operacao antes de usar a
precificacao para decidir preco de venda.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

DEFAULT_ROOT = Path(os.environ.get("MORUMBI3D_HOME", Path.home() / ".morumbi3d"))


@dataclass
class ImpressoraConfig:
    """Limites fisicos da impressora usada na producao."""

    nome: str = "Bambu Lab A1 / A2L"
    mesa_x_mm: float = 256.0
    mesa_y_mm: float = 256.0
    altura_max_mm: float = 256.0
    folga_mm: float = 3.0
    """Margem de seguranca subtraida da mesa ao verificar se o modelo cabe."""

    altura_camada_mm: float = 0.24
    preenchimento: float = 0.08
    """Fracao (0-1). O guia padroniza 8%."""

    espessura_parede_mm: float = 1.2
    """3 perimetros de 0,4 mm — usado para estimar material."""

    vazao_cm3_por_hora: float = 12.0
    """Vazao media efetiva do conjunto impressora/perfil, em cm3/h."""

    overhead_horas: float = 0.15
    """Aquecimento, purga e primeira camada."""

    angulo_suporte_graus: float = 45.0
    """Acima deste angulo (medido a partir da vertical) o slicer poe suporte."""


@dataclass
class CustoConfig:
    """Formula de custo: material + maquina + margem."""

    densidade_g_cm3: float = 1.24
    """PLA. PETG ~1.27, ABS ~1.04."""

    preco_filamento_kg: float = 120.0
    custo_hora_maquina: float = 3.50
    """Depreciacao + energia + manutencao por hora de impressao."""

    taxa_falha: float = 0.10
    """Fracao adicionada ao custo para cobrir refugo/reimpressao."""

    custo_fixo_por_peca: float = 1.50
    """Embalagem, etiqueta, acabamento."""

    multiplicador_margem: float = 3.0
    densidade_suporte: float = 0.15
    """Fracao do volume de suporte efetivamente extrudado."""


@dataclass
class RedeConfig:
    """Boas praticas de acesso as fontes (secao 6 da especificacao)."""

    user_agent: str = (
        "Morumbi3D-Curadoria/0.1 (+contato: configure MORUMBI3D_CONTATO)"
    )
    contato: str = ""
    intervalo_min_s: float = 3.0
    """Intervalo minimo entre requisicoes ao MESMO host."""

    timeout_s: float = 20.0
    tentativas: int = 3
    cache_ttl_s: int = 60 * 60 * 24 * 7
    respeitar_robots: bool = True
    tamanho_max_download_mb: float = 80.0


@dataclass
class FontesConfig:
    """Habilitacao por fonte.

    Fontes sem API publica oficial ficam DESLIGADAS por padrao: ligue apenas
    depois de conferir os termos de uso do site (secao 6 da especificacao).
    """

    thingiverse: bool = True
    github: bool = True
    printables: bool = False
    makerworld: bool = False
    thangs: bool = False
    cults3d: bool = False


@dataclass
class Config:
    raiz: Path = field(default_factory=lambda: DEFAULT_ROOT)
    impressora: ImpressoraConfig = field(default_factory=ImpressoraConfig)
    custo: CustoConfig = field(default_factory=CustoConfig)
    rede: RedeConfig = field(default_factory=RedeConfig)
    fontes: FontesConfig = field(default_factory=FontesConfig)

    # --- caminhos derivados ------------------------------------------------
    @property
    def banco(self) -> Path:
        return self.raiz / "catalogo.sqlite3"

    @property
    def cache_http(self) -> Path:
        return self.raiz / "cache" / "http"

    @property
    def cache_arquivos(self) -> Path:
        return self.raiz / "cache" / "arquivos"

    @property
    def cache_imagens(self) -> Path:
        return self.raiz / "cache" / "imagens"

    @property
    def relatorios(self) -> Path:
        return self.raiz / "relatorios"

    def preparar_diretorios(self) -> None:
        for caminho in (
            self.raiz,
            self.cache_http,
            self.cache_arquivos,
            self.cache_imagens,
            self.relatorios,
        ):
            caminho.mkdir(parents=True, exist_ok=True)

    @property
    def mesa_util(self) -> tuple[float, float, float]:
        imp = self.impressora
        folga = imp.folga_mm
        return (
            max(imp.mesa_x_mm - folga, 0.0),
            max(imp.mesa_y_mm - folga, 0.0),
            max(imp.altura_max_mm - folga, 0.0),
        )


def _aplicar(secao: Any, dados: dict[str, Any], erros: list[str], prefixo: str) -> None:
    validos = {f.name: f for f in fields(secao)}
    for chave, valor in dados.items():
        campo = validos.get(chave)
        if campo is None:
            erros.append(f"{prefixo}.{chave}: opcao desconhecida (ignorada)")
            continue
        try:
            if campo.type in ("float", float):
                valor = float(valor)
            elif campo.type in ("int", int):
                valor = int(valor)
            elif campo.type in ("bool", bool):
                valor = bool(valor)
            else:
                valor = str(valor)
        except (TypeError, ValueError):
            erros.append(f"{prefixo}.{chave}: valor invalido ({valor!r}); mantido o padrao")
            continue
        setattr(secao, chave, valor)


def carregar_config(caminho: Path | str | None = None) -> Config:
    """Monta a configuracao a partir do TOML e do ambiente."""

    cfg = Config()
    erros: list[str] = []

    arquivo = caminho or os.environ.get("MORUMBI3D_CONFIG")
    candidatos = [Path(arquivo)] if arquivo else [Path.cwd() / "morumbi3d.toml", DEFAULT_ROOT / "morumbi3d.toml"]
    for candidato in candidatos:
        if candidato.is_file():
            with candidato.open("rb") as fh:
                dados = tomllib.load(fh)
            if "raiz" in dados:
                cfg.raiz = Path(str(dados.pop("raiz"))).expanduser()
            for nome, valor in dados.items():
                secao = getattr(cfg, nome, None)
                if is_dataclass(secao) and isinstance(valor, dict):
                    _aplicar(secao, valor, erros, nome)
                else:
                    erros.append(f"{nome}: secao desconhecida (ignorada)")
            break

    if os.environ.get("MORUMBI3D_HOME"):
        cfg.raiz = Path(os.environ["MORUMBI3D_HOME"]).expanduser()
    contato = os.environ.get("MORUMBI3D_CONTATO")
    if contato:
        cfg.rede.contato = contato
        cfg.rede.user_agent = f"Morumbi3D-Curadoria/0.1 (+{contato})"

    cfg.avisos = erros  # type: ignore[attr-defined]
    return cfg
