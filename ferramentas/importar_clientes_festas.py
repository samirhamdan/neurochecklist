#!/usr/bin/env python3
"""Importa clientes da planilha 'Ficha de Reserva' da Morumbi Festas.

Uso:
    python3 ferramentas/importar_clientes_festas.py caminho/ficha_reserva.csv

Desduplicação por NOME, CPF e CELULAR: se qualquer um bate, é a
mesma pessoa. Idempotente: rodar duas vezes não duplica.

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
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

CANAIS_VALIDOS = {"Instagram", "Facebook", "Google", "Indicação", "WhatsApp"}


def ler_planilha(caminho: str) -> list[dict]:
    with open(caminho, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _so_digitos(texto: str | None) -> str:
    return re.sub(r"\D", "", texto or "")


def agrupar_clientes(linhas: list[dict]) -> list[list[dict]]:
    """Agrupa linhas da mesma pessoa por nome, CPF ou celular.

    Se duas linhas compartilham qualquer um dos três identificadores
    (não vazio), são tratadas como a mesma pessoa — mesmo que os nomes
    sejam ligeiramente diferentes.
    """
    chave_para_grupo: dict[str, int] = {}
    grupos: dict[int, list[dict]] = {}
    proximo = 0

    for linha in linhas:
        nome = (linha.get("nome") or "").strip()
        if not nome:
            continue

        chaves = []
        chave_nome = f"n:{nome.upper()}"
        chaves.append(chave_nome)

        cpf = _so_digitos(linha.get("CPF"))
        if len(cpf) >= 11:
            chaves.append(f"c:{cpf}")

        tel = _so_digitos(linha.get("TELEFONE C/ DDD"))
        if len(tel) >= 10:
            chaves.append(f"t:{tel}")

        encontrados = set()
        for ch in chaves:
            if ch in chave_para_grupo:
                encontrados.add(chave_para_grupo[ch])

        if not encontrados:
            gid = proximo
            proximo += 1
            grupos[gid] = []
        elif len(encontrados) == 1:
            gid = encontrados.pop()
        else:
            gid = min(encontrados)
            for antigo in encontrados:
                if antigo != gid:
                    grupos[gid].extend(grupos.pop(antigo))
                    for k, v in list(chave_para_grupo.items()):
                        if v == antigo:
                            chave_para_grupo[k] = gid

        grupos[gid].append(linha)
        for ch in chaves:
            chave_para_grupo[ch] = gid

    return list(grupos.values())


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
    grupos = agrupar_clientes(linhas)

    existentes_nome = {c["nome"].upper(): c["id"] for c in dados.clientes(False)}
    existentes_cpf: dict[str, int] = {}
    existentes_tel: dict[str, int] = {}
    for c in dados.clientes(False):
        cpf = _so_digitos(c.get("cpf"))
        if len(cpf) >= 11:
            existentes_cpf[cpf] = c["id"]
        tel = _so_digitos(c.get("whatsapp"))
        if len(tel) >= 10:
            existentes_tel[tel] = c["id"]

    importados = 0
    historicos = 0
    pulados = 0
    mesclados = 0

    for registros in grupos:
        mais_recente = max(registros,
                          key=lambda r: r.get("Carimbo de data/hora", ""))

        nome = (mais_recente.get("nome") or "").strip()
        cpf = _so_digitos(mais_recente.get("CPF"))
        tel = _so_digitos(mais_recente.get("TELEFONE C/ DDD"))

        cliente_id = (existentes_nome.get(nome.upper())
                      or (existentes_cpf.get(cpf) if len(cpf) >= 11 else None)
                      or (existentes_tel.get(tel) if len(tel) >= 10 else None))

        if cliente_id:
            pulados += 1
            continue

        email = (mais_recente.get("EMAIL") or "").strip()
        cpf_texto = (mais_recente.get("CPF") or "").strip()
        endereco = (mais_recente.get("ENDEREÇO (COMPLETO)") or "").strip()
        canal = mapear_canal(mais_recente.get("COMO NOS CONHECEU"))

        cliente_id = dados.salvar_cliente({
            "nome": nome,
            "whatsapp": (mais_recente.get("TELEFONE C/ DDD") or "").strip(),
            "email": email,
            "cpf": cpf_texto,
            "endereco": endereco,
            "canal": canal,
        }, "importacao")
        importados += 1

        if len(registros) > 1:
            mesclados += len(registros) - 1

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
    print(f"Linhas mescladas (mesmo CPF/celular): {mesclados}")
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
