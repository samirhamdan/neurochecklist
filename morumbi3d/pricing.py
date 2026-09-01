"""Custo e preco sugerido: material + maquina + margem.

Os coeficientes vem de ``Config.custo`` (editaveis em ``morumbi3d.toml``).
O objetivo nao e substituir o fatiador, e sim dar ordem de grandeza antes de
gastar tempo com o modelo — se o custo ja inviabiliza o produto, nem precisa
baixar o arquivo.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict

from .config import Config
from .mesh import RelatorioMalha


@dataclass
class Orcamento:
    material_g: float = 0.0
    tempo_h: float = 0.0
    custo_material: float = 0.0
    custo_maquina: float = 0.0
    custo_falha: float = 0.0
    custo_fixo: float = 0.0
    custo_total: float = 0.0
    preco_sugerido: float = 0.0
    margem_reais: float = 0.0

    def resumo(self) -> str:
        return (
            f"custo R$ {self.custo_total:.2f} | preco sugerido R$ "
            f"{self.preco_sugerido:.2f} | margem R$ {self.margem_reais:.2f} "
            f"({self.material_g:.0f} g, {self.tempo_h:.1f} h)"
        )

    def como_dict(self) -> dict:
        return asdict(self)


def _arredondar_comercial(valor: float) -> float:
    """Sobe para o proximo final .90 (12,34 -> 12,90; 37,42 -> 39,90)."""

    if valor <= 0:
        return 0.0
    if valor < 20:
        base = math.ceil(valor)
        return round(base - 0.10 if base - 0.10 >= valor else base + 0.90, 2)
    base = math.ceil(valor / 5.0) * 5.0
    if base - 0.10 < valor:
        base += 5.0
    return round(base - 0.10, 2)


def orcar(relatorio: RelatorioMalha, cfg: Config, quantidade: int = 1) -> Orcamento:
    """Aplica a formula de custo sobre o resultado da analise de malha."""

    c = cfg.custo
    material_g = relatorio.material_g * quantidade
    tempo_h = relatorio.tempo_h * quantidade

    custo_material = material_g / 1000.0 * c.preco_filamento_kg
    custo_maquina = tempo_h * c.custo_hora_maquina
    custo_falha = (custo_material + custo_maquina) * c.taxa_falha
    custo_fixo = c.custo_fixo_por_peca * quantidade
    custo_total = custo_material + custo_maquina + custo_falha + custo_fixo
    preco = _arredondar_comercial(custo_total * c.multiplicador_margem)

    return Orcamento(
        material_g=round(material_g, 1),
        tempo_h=round(tempo_h, 2),
        custo_material=round(custo_material, 2),
        custo_maquina=round(custo_maquina, 2),
        custo_falha=round(custo_falha, 2),
        custo_fixo=round(custo_fixo, 2),
        custo_total=round(custo_total, 2),
        preco_sugerido=preco,
        margem_reais=round(preco - custo_total, 2),
    )
