"""Armazenamento do sistema de gestao.

SQLite num arquivo so, como o catalogo da curadoria. Estado em disco, nunca
em memoria: o gunicorn roda com mais de um worker e cache em memoria faz um
pedido cair num processo e a consulta noutro — a mesma armadilha ja
documentada no CLAUDE.md do gerador de logo.

As telas desta primeira entrega so LEEM daqui. A escrita entra junto com o
cadastro de pedido.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

PASTA = Path(os.environ.get("MORUMBI_DADOS", "/var/lib/morumbi3d"))

ESQUEMA = """
CREATE TABLE IF NOT EXISTS pedidos (
    id          INTEGER PRIMARY KEY,
    cliente     TEXT NOT NULL,
    canal       TEXT NOT NULL DEFAULT '',
    prazo       TEXT,
    valor       REAL,
    status      TEXT NOT NULL DEFAULT 'novo',
    observacao  TEXT DEFAULT '',
    criado_em   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_pedidos_status ON pedidos (status, prazo);

CREATE TABLE IF NOT EXISTS pecas (
    id           INTEGER PRIMARY KEY,
    pedido_id    INTEGER REFERENCES pedidos (id) ON DELETE CASCADE,
    descricao    TEXT NOT NULL,
    produto      TEXT DEFAULT '',
    cor          TEXT DEFAULT '',
    gramas_est   REAL,
    horas_est    REAL,
    gramas_real  REAL,
    horas_real   REAL,
    status       TEXT NOT NULL DEFAULT 'na fila',
    criado_em    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_pecas_status ON pecas (status);

CREATE TABLE IF NOT EXISTS filamento (
    cor        TEXT PRIMARY KEY,
    gramas     REAL NOT NULL DEFAULT 0,
    minimo     REAL NOT NULL DEFAULT 300
);
"""

# Estados de peca que ocupam a impressora, na ordem em que acontecem.
EM_PRODUCAO = ("na fila", "imprimindo", "acabamento")

# As mesmas 11 cores do gerador de letreiros: catalogo e estoque falam a
# mesma lingua, senao a fila agrupa por um nome e o estoque por outro.
CORES = {
    "Branco": "#F2F0EA", "Preto": "#23262A", "Vermelho": "#C0392B",
    "Azul": "#1E63A8", "Rosa": "#E0669A", "Amarelo": "#E8B92E",
    "Verde": "#3E9B54", "Roxo": "#7B52AB", "Laranja": "#E0752A",
    "Dourado": "#C9A227", "Prata": "#B9BEC4",
}


def caminho_banco() -> Path:
    return PASTA / "sistema.sqlite3"


def conectar() -> sqlite3.Connection:
    PASTA.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(caminho_banco())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(ESQUEMA)
    return conn


def _dias_ate(prazo: str | None) -> int | None:
    if not prazo:
        return None
    try:
        return (date.fromisoformat(prazo) - date.today()).days
    except ValueError:
        return None


def resumo() -> dict:
    """Tudo que o painel mostra, numa consulta so por bloco."""

    with conectar() as conn:
        pedidos = conn.execute(
            "SELECT * FROM pedidos WHERE status NOT IN ('entregue', 'cancelado') "
            "ORDER BY prazo IS NULL, prazo, id"
        ).fetchall()

        marcadores = ", ".join("?" for _ in EM_PRODUCAO)
        fila = conn.execute(
            f"SELECT p.*, d.cliente, d.prazo FROM pecas p "
            f"LEFT JOIN pedidos d ON d.id = p.pedido_id "
            f"WHERE p.status IN ({marcadores}) "
            f"ORDER BY d.prazo IS NULL, d.prazo, p.id",
            EM_PRODUCAO,
        ).fetchall()

        filamento = conn.execute(
            "SELECT * FROM filamento ORDER BY gramas <= minimo DESC, cor"
        ).fetchall()

    # Agrupar por cor e o ponto, nao um detalhe de exibicao: cada troca custa
    # 6 g de purga, numero que o gerador de letreiros ja calcula. Ordenar por
    # prazo PRIMEIRO separaria a mesma cor em pedidos diferentes e faria a
    # impressora trocar de filamento a toa.
    #
    # Entao: agrupa por cor, e ordena os GRUPOS pelo prazo mais apertado que
    # cada um contem. A cor com a peca mais urgente vai primeiro, e todas as
    # pecas dela saem de uma vez.
    por_cor: dict[str, list] = {}
    for peca in fila:
        por_cor.setdefault(peca["cor"] or "sem cor", []).append(peca)

    def urgencia(item) -> tuple[int, str]:
        prazos = [p["prazo"] for p in item[1] if p["prazo"]]
        return (0, min(prazos)) if prazos else (1, "")

    por_cor = dict(sorted(por_cor.items(), key=urgencia))
    fila = [peca for grupo in por_cor.values() for peca in grupo]

    horas = sum(p["horas_est"] or 0 for p in fila)
    atrasados = [p for p in pedidos if (_dias_ate(p["prazo"]) or 99) < 0]

    return {
        "pedidos": [dict(p, dias=_dias_ate(p["prazo"])) for p in pedidos],
        "fila": [dict(p) for p in fila],
        "fila_por_cor": {c: [dict(p) for p in v] for c, v in por_cor.items()},
        "horas_fila": horas,
        "trocas_de_cor": max(0, len(por_cor) - 1),
        "purga_g": max(0, len(por_cor) - 1) * 6,
        "filamento": [dict(f) for f in filamento],
        "filamento_baixo": [dict(f) for f in filamento if f["gramas"] <= f["minimo"]],
        "atrasados": [dict(p) for p in atrasados],
        "vazio": not pedidos and not fila and not filamento,
        "cores": CORES,
    }


def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
