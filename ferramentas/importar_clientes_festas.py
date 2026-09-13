#!/usr/bin/env python3
"""Importa clientes da planilha 'Ficha de Reserva' da Morumbi Festas.

Uso:
    python3 ferramentas/importar_clientes_festas.py caminho/ficha_reserva.csv

Agrupa registros por nome (case-insensitive), pega o mais recente de cada.
Pula quem já existe no banco. Idempotente: rodar duas vezes não duplica.

Campos mapeados:
    nome           -> nome
    TELEFONE C/ DDD -> whatsapp
    EMAIL          -> email
    CPF            -> cpf
    ENDEREÇO       -> endereco
    COMO NOS CONHECEU -> canal
    Cada linha     -> entrada no histórico (kit, data, pagamento, status)
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


def agrupar_por_nome(linhas: list[dict]) -> dict[str, list[dict]]:
    """Agrupa todas as linhas de cada nome (case-insensitive)."""
    por_nome: dict[str, list[dict]] = {}
    for l in linhas:
        nome = (l.get("nome") or "").strip()
        if not nome:
            continue
        chave = nome.upper()
        por_nome.setdefault(chave, []).append(l)
    return por_nome


def mapear_canal(texto: str | None) -> str:
    texto = (texto or "").strip()
    for c in CANAIS_VALIDOS:
        if c.lower() in texto.lower():
            return c
    return ""


def montar_descricao_historico(linha: dict) -> str:
    partes = []
    kit = (linha.get("MEU KIT ESCOLHIDO") or "").strip()
    if kit:
        partes.append(kit)
    pagamento = (linha.get("FORMA DE PAGAMENTO") or "").strip()
    if pagamento:
        partes.append(pagamento)
    status = (linha.get("STATUS") or "").strip()
    if status:
        partes.append(status)
    return " — ".join(partes) or "Reserva"


def extrair_data(linha: dict) -> str:
    """Tenta montar uma data ISO a partir de mes/ano ou do carimbo."""
    mes = (linha.get("mes") or "").strip()
    ano = (linha.get("ano") or "").strip()
    if mes.isdigit() and ano.isdigit() and int(ano) > 2000:
        return f"{int(ano):04d}-{int(mes):02d}-01"
    carimbo = (linha.get("Carimbo de data/hora") or "").strip()
    if len(carimbo) >= 10:
        return carimbo[:10].replace("/", "-")
    return ""


def importar(caminho_csv: str) -> None:
    from sistema import dados
    importlib.reload(dados)

    linhas = ler_planilha(caminho_csv)
    agrupados = agrupar_por_nome(linhas)
    existentes = {c["nome"].upper(): c["id"] for c in dados.clientes(False)}

    importados = 0
    historicos = 0
    pulados = 0
    for chave, registros in sorted(agrupados.items()):
        mais_recente = max(registros,
                          key=lambda r: r.get("Carimbo de data/hora", ""))

        if chave in existentes:
            pulados += 1
            continue

        nome = (mais_recente.get("nome") or "").strip()
        telefone = (mais_recente.get("TELEFONE C/ DDD") or "").strip()
        email = (mais_recente.get("EMAIL") or "").strip()
        cpf = (mais_recente.get("CPF") or "").strip()
        endereco = (mais_recente.get("ENDEREÇO (COMPLETO)") or "").strip()
        canal = mapear_canal(mais_recente.get("COMO NOS CONHECEU"))

        cliente_id = dados.salvar_cliente({
            "nome": nome,
            "whatsapp": telefone,
            "email": email,
            "cpf": cpf,
            "endereco": endereco,
            "canal": canal,
        }, "importacao")
        importados += 1

        for reg in sorted(registros,
                          key=lambda r: r.get("Carimbo de data/hora", "")):
            descricao = montar_descricao_historico(reg)
            data = extrair_data(reg)
            dados.salvar_historico(cliente_id,
                                  {"data": data, "descricao": descricao},
                                  "importacao")
            historicos += 1

    print(f"Importados: {importados}")
    print(f"Históricos criados: {historicos}")
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
