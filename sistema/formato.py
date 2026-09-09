# -*- coding: utf-8 -*-
"""Numero e data do jeito que se le em Campo Grande.

Desde a primeira tela o sistema escreve `R$ 1120.00` e `2026-09-08`. As duas
sao a convencao de MAQUINA: ponto decimal e ano na frente. Nenhuma das duas
e como o Samir le um valor no meio de uma festa, com o telefone na mao.

Isto fica num modulo, e nao espalhado em `'%.2f'|format(...)` por vinte
templates, por um motivo pratico: com o filtro num lugar so, ha um teste que
varre os templates e reprova o padrao antigo. Sem ele, a proxima tela nasce
com ponto de novo -- foi assim que quatorze telas ficaram erradas.

O fuso tambem e daqui. `agora()` grava em UTC (certo: horario que nao anda
para tras em marco), mas mostrar UTC com cara de hora local erra por quatro
horas -- uma geracao das 22h de terca aparece como quarta-feira. Mato Grosso
do Sul nao tem mais horario de verao desde 2019, entao o deslocamento e fixo.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

TRACO = "—"

# America/Campo_Grande. Tenta o banco de fusos do sistema; onde ele nao
# existir (container enxuto), cai no deslocamento fixo -- que para MS e o
# mesmo o ano inteiro.
try:
    from zoneinfo import ZoneInfo

    AQUI = ZoneInfo("America/Campo_Grande")
except Exception:  # pragma: no cover - depende do tzdata da maquina
    AQUI = timezone(timedelta(hours=-4), "-04")


def numero(valor, casas: int = 2) -> str:
    """1120.5 -> '1.120,50'. Milhar com ponto, decimal com virgula."""
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return TRACO
    inteiro, _, decimal = f"{abs(v):,.{casas}f}".partition(".")
    # O f-string entrega no padrao ingles; a troca e posicional de proposito.
    # `.replace(",", ".")` sozinho transformaria 1,120.50 em 1.120.50.
    inteiro = inteiro.replace(",", ".")
    sinal = "-" if v < 0 else ""
    return f"{sinal}{inteiro},{decimal}" if casas else f"{sinal}{inteiro}"


def dinheiro(valor, vazio: str = TRACO) -> str:
    """R$ com o sinal ANTES do cifrao: -R$ 5,00, e nao R$ -5,00.

    Vazio nao e zero. Produto sem preco de filamento tem custo desconhecido,
    e escrever `R$ 0,00` ali faria a margem parecer de 100%.
    """
    if valor is None or valor == "":
        return vazio
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return vazio
    return f"-R$ {numero(-v)}" if v < 0 else f"R$ {numero(v)}"


def data(valor, vazio: str = TRACO) -> str:
    """'2026-09-08' -> '08/09/2026'. Aceita date, datetime e ISO com hora."""
    d = _para_data(valor)
    return d.strftime("%d/%m/%Y") if d else vazio


def datahora(valor, vazio: str = TRACO) -> str:
    """Carimbo UTC do banco -> '08/09/2026 14:03' no relogio daqui."""
    if isinstance(valor, str) and valor:
        try:
            valor = datetime.fromisoformat(valor)
        except ValueError:
            return vazio
    if not isinstance(valor, datetime):
        return vazio
    # Carimbo antigo, gravado sem fuso, e UTC: era o que `agora()` fazia.
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(AQUI).strftime("%d/%m/%Y %H:%M")


MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro")


def mes_por_extenso(quando: date | None = None) -> str:
    quando = quando or hoje()
    return MESES[quando.month - 1]


def hoje() -> date:
    """A data de hoje NO FUSO DAQUI -- as 21h de MS ja e o dia seguinte em UTC."""
    return datetime.now(AQUI).date()


def _para_data(valor) -> date | None:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str) and valor:
        try:
            return date.fromisoformat(valor[:10])
        except ValueError:
            return None
    return None


FILTROS = {"dinheiro": dinheiro, "numero": numero, "data": data, "datahora": datahora}
