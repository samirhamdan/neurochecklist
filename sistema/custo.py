# -*- coding: utf-8 -*-
"""Custo e preco de uma peca.

Sao DUAS contas que respondem perguntas diferentes, e mistura-las e como o
negocio perde dinheiro sem perceber:

  CUSTO   quanto sai do bolso, e sao DOIS TEMPOS diferentes:
            - a impressora trabalhando SOZINHA, que custa pouco por hora
              (depreciacao + energia + manutencao);
            - as MAOS, que custam caro por hora mas entram por minutos --
              preparar a mesa, tirar a peca, tirar suporte, colar, embalar.
          A primeira versao tinha uma linha so, e multiplicava o valor da
          hora de trabalho pelas horas da MAQUINA. Com a hora a R$ 25, um
          topo de bolo de 5,77 h aparecia com R$ 96 de prejuizo -- cobrado
          por horas em que ninguem estava trabalhando.
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
from dataclasses import dataclass, replace


@dataclass
class Conta:
    gramas: float
    horas: float
    custo_filamento: float
    custo_maquina: float
    custo_pessoa: float
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

    def com_preco(self, preco: float | None) -> "Conta":
        """A mesma conta, com o preco que o produto REALMENTE cobra.

        `Conta.preco` e a sugestao da regra do balcao. Quando o produto tem
        preco digitado, e ele que manda na margem e no retorno por hora --
        senao o painel compara produtos por um preco que ninguem paga.
        """
        return replace(self, preco=float(preco)) if preco else self

    def como_dict(self) -> dict:
        d = {c: getattr(self, c) for c in self.__dataclass_fields__}
        d.update(margem=self.margem, margem_pct=self.margem_pct, por_hora=self.por_hora)
        return d


def conta_de_produto(prod: dict, param: dict[str, float]) -> Conta:
    """A conta de um produto do CADASTRO.

    Existe para que a lista de produtos, a ficha do produto e o grafico do
    painel nao facam a mesma conta de tres jeitos. A lista nao carrega os
    insumos de cada produto (seria uma consulta por linha); a ficha carrega.
    O `or []` cobre os dois sem que a chamada precise saber qual e qual.
    """
    insumos = sum(i["quantidade"] * i["valor_unit"] for i in prod.get("insumos") or [])
    return calcular(prod.get("gramas") or 0, prod.get("horas") or 0,
                    prod.get("filamento_preco_kg"), insumos,
                    prod.get("minutos"), param=param)


def retorno_por_hora(produtos: list[dict], param: dict[str, float]) -> dict:
    """Quanto sobra em cada hora de impressora, produto a produto.

    A impressora e o recurso escasso da casa: e uma so, e a peca que ocupa
    ela doze horas impede todas as outras. Margem por PECA nao responde isso
    -- um chaveiro de R$ 11 de margem em meia hora paga melhor do que um topo
    de bolo de R$ 32 em seis horas, e nenhuma tela mostrava essa comparacao.

    Fica de fora quem nao tem como responder, e cada um por um motivo que a
    tela precisa dizer:

      sem preco de filamento  a conta sai incompleta (`Conta.completo`) --
                              e a maior parcela do custo que esta faltando;
      sem horas medidas       dividir por zero hora nao da numero nenhum.

    Sumir com um produto sem explicar e a origem de "o grafico esta errado".
    """
    dentro, sem_filamento, sem_horas = [], [], []
    for prod in produtos:
        conta = conta_de_produto(prod, param).com_preco(prod.get("preco"))
        if not conta.completo:
            sem_filamento.append(prod)
        elif conta.horas <= 0:
            sem_horas.append(prod)
        else:
            dentro.append({**prod, "conta": conta})
    dentro.sort(key=lambda i: i["conta"].por_hora, reverse=True)

    # A escala sai daqui, e nao do template, por um motivo: um produto que da
    # PREJUIZO por hora tem barra para a esquerda do zero, e onde o zero cai
    # depende de todos os outros. Conta de regra de tres espalhada por Jinja e
    # onde esse tipo de coisa fica errada em silencio.
    valores = [i["conta"].por_hora for i in dentro]
    teto, piso = max(valores + [0.0]), min(valores + [0.0])
    faixa = (teto - piso) or 1.0
    zero = (0.0 - piso) / faixa * 100
    for item in dentro:
        v = item["conta"].por_hora
        item["esquerda"] = round(zero if v >= 0 else (v - piso) / faixa * 100, 2)
        item["largura"] = round(abs(v) / faixa * 100, 2)

    return {"itens": dentro, "sem_filamento": sem_filamento, "sem_horas": sem_horas,
            "de_fora": len(sem_filamento) + len(sem_horas), "zero": round(zero, 2),
            "tem_prejuizo": piso < 0}


def preco_comercial(gramas: float, piso: float, por_grama: float) -> float:
    """A regra do balcao: piso + gramas x valor, para cima de 5 em 5.

    Mesma conta do gerador de letreiros:
        Math.ceil((piso + gTotal * pg) / 5) * 5
    """
    if gramas <= 0:
        return 0.0
    return float(math.ceil((piso + gramas * por_grama) / 5.0) * 5.0)


def preco_por_volume(produto: dict, param: dict[str, float]) -> dict | None:
    """Tabela de preços por volume para um produto.

    Calcula quantas peças cabem na bandeja Bambu Lab A2L (330×320 mm) e retorna
    preços para 1, 8, 32 e 50+ unidades, considerando a diluição do setup.
    """
    if not produto.get("usa_preco_volume"):
        return None

    # Dimensões da peça (em mm)
    dim_x = float(produto.get("dimensao_x") or 100)
    dim_y = float(produto.get("dimensao_y") or 100)

    # Bandeja Bambu Lab A2L: 330 × 320 mm
    bandeja_x, bandeja_y = 330, 320

    # Quantas peças cabem (layout simples, com margem)
    por_linha = max(1, int(bandeja_x / dim_x))
    por_coluna = max(1, int(bandeja_y / dim_y))
    quantidade_por_bandeja = max(1, int(por_linha * por_coluna * 0.8))  # 80% de ocupação

    # Parâmetros de cálculo
    conta_unitaria = conta_de_produto(produto, param).com_preco(produto.get("preco_fixo"))
    custo_prod = conta_unitaria.custo
    margem = float(produto.get("margem_volume") or 150) / 100.0  # 150% = 2.5x
    taxa_setup = float(produto.get("taxa_setup") or 5.0)

    # Cálculo para cada faixa de volume
    faixas = [
        (1, "1 unidade"),
        (quantidade_por_bandeja, f"{quantidade_por_bandeja} unidades (1 bandeja)"),
        (quantidade_por_bandeja * 4, f"{quantidade_por_bandeja * 4} unidades (4 bandejas)"),
        (50, "50+ unidades"),
    ]

    tabela = []
    for quantidade, descricao in faixas:
        custo_total = (custo_prod * quantidade) + taxa_setup
        custo_unitario = custo_total / quantidade
        preco_unitario = round(custo_unitario * margem, 2)

        # Calcular retorno por hora (usando as horas do produto)
        horas_totais = (produto.get("horas") or 0) * quantidade
        retorno_hora = round((preco_unitario - custo_unitario) / (produto.get("horas") or 1), 2) if horas_totais > 0 else 0

        tabela.append({
            "quantidade": quantidade,
            "descricao": descricao,
            "custo_unitario": round(custo_unitario, 2),
            "preco_unitario": preco_unitario,
            "retorno_hora": retorno_hora,
        })

    return {
        "quantidade_por_bandeja": quantidade_por_bandeja,
        "tabela": tabela,
    }


def calcular(gramas: float, horas: float, preco_kg: float | None,
             insumos: float = 0.0, minutos: float | None = None, *,
             param: dict[str, float]) -> Conta:
    """Custo e preco de uma peca ja medida.

    `preco_kg` vem do filamento cadastrado. Sem ele nao da para custear, e o
    custo sai zero -- de proposito, para o cadastro poder avisar em vez de
    inventar um numero que parece certo.
    """
    gramas = max(float(gramas or 0), 0.0)
    horas = max(float(horas or 0), 0.0)

    custo_filamento = gramas / 1000.0 * float(preco_kg) if preco_kg else 0.0
    custo_maquina = horas * float(param["custo_hora_maquina"])
    if minutos is None:
        minutos = param["minutos_acabamento"]
    custo_pessoa = max(float(minutos), 0.0) / 60.0 * float(param["valor_hora_pessoa"])
    custo_insumos = max(float(insumos or 0), 0.0)
    # A reserva incide sobre o que se perde ao refugar: filamento, hora de
    # maquina e o acabamento que foi feito na peca perdida. Insumo de peca
    # refugada costuma sobrar, entao fica de fora.
    custo_falha = (custo_filamento + custo_maquina + custo_pessoa) * float(param["taxa_falha"])
    custo = custo_filamento + custo_maquina + custo_pessoa + custo_insumos + custo_falha

    return Conta(
        gramas=round(gramas, 1),
        horas=round(horas, 2),
        custo_filamento=round(custo_filamento, 2),
        custo_maquina=round(custo_maquina, 2),
        custo_pessoa=round(custo_pessoa, 2),
        custo_insumos=round(custo_insumos, 2),
        custo_falha=round(custo_falha, 2),
        custo=round(custo, 2),
        preco=preco_comercial(gramas, param["piso"], param["por_grama"]),
        completo=bool(preco_kg) or gramas == 0,
    )
