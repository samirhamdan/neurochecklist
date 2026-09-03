"""Gerador de letra caixa: SVG entra, STL imprimivel sai.

Fluxo completo em ``gerar_de_svg``:

1. le o SVG e monta as faces (contorno + contra-formas);
2. escala para a altura pedida;
3. monta o solido — caixa oca com face, parede e fundo aberto, ou macica;
4. aplica chanfro e furos de fixacao;
5. corta em pedacos se a peca nao couber na mesa;
6. CONFERE cada pedaco no analisador de malha antes de gravar;
7. grava os STL e devolve custo e tempo estimados.

O passo 6 e o que separa isto de um conversor qualquer: nada e gravado sem
antes responder "esta malha e fechada e cabe na impressora?".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..config import Config
from ..mesh import RelatorioMalha, analisar_triangulos
from ..pricing import Orcamento, orcar
from .cortar import cortar_para_caber
from .geom2d import Face, Ponto, montar_faces, simplificar
from .solid import (
    GeometriaInvalida, Letra, escalar_para_altura, escrever_stl, gerar, medidas,
)
from .svg import carregar_svg

__all__ = [
    "Face", "GeometriaInvalida", "ResultadoLetra", "gerar_de_svg", "carregar_faces",
]

LIMITE_CONFIAVEL_DE_PECAS = 12
"""Acima disso o cortador comeca a produzir peca aberta (ver o README)."""


@dataclass
class Pedaco:
    nome: str
    arquivo: Path
    relatorio: RelatorioMalha
    orcamento: Orcamento


@dataclass
class ResultadoLetra:
    pedacos: list[Pedaco] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    macica: bool = False
    furos: list[Ponto] = field(default_factory=list)
    largura_mm: float = 0.0
    altura_mm: float = 0.0
    profundidade_mm: float = 0.0

    @property
    def material_g(self) -> float:
        return sum(p.relatorio.material_g for p in self.pedacos)

    @property
    def tempo_h(self) -> float:
        return sum(p.relatorio.tempo_h for p in self.pedacos)

    @property
    def custo(self) -> float:
        return sum(p.orcamento.custo_total for p in self.pedacos)

    @property
    def preco_sugerido(self) -> float:
        return sum(p.orcamento.preco_sugerido for p in self.pedacos)

    @property
    def tudo_fechado(self) -> bool:
        return all(p.relatorio.fechada for p in self.pedacos)

    def resumo(self) -> str:
        return (
            f"{self.largura_mm:.0f} x {self.altura_mm:.0f} x {self.profundidade_mm:.0f} mm | "
            f"{len(self.pedacos)} peca(s) | {'macica' if self.macica else 'caixa'} | "
            f"~{self.material_g:.0f} g | ~{self.tempo_h:.1f} h"
        )


def carregar_faces(
    caminho_svg: Path | str, tolerancia: float = 0.1, simplificacao: float = 0.03
) -> list[Face]:
    """Le o SVG e devolve as faces prontas (contornos + contra-formas)."""

    contornos = carregar_svg(caminho_svg, tolerancia)
    if not contornos:
        raise GeometriaInvalida(
            f"nenhum contorno fechado em {caminho_svg}. Converta o texto em "
            "curvas antes de exportar: fonte viva e traco (stroke) nao viram "
            "material."
        )
    if simplificacao > 0:
        contornos = [simplificar(c, simplificacao) for c in contornos]
    faces = montar_faces(contornos)
    if not faces:
        raise GeometriaInvalida("os contornos do SVG nao formam area preenchida")
    return faces


def gerar_de_svg(
    caminho_svg: Path | str,
    cfg: Config,
    *,
    altura: float = 150.0,
    profundidade: float = 25.0,
    parede: float = 2.4,
    frente: float = 2.0,
    chanfro: float = 0.0,
    macica: bool = False,
    furos: list[Ponto] | None = None,
    furos_auto: bool = False,
    diametro_furo: float = 4.0,
    espacamento_furo: float = 60.0,
    cortar_para_mesa: bool = True,
    tolerancia: float = 0.1,
    simplificacao: float = 0.03,
    saida: Path | str | None = None,
    nome: str | None = None,
) -> ResultadoLetra:
    """Gera os STL da letra a partir de um SVG. Ver o modulo para o fluxo."""

    caminho_svg = Path(caminho_svg)
    nome = nome or caminho_svg.stem
    destino = Path(saida) if saida else (cfg.raiz / "letras" / nome)
    destino.mkdir(parents=True, exist_ok=True)

    faces = escalar_para_altura(
        carregar_faces(caminho_svg, tolerancia, simplificacao), altura
    )
    x0, y0, x1, y1 = medidas(faces)
    resultado = ResultadoLetra(
        largura_mm=round(x1 - x0, 2),
        altura_mm=round(y1 - y0, 2),
        profundidade_mm=profundidade,
    )

    letra: Letra = gerar(
        faces,
        profundidade=profundidade,
        parede=parede,
        frente=frente,
        chanfro=chanfro,
        macica=macica,
        furos=list(furos or []),
        furos_auto=furos_auto,
        espacamento_furo=espacamento_furo,
        diametro_furo=diametro_furo,
    )
    resultado.avisos += letra.avisos
    resultado.macica = letra.macica
    resultado.furos = letra.furos

    mesa_x, mesa_y, _ = cfg.mesa_util
    if cortar_para_mesa:
        partes, avisos_corte = cortar_para_caber(letra.triangulos, mesa_x, mesa_y)
        resultado.avisos += avisos_corte
        if len(partes) > LIMITE_CONFIAVEL_DE_PECAS:
            # Medido: ate ~10 pecas sai 100% limpo; em 30 pecas cai 1; em 124
            # cai a maioria. Melhor dizer isso na cara do que deixar o usuario
            # descobrir no fatiador.
            resultado.avisos.append(
                f"ATENCAO: {len(partes)} pecas. O cortador so e confiavel ate "
                f"cerca de {LIMITE_CONFIAVEL_DE_PECAS}; acima disso muitas pecas "
                "saem com malha aberta. Gere uma letra por vez (um SVG para "
                "cada) ou use --sem-cortar e corte no fatiador."
            )
    else:
        partes = [letra.triangulos]

    for indice, parte in enumerate(partes, start=1):
        rotulo = nome if len(partes) == 1 else f"{nome}-parte{indice}"
        arquivo = destino / f"{rotulo}.stl"
        escrever_stl(parte, arquivo, rotulo)
        relatorio = analisar_triangulos(parte, cfg)
        relatorio.arquivo = str(arquivo)
        relatorio.formato = "stl"
        resultado.pedacos.append(
            Pedaco(
                nome=rotulo,
                arquivo=arquivo,
                relatorio=relatorio,
                orcamento=orcar(relatorio, cfg),
            )
        )
        if not relatorio.fechada:
            resultado.avisos.append(
                f"{rotulo}: malha saiu aberta ({relatorio.arestas_abertas} arestas) "
                "— confira no fatiador antes de imprimir"
            )
        if not relatorio.cabe_na_mesa:
            resultado.avisos.append(
                f"{rotulo}: ainda nao cabe na mesa "
                f"({relatorio.dimensoes_mm[0]:.0f} x {relatorio.dimensoes_mm[1]:.0f} mm)"
            )
    return resultado
