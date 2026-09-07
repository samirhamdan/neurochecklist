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

CREATE TABLE IF NOT EXISTS filamentos (
    id         INTEGER PRIMARY KEY,
    nome       TEXT NOT NULL,
    marca      TEXT NOT NULL DEFAULT '',
    tipo       TEXT NOT NULL DEFAULT 'PLA',
    cor        TEXT NOT NULL,
    gramas     REAL NOT NULL DEFAULT 0,
    minimo     REAL NOT NULL DEFAULT 300,
    preco_kg   REAL,
    ativo      INTEGER NOT NULL DEFAULT 1,
    criado_em  TEXT NOT NULL,
    criado_por TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_filamentos_cor ON filamentos (cor, ativo);

CREATE TABLE IF NOT EXISTS insumos (
    id         INTEGER PRIMARY KEY,
    nome       TEXT NOT NULL,
    unidade    TEXT NOT NULL DEFAULT 'un',
    quantidade REAL NOT NULL DEFAULT 0,
    minimo     REAL NOT NULL DEFAULT 0,
    valor_unit REAL NOT NULL DEFAULT 0,
    descricao  TEXT NOT NULL DEFAULT '',
    ativo      INTEGER NOT NULL DEFAULT 1,
    criado_em  TEXT NOT NULL,
    criado_por TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS produtos (
    id           INTEGER PRIMARY KEY,
    sku          TEXT UNIQUE,
    nome         TEXT NOT NULL,
    categoria    TEXT NOT NULL DEFAULT '',
    gramas       REAL,
    horas        REAL,
    caixa_x      REAL,
    caixa_y      REAL,
    caixa_z      REAL,
    minutos      REAL,
    filamento_id INTEGER REFERENCES filamentos (id),
    arquivo      TEXT NOT NULL DEFAULT '',
    malha_ok     INTEGER,
    malha_nota   INTEGER,
    preco        REAL,
    observacao   TEXT NOT NULL DEFAULT '',
    ativo        INTEGER NOT NULL DEFAULT 1,
    criado_em    TEXT NOT NULL,
    criado_por   TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS produto_insumos (
    produto_id INTEGER NOT NULL REFERENCES produtos (id) ON DELETE CASCADE,
    insumo_id  INTEGER NOT NULL REFERENCES insumos (id),
    quantidade REAL NOT NULL DEFAULT 1,
    PRIMARY KEY (produto_id, insumo_id)
);

CREATE TABLE IF NOT EXISTS parametros (
    chave  TEXT PRIMARY KEY,
    valor  REAL NOT NULL
);
"""

# A regra comercial que o gerador de letreiros usa na tela, todo dia:
#   preco = arredonda_para_cima_5(piso + gramas * por_grama)
# Ela fica aqui, e nao so no JavaScript, para o cadastro de produto, a loja
# e o gerador darem o MESMO preco para a mesma peca. Dois precos para a
# mesma coisa e a origem classica de numero que nao bate.
PADROES = {
    "piso": 18.0,
    "por_grama": 0.60,
    # Duas linhas de tempo, nao uma. A impressora trabalha sozinha 6 horas;
    # as maos do Samir entram por minutos, antes e depois. Cobrar a hora
    # dele pelas horas DA MAQUINA fazia todo o catalogo dar prejuizo.
    "custo_hora_maquina": 2.39,   # R$ 6.000 / 3.000 h + energia + manutencao
    "valor_hora_pessoa": 25.00,   # o que a hora do Samir vale
    "minutos_acabamento": 30.0,   # padrao por peca; o produto pode ter o seu
    "taxa_falha": 0.10,
}

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
    _migrar(conn)
    return conn


def _migrar(conn: sqlite3.Connection) -> None:
    """O que CREATE TABLE IF NOT EXISTS nao resolve.

    Roda a cada conexao, entao cada passo confere o estado antes de agir.
    """
    tabelas = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'")}

    # O estoque era uma linha por COR. Virou uma linha por ROLO: PLA Preto e
    # PETG Preto sao filamentos diferentes com a mesma cor, e o custo de cada
    # um e outro. O DROP no fim e o que torna esta migracao unica.
    if "filamento" in tabelas:
        conn.execute(
            "INSERT INTO filamentos (nome, tipo, cor, gramas, minimo, criado_em, criado_por)"
            " SELECT 'PLA ' || cor, 'PLA', cor, gramas, minimo, ?, 'migracao' FROM filamento",
            (agora(),))
        conn.execute("DROP TABLE filamento")

    colunas = {r[1] for r in conn.execute("PRAGMA table_info(produtos)")}
    if "minutos" not in colunas:
        conn.execute("ALTER TABLE produtos ADD COLUMN minutos REAL")

    # A primeira versao gravou custo_hora_maquina = 3,50, que era chute meu e
    # misturava maquina com mao de obra. So corrige se ainda estiver no valor
    # antigo -- se alguem ja ajustou, a escolha da pessoa vale mais.
    antigo = conn.execute(
        "SELECT valor FROM parametros WHERE chave = 'custo_hora_maquina'").fetchone()
    if antigo and abs(antigo["valor"] - 3.50) < 1e-9:
        conn.execute("UPDATE parametros SET valor = ? WHERE chave = 'custo_hora_maquina'",
                     (PADROES["custo_hora_maquina"],))

    faltando = [(c, v) for c, v in PADROES.items() if not conn.execute(
        "SELECT 1 FROM parametros WHERE chave = ?", (c,)).fetchone()]
    if faltando:
        conn.executemany("INSERT INTO parametros (chave, valor) VALUES (?, ?)", faltando)
    conn.commit()


def parametros() -> dict[str, float]:
    with conectar() as conn:
        linhas = conn.execute("SELECT chave, valor FROM parametros").fetchall()
    valores = dict(PADROES)
    valores.update({l["chave"]: l["valor"] for l in linhas})
    return valores


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
            "SELECT * FROM filamentos WHERE ativo = 1"
            " ORDER BY gramas <= minimo DESC, cor, nome"
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


# ---------------------------------------------------------------- cadastros
#
# Tres cadastros com a mesma forma: listar, ler um, salvar. Ficam explicitos,
# um por um, em vez de um CRUD generico -- sao poucos e cada um tem regra
# propria, e generico aqui esconderia essas regras.

def _limpo(valor, padrao=""):
    return (valor or padrao).strip() if isinstance(valor, str) else (valor if valor is not None else padrao)


def _numero(valor, padrao=0.0):
    try:
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return padrao


def filamentos(so_ativos: bool = True) -> list[dict]:
    with conectar() as conn:
        onde = "WHERE ativo = 1" if so_ativos else ""
        return [dict(l) for l in conn.execute(
            f"SELECT * FROM filamentos {onde} ORDER BY gramas <= minimo DESC, cor, nome")]


def filamento(id_: int) -> dict | None:
    with conectar() as conn:
        linha = conn.execute("SELECT * FROM filamentos WHERE id = ?", (id_,)).fetchone()
    return dict(linha) if linha else None


def campos_filamento(dados: dict) -> dict:
    """Converte o que veio do formulario em campos tipados.

    Existe separado de salvar_ para o caminho de ERRO poder redesenhar o
    formulario com os mesmos valores ja convertidos. Redesenhar com o
    request.form cru quebra: la tudo e texto, e campo que o usuario nao
    preencheu nem existe -- o template pedia round() de coisa nenhuma.
    """
    return dict(
        nome=_limpo(dados.get("nome")),
        marca=_limpo(dados.get("marca")),
        tipo=_limpo(dados.get("tipo"), "PLA"),
        cor=_limpo(dados.get("cor")),
        gramas=_numero(dados.get("gramas")),
        minimo=_numero(dados.get("minimo"), 300.0),
        preco_kg=_numero(dados.get("preco_kg")) or None,
        ativo=1 if dados.get("ativo", "1") in (1, "1", True, "on") else 0,
    )


def salvar_filamento(dados: dict, autor: str, id_: int | None = None) -> int:
    campos = campos_filamento(dados)
    if not campos["nome"] or campos["cor"] not in CORES:
        raise ValueError("filamento precisa de nome e de uma das cores do catalogo")
    with conectar() as conn:
        if id_:
            conn.execute(
                "UPDATE filamentos SET nome=:nome, marca=:marca, tipo=:tipo, cor=:cor,"
                " gramas=:gramas, minimo=:minimo, preco_kg=:preco_kg, ativo=:ativo"
                " WHERE id=:id", {**campos, "id": id_})
            conn.commit()
            return id_
        cur = conn.execute(
            "INSERT INTO filamentos (nome, marca, tipo, cor, gramas, minimo, preco_kg,"
            " ativo, criado_em, criado_por) VALUES (:nome, :marca, :tipo, :cor, :gramas,"
            " :minimo, :preco_kg, :ativo, :criado_em, :criado_por)",
            {**campos, "criado_em": agora(), "criado_por": autor})
        conn.commit()
        return int(cur.lastrowid)


def insumos(so_ativos: bool = True) -> list[dict]:
    with conectar() as conn:
        onde = "WHERE ativo = 1" if so_ativos else ""
        return [dict(l) for l in conn.execute(
            f"SELECT * FROM insumos {onde} ORDER BY quantidade <= minimo DESC, nome")]


def insumo(id_: int) -> dict | None:
    with conectar() as conn:
        linha = conn.execute("SELECT * FROM insumos WHERE id = ?", (id_,)).fetchone()
    return dict(linha) if linha else None


def campos_insumo(dados: dict) -> dict:
    return dict(
        nome=_limpo(dados.get("nome")),
        unidade=_limpo(dados.get("unidade"), "un"),
        quantidade=_numero(dados.get("quantidade")),
        minimo=_numero(dados.get("minimo")),
        valor_unit=_numero(dados.get("valor_unit")),
        descricao=_limpo(dados.get("descricao")),
        ativo=1 if dados.get("ativo", "1") in (1, "1", True, "on") else 0,
    )


def salvar_insumo(dados: dict, autor: str, id_: int | None = None) -> int:
    campos = campos_insumo(dados)
    if not campos["nome"]:
        raise ValueError("insumo precisa de nome")
    with conectar() as conn:
        if id_:
            conn.execute(
                "UPDATE insumos SET nome=:nome, unidade=:unidade, quantidade=:quantidade,"
                " minimo=:minimo, valor_unit=:valor_unit, descricao=:descricao, ativo=:ativo"
                " WHERE id=:id", {**campos, "id": id_})
            conn.commit()
            return id_
        cur = conn.execute(
            "INSERT INTO insumos (nome, unidade, quantidade, minimo, valor_unit, descricao,"
            " ativo, criado_em, criado_por) VALUES (:nome, :unidade, :quantidade, :minimo,"
            " :valor_unit, :descricao, :ativo, :criado_em, :criado_por)",
            {**campos, "criado_em": agora(), "criado_por": autor})
        conn.commit()
        return int(cur.lastrowid)


def produtos(so_ativos: bool = True) -> list[dict]:
    onde = "WHERE p.ativo = 1" if so_ativos else ""
    with conectar() as conn:
        linhas = conn.execute(
            "SELECT p.*, f.nome AS filamento_nome, f.cor AS filamento_cor,"
            " f.preco_kg AS filamento_preco_kg"
            " FROM produtos p LEFT JOIN filamentos f ON f.id = p.filamento_id"
            f" {onde} ORDER BY p.nome").fetchall()
    return [dict(l) for l in linhas]


def produto(id_: int) -> dict | None:
    with conectar() as conn:
        linha = conn.execute(
            "SELECT p.*, f.nome AS filamento_nome, f.cor AS filamento_cor,"
            " f.preco_kg AS filamento_preco_kg"
            " FROM produtos p LEFT JOIN filamentos f ON f.id = p.filamento_id"
            " WHERE p.id = ?", (id_,)).fetchone()
        if not linha:
            return None
        vinculos = conn.execute(
            "SELECT i.id, i.nome, i.unidade, i.valor_unit, pi.quantidade"
            " FROM produto_insumos pi JOIN insumos i ON i.id = pi.insumo_id"
            " WHERE pi.produto_id = ? ORDER BY i.nome", (id_,)).fetchall()
    dados = dict(linha)
    dados["insumos"] = [dict(v) for v in vinculos]
    return dados


def campos_produto(dados: dict) -> dict:
    return dict(
        sku=_limpo(dados.get("sku")) or None,
        nome=_limpo(dados.get("nome")),
        categoria=_limpo(dados.get("categoria")),
        gramas=_numero(dados.get("gramas")) or None,
        horas=_numero(dados.get("horas")) or None,
        caixa_x=_numero(dados.get("caixa_x")) or None,
        caixa_y=_numero(dados.get("caixa_y")) or None,
        caixa_z=_numero(dados.get("caixa_z")) or None,
        minutos=_numero(dados.get("minutos")) if _limpo(dados.get("minutos")) else None,
        filamento_id=int(dados["filamento_id"]) if _limpo(dados.get("filamento_id")) else None,
        arquivo=_limpo(dados.get("arquivo")),
        malha_ok=int(dados["malha_ok"]) if dados.get("malha_ok") not in (None, "") else None,
        malha_nota=int(_numero(dados.get("malha_nota"))) if _limpo(dados.get("malha_nota")) else None,
        preco=_numero(dados.get("preco")) or None,
        observacao=_limpo(dados.get("observacao")),
        ativo=1 if dados.get("ativo", "1") in (1, "1", True, "on") else 0,
    )


def salvar_produto(dados: dict, autor: str, id_: int | None = None,
                   vinculos: list[tuple[int, float]] | None = None) -> int:
    campos = campos_produto(dados)
    if not campos["nome"]:
        raise ValueError("produto precisa de nome")
    colunas = ", ".join(f"{c}=:{c}" for c in campos)
    with conectar() as conn:
        if id_:
            conn.execute(f"UPDATE produtos SET {colunas} WHERE id=:id", {**campos, "id": id_})
        else:
            nomes = ", ".join(campos)
            marcas = ", ".join(f":{c}" for c in campos)
            cur = conn.execute(
                f"INSERT INTO produtos ({nomes}, criado_em, criado_por)"
                f" VALUES ({marcas}, :criado_em, :criado_por)",
                {**campos, "criado_em": agora(), "criado_por": autor})
            id_ = int(cur.lastrowid)
        if vinculos is not None:
            conn.execute("DELETE FROM produto_insumos WHERE produto_id = ?", (id_,))
            conn.executemany(
                "INSERT INTO produto_insumos (produto_id, insumo_id, quantidade)"
                " VALUES (?, ?, ?)", [(id_, i, q) for i, q in vinculos if q > 0])
        conn.commit()
    return id_
