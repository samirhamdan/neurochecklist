#!/usr/bin/env python3
"""Importa clientes da planilha 'Ficha de Reserva' da Morumbi Festas.

Uso:
    python3 ferramentas/importar_clientes_festas.py caminho/ficha_reserva.csv

Agrupa registros por nome (case-insensitive), pega o mais recente de cada.
Pula quem já existe no banco. Idempotente: rodar duas vezes não duplica.
"""
from __future__ import annotations

import csv
import importlib
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

CANAIS_VALIDOS = {"Instagram", "Facebook", "Google", "Indicação", "WhatsApp"}


def ler_planilha(caminho: str) -> list[dict]:
    with open(caminho, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def agrupar_por_nome(linhas: list[dict]) -> dict[str, dict]:
    por_nome: dict[str, dict] = {}
    for l in linhas:
        nome = (l.get("nome") or "").strip()
        if not nome:
            continue
        chave = nome.upper()
        if chave not in por_nome:
            por_nome[chave] = l
        else:
            ts_atual = por_nome[chave].get("Carimbo de data/hora", "")
            ts_novo = l.get("Carimbo de data/hora", "")
            if ts_novo > ts_atual:
                por_nome[chave] = l
    return por_nome


def mapear_canal(texto: str | None) -> str:
    texto = (texto or "").strip()
    for c in CANAIS_VALIDOS:
        if c.lower() in texto.lower():
            return c
    return ""


def montar_observacao(linha: dict) -> str:
    partes = []
    email = (linha.get("EMAIL") or "").strip()
    if email:
        partes.append(f"Email: {email}")
    endereco = (linha.get("ENDEREÇO (COMPLETO)") or "").strip()
    if endereco:
        partes.append(f"End: {endereco}")
    cpf = (linha.get("CPF") or "").strip()
    if cpf and len(cpf) >= 11:
        partes.append(f"CPF: {cpf}")
    return " | ".join(partes)[:200]


def importar(caminho_csv: str) -> None:
    from sistema import dados
    importlib.reload(dados)

    linhas = ler_planilha(caminho_csv)
    agrupados = agrupar_por_nome(linhas)
    existentes = {c["nome"].upper() for c in dados.clientes(False)}

    importados = 0
    pulados = 0
    for chave, l in sorted(agrupados.items()):
        if chave in existentes:
            pulados += 1
            continue

        nome = (l.get("nome") or "").strip()
        telefone = (l.get("TELEFONE C/ DDD") or "").strip()
        canal = mapear_canal(l.get("COMO NOS CONHECEU"))
        obs = montar_observacao(l)

        dados.salvar_cliente({
            "nome": nome,
            "whatsapp": telefone,
            "canal": canal,
            "observacao": obs,
        }, "importacao")
        importados += 1

    print(f"Importados: {importados}")
    print(f"Já existiam (pulados): {pulados}")
    print(f"Total na base agora: {len(dados.clientes(False))}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 ferramentas/importar_clientes_festas.py <arquivo.csv>")
        sys.exit(1)
    caminho = sys.argv[1]
    if not os.path.exists(caminho):
        print(f"Arquivo não encontrado: {caminho}")
        sys.exit(1)
    importar(caminho)
