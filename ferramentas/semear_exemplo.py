#!/usr/bin/env python3
"""Enche o sistema com pedidos de EXEMPLO, para ver o painel funcionando.

Serve para conhecer as telas antes de existir movimento real. Nao use no
banco de producao: os nomes sao inventados e vao poluir o historico que o
laco de custo depende.

    MORUMBI_DADOS=/tmp/demo python3 ferramentas/semear_exemplo.py
    MORUMBI_DADOS=/tmp/demo python3 ferramentas/semear_exemplo.py --limpar
"""

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sistema.dados import agora, caminho_banco, conectar   # noqa: E402

HOJE = date.today()

PEDIDOS = [
    # cliente, canal, dias ate o prazo, valor, status
    ("Ana Paula Ribeiro", "Instagram", -1, 180.00, "na fila"),
    ("Buffet Estrela",    "Morumbi Festas", 0, 460.00, "imprimindo"),
    ("Carlos Menezes",    "Indicação", 3, 95.00, "novo"),
    ("Escola Girassol",   "WhatsApp", 9, 720.00, "novo"),
]

PECAS = [
    # pedido, descricao, cor, horas
    (1, "Letreiro ANA · 22 cm · clássico", "Rosa", 3.4),
    (2, "Letreiro ESTRELA · 28 cm · magia — corpo", "Azul", 5.2),
    (2, "Letreiro ESTRELA · 28 cm · magia — face", "Branco", 1.6),
    (2, "Luminária LOVE · 60 mm", "Branco", 14.5),
    (3, "Chaveiro personalizado ×6", "Preto", 2.1),
    (4, "Letreiro GIRASSOL · 28 cm", "Amarelo", 6.8),
    (4, "Topo de bolo · formatura", "Branco", 2.9),
]

FILAMENTO = [
    ("Branco", 1850, 300), ("Preto", 920, 300), ("Vermelho", 140, 300),
    ("Azul", 640, 300), ("Rosa", 380, 300), ("Amarelo", 210, 300),
]


def main() -> int:
    limpar = "--limpar" in sys.argv
    with conectar() as conn:
        conn.execute("DELETE FROM pecas")
        conn.execute("DELETE FROM pedidos")
        conn.execute("DELETE FROM filamentos")
        if limpar:
            print(f"Banco esvaziado: {caminho_banco()}")
            return 0

        for i, (cliente, canal, dias, valor, status) in enumerate(PEDIDOS, start=1):
            conn.execute(
                "INSERT INTO pedidos (id, cliente, canal, prazo, valor, status, criado_em)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (i, cliente, canal, (HOJE + timedelta(days=dias)).isoformat(),
                 valor, status, agora()),
            )
        for pedido, descricao, cor, horas in PECAS:
            conn.execute(
                "INSERT INTO pecas (pedido_id, descricao, cor, horas_est, status, criado_em)"
                " VALUES (?, ?, ?, ?, 'na fila', ?)",
                (pedido, descricao, cor, horas, agora()),
            )
        for cor, gramas, minimo in FILAMENTO:
            conn.execute(
                "INSERT INTO filamentos (nome, tipo, cor, gramas, minimo, preco_kg,"
                " criado_em, criado_por)"
                " VALUES (?, 'PLA', ?, ?, ?, 120.0, ?, 'exemplo')",
                (f"PLA {cor}", cor, gramas, minimo, agora()),
            )

    print(f"{len(PEDIDOS)} pedidos e {len(PECAS)} pecas de EXEMPLO em {caminho_banco()}")
    print("Para esvaziar:  python3 ferramentas/semear_exemplo.py --limpar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
