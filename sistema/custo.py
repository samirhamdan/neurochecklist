# -*- coding: utf-8 -*-
"""Custo e preco de uma peca.

Sao DUAS contas que respondem perguntas diferentes, e mistura-las e como o
negocio perde dinheiro sem perceber:

  CUSTO   quanto sai do bolso: filamento + hora de maquina + insumos, mais
          uma reserva para a peca que falha e precisa ser reimpressa.
  PRECO   quanto se cobra. E a regra comercial que o gerador de letreiros ja
          usa na tela todo dia: piso + gramas x valor por grama, arredondado
          para cima de 5 em 5 reais.

O preco NAO e o custo vezes um multiplicador. Ele e uma regra de mercado que
o Samir ja calibrou vendendo; o custo e o que diz se essa regra ainda cobre.
A margem entre os dois e a resposta que o painel existe para dar.

O calculo do preco fica aqui, e nao so no JavaScript do gerador, para o
cadastro de produto, a loja e o gerador darem o MESMO numero para a mesma
peca. Dois precos para a mesma coisa e a origem classica de numero que nao
bate no fim do mes.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class Conta:
    gramas: float
    horas: float
    custo_filamento: float
    custo_maquina: float
    custo_insumos: float
    custo_falha: float
    custo: float
    preco: float
    completo: bool = True
    """False quando falta o preco do filamento.

    Sem ele o custo perde o material -- justo a maior parcela. Mostrar o
    numero assim mesmo faria uma peca de 9 g parecer ter 94% de margem, que
    e o tipo de mentira que leva a baixar preco de um produto que da
    prejuizo. Entao a conta se declara incompleta e a tela mostra um traco.
    """

    @property
    def margem(self) -> float:
        """Quantos reais sobram por peca. So faz sentido com o custo inteiro."""
        return round(self.preco - self.custo, 2) if self.completo else 0.0

    @property
    def margem_pct(self) -> float:
        if self.preco <= 0 or not self.completo:
            return 0.0
        return round((self.preco - self.custo) / self.preco * 100, 1)

    @property
    def por_hora(self) -> float:
        """Retorno por hora de impressora ocupada -- o recurso escasso."""
        if self.horas <= 0 or not self.completo:
            return 0.0
        return round((self.preco - self.custo) / self.horas, 2)

    def como_dict(self) -> dict:
        d = {c: getattr(self, c) for c in self.__dataclass_fields__}
        d.update(margem=self.margem, margem_pct=self.margem_pct, por_hora=self.por_hora)
        return d


def preco_comercial(gramas: float, piso: float, por_grama: float) -> float:
    """A regra do balcao: piso + gramas x valor, para cima de 5 em 5.

    Mesma conta do gerador de letreiros:
        Math.ceil((piso + gTotal * pg) / 5) * 5
    """
    if gramas <= 0:
        return 0.0
    return float(math.ceil((piso + gramas * por_grama) / 5.0) * 5.0)


def calcular(gramas: float, horas: float, preco_kg: float | None,
             insumos: float = 0.0, *, param: dict[str, float]) -> Conta:
    """Custo e preco de uma peca ja medida.

    `preco_kg` vem do filamento cadastrado. Sem ele nao da para custear, e o
    custo sai zero -- de proposito, para o cadastro poder avisar em vez de
    inventar um numero que parece certo.
    """
    gramas = max(float(gramas or 0), 0.0)
    horas = max(float(horas or 0), 0.0)

    custo_filamento = gramas / 1000.0 * float(preco_kg) if preco_kg else 0.0
    custo_maquina = horas * float(param["custo_hora_maquina"])
    custo_insumos = max(float(insumos or 0), 0.0)
    # A reserva incide sobre o que se perde ao refugar: filamento e hora de
    # maquina. Insumo de peca refugada costuma sobrar, entao fica de fora.
    custo_falha = (custo_filamento + custo_maquina) * float(param["taxa_falha"])
    custo = custo_filamento + custo_maquina + custo_insumos + custo_falha

    return Conta(
        gramas=round(gramas, 1),
        horas=round(horas, 2),
        custo_filamento=round(custo_filamento, 2),
        custo_maquina=round(custo_maquina, 2),
        custo_insumos=round(custo_insumos, 2),
        custo_falha=round(custo_falha, 2),
        custo=round(custo, 2),
        preco=preco_comercial(gramas, param["piso"], param["por_grama"]),
        completo=bool(preco_kg) or gramas == 0,
    )
