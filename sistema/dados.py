"""Armazenamento do sistema de gestao.

SQLite num arquivo so, como o catalogo da curadoria. Estado em disco, nunca
em memoria: o gunicorn roda com mais de um worker e cache em memoria faz um
pedido cair num processo e a consulta noutro — a mesma armadilha ja
documentada no CLAUDE.md do gerador de logo.

As telas desta primeira entrega so LEEM daqui. A escrita entra junto com o
cadastro de pedido.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import formato

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
    preco_manual REAL,
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
    valor_manual REAL,
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
    dimensao_x   REAL,
    dimensao_y   REAL,
    usa_preco_volume INTEGER NOT NULL DEFAULT 0,
    margem_volume REAL NOT NULL DEFAULT 150,
    taxa_setup   REAL NOT NULL DEFAULT 5.0,
    preco_fixo   REAL,
    criado_em    TEXT NOT NULL,
    criado_por   TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS produto_insumos (
    produto_id INTEGER NOT NULL REFERENCES produtos (id) ON DELETE CASCADE,
    insumo_id  INTEGER NOT NULL REFERENCES insumos (id),
    quantidade REAL NOT NULL DEFAULT 1,
    PRIMARY KEY (produto_id, insumo_id)
);

CREATE TABLE IF NOT EXISTS compras (
    id         INTEGER PRIMARY KEY,
    data       TEXT NOT NULL,
    fornecedor TEXT NOT NULL DEFAULT '',
    nota       TEXT NOT NULL DEFAULT '',
    observacao TEXT NOT NULL DEFAULT '',
    valor      REAL NOT NULL DEFAULT 0,
    criado_em  TEXT NOT NULL,
    criado_por TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_compras_data ON compras (data DESC, id DESC);

CREATE TABLE IF NOT EXISTS compra_itens (
    id         INTEGER PRIMARY KEY,
    compra_id  INTEGER NOT NULL REFERENCES compras (id) ON DELETE CASCADE,
    tipo       TEXT NOT NULL,
    alvo_id    INTEGER NOT NULL,
    quantidade REAL NOT NULL,
    valor      REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_compra_itens ON compra_itens (tipo, alvo_id, compra_id);

CREATE TABLE IF NOT EXISTS movimentos (
    id         INTEGER PRIMARY KEY,
    tipo       TEXT NOT NULL,
    alvo_id    INTEGER NOT NULL,
    quantidade REAL NOT NULL,
    motivo     TEXT NOT NULL,
    peca_id    INTEGER,
    compra_id  INTEGER,
    observacao TEXT NOT NULL DEFAULT '',
    criado_em  TEXT NOT NULL,
    criado_por TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_mov_alvo ON movimentos (tipo, alvo_id, criado_em);
-- Uma baixa de producao por peca, garantida pelo BANCO e nao pelo cuidado
-- de quem escreve a consulta. Mover a peca duas vezes para "imprimindo" nao
-- tem como tirar o filamento duas vezes. Refugo fica de fora do indice de
-- proposito: uma peca pode falhar mais de uma vez.
CREATE UNIQUE INDEX IF NOT EXISTS ix_mov_producao
    ON movimentos (peca_id, tipo, alvo_id)
    WHERE peca_id IS NOT NULL AND motivo = 'producao';

CREATE TABLE IF NOT EXISTS historico (
    id         INTEGER PRIMARY KEY,
    peca_id    INTEGER NOT NULL REFERENCES pecas (id) ON DELETE CASCADE,
    de         TEXT NOT NULL DEFAULT '',
    para       TEXT NOT NULL,
    observacao TEXT NOT NULL DEFAULT '',
    criado_em  TEXT NOT NULL,
    criado_por TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_hist_peca ON historico (peca_id, id);

CREATE TABLE IF NOT EXISTS clientes (
    id         INTEGER PRIMARY KEY,
    nome       TEXT NOT NULL,
    whatsapp   TEXT NOT NULL DEFAULT '',
    canal      TEXT NOT NULL DEFAULT '',
    observacao TEXT NOT NULL DEFAULT '',
    ativo      INTEGER NOT NULL DEFAULT 1,
    criado_em  TEXT NOT NULL,
    criado_por TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_clientes_nome ON clientes (ativo, nome);

CREATE TABLE IF NOT EXISTS canais (
    nome     TEXT PRIMARY KEY,
    comissao REAL NOT NULL DEFAULT 0,
    ativo    INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    tipo TEXT NOT NULL DEFAULT 'topo',         -- qual gerador desenha
    modelo TEXT NOT NULL,
    categoria TEXT NOT NULL DEFAULT '',
    resumo TEXT NOT NULL DEFAULT '',
    campos TEXT NOT NULL DEFAULT 'nome',       -- separados por virgula
    frase TEXT NOT NULL DEFAULT '',
    fonte TEXT NOT NULL DEFAULT 'luckiest',
    forma TEXT NOT NULL DEFAULT '',
    arco REAL NOT NULL DEFAULT 0,
    base INTEGER NOT NULL DEFAULT 1,
    limite_nome INTEGER NOT NULL DEFAULT 12,
    limite_numero INTEGER NOT NULL DEFAULT 2,
    licenca TEXT NOT NULL DEFAULT '',
    preco REAL NOT NULL DEFAULT 0,             -- 0 = calculado pelo peso
    publicado INTEGER NOT NULL DEFAULT 0,      -- §10: em teste ate ser impresso
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL,
    criado_por TEXT NOT NULL DEFAULT ''
);

-- §12: "acompanhar geracoes". Guarda a CONFIGURACAO, e nao o arquivo: o
-- gerador refaz o STL igual a partir dela, e um STL de 3 MB por geracao
-- encheria o disco da VPS em um mes de festa.
--
-- O sku fica como TEXTO, sem chave estrangeira. E de proposito: apagar ou
-- desativar um template nao pode apagar o registro de um pedido antigo que
-- usou ele.
CREATE TABLE IF NOT EXISTS geracoes (
    id INTEGER PRIMARY KEY,
    sku TEXT NOT NULL,
    modelo TEXT NOT NULL DEFAULT '',
    nome TEXT NOT NULL,
    numero TEXT NOT NULL DEFAULT '',
    tamanho INTEGER NOT NULL,
    arquivo TEXT NOT NULL DEFAULT '',
    gramas REAL NOT NULL DEFAULT 0,
    preco REAL NOT NULL DEFAULT 0,
    criado_em TEXT NOT NULL,
    criado_por TEXT NOT NULL DEFAULT ''
);

-- Quais SKUs a semente ja OFERECEU, uma vez cada.
--
-- Nao e "a semente ja rodou": com esse marcador, template novo que eu
-- acrescentasse nunca chegaria a um banco que ja existe -- e a VPS do Samir
-- e um banco que ja existe. Guardando o que ja foi oferecido, template novo
-- chega, e template apagado por ele nao volta.
CREATE TABLE IF NOT EXISTS semente_vista (
    sku TEXT PRIMARY KEY,
    visto_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS parametros (
    chave  TEXT PRIMARY KEY,
    valor  REAL NOT NULL
);

-- Quem assina o orcamento. Uma linha so (id = 1) -- e uma empresa, e uma
-- tabela de uma linha e mais honesta do que uma de chave/valor com dez
-- chaves soltas que ninguem sabe se ainda existem.
CREATE TABLE IF NOT EXISTS empresa (
    id         INTEGER PRIMARY KEY CHECK (id = 1),
    nome       TEXT NOT NULL DEFAULT 'Morumbi 3D',
    documento  TEXT NOT NULL DEFAULT '',
    telefone   TEXT NOT NULL DEFAULT '',
    email      TEXT NOT NULL DEFAULT '',
    endereco   TEXT NOT NULL DEFAULT '',
    site       TEXT NOT NULL DEFAULT '',
    -- Cor do documento. Nasce no azul da marca; o Samir muda se quiser.
    cor        TEXT NOT NULL DEFAULT '#0040F0',
    validade_dias INTEGER NOT NULL DEFAULT 7,
    condicoes  TEXT NOT NULL DEFAULT '',
    atualizado_em TEXT NOT NULL DEFAULT ''
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

# As cinco etapas da peca, no vocabulario do Sistema3D -- que e o que o
# Samir ja usa. O quadro do painel de producao move PECAS por elas.
ETAPAS = ("aguardando", "imprimindo", "montagem", "a entregar", "entregue")

ROTULOS = {
    "aguardando": "Aguardando", "imprimindo": "Em produção",
    "montagem": "Montagem", "a entregar": "À entregar", "entregue": "Entregue",
    "orcamento": "Orçamento", "refugada": "Refugada",
}

# O que cada etapa E, para a coluna vazia poder ensinar em vez de ficar em
# branco. Fica ao lado de ETAPAS de proposito: coluna nova sem convite fica
# vermelha no teste, em vez de nascer muda.
CONVITES = {
    "aguardando": "Peça entra aqui quando um pedido é aprovado. Enquanto for "
                  "orçamento, ela não ocupa a mesa.",
    "imprimindo": "Arraste para cá quando puser na impressora. É a etapa que "
                  "baixa o filamento e o insumo do estoque.",
    "montagem": "Peça que saiu da mesa e ainda precisa de mão: tirar suporte, "
                "colar, lixar, pintar.",
    "a entregar": "Pronta, esperando o cliente. A impressora já está livre — "
                  "por isso estas horas não contam em “na mesa”.",
    "entregue": "Saiu daqui. Marcar o pedido inteiro como entregue move as "
                "peças que faltarem.",
}

# Etapas que ocupam a bancada. "A entregar" ja saiu da impressora, entao a
# fila do painel -- que conta horas e trocas de cor -- para antes dela.
EM_PRODUCAO = ("aguardando", "imprimindo", "montagem")

# Entrar nesta etapa e o que consome filamento e insumo.
ETAPA_QUE_CONSOME = "imprimindo"

# O PEDIDO tem situacao comercial; a PECA tem etapa de producao. Sao coisas
# diferentes e estavam misturadas: o semeador gravava pedido com status
# "imprimindo", que e etapa de peca. Um pedido de 5 pecas tem pecas em
# etapas diferentes ao mesmo tempo -- por isso a etapa nao cabe no pedido.
SITUACOES = ("orcamento", "aprovado", "entregue", "cancelado")
ABERTOS = ("orcamento", "aprovado")

# De onde vem o pedido. Os quatro primeiros sao o balcao e as redes; os tres
# ultimos entram sozinhos, pela loja e pelos marketplaces (sprints 8 e 9).
CANAIS = ("Balcão", "Instagram", "WhatsApp", "Indicação", "Morumbi Festas",
          "Loja", "Shopee", "Mercado Livre")

# As mesmas 11 cores do gerador de letreiros: catalogo e estoque falam a
# mesma lingua, senao a fila agrupa por um nome e o estoque por outro.
CORES = {
    "Branco": "#F2F0EA", "Preto": "#23262A", "Vermelho": "#C0392B",
    "Azul": "#1E63A8", "Rosa": "#E0669A", "Amarelo": "#E8B92E",
    "Verde": "#3E9B54", "Roxo": "#7B52AB", "Laranja": "#E0752A",
    "Dourado": "#C9A227", "Prata": "#B9BEC4",
}


class ErroDeCampo(ValueError):
    """Um erro que sabe DE QUAL campo ele e.

    O topo da pagina diz que algo deu errado; so o campo diz o que. Num
    cadastro de dezessete campos, "produto precisa de nome" la em cima e uma
    caca ao tesouro -- e o campo que falta pode estar fora da parte visivel
    da tela.

    Herda de ValueError de proposito: quem ja tratava ValueError continua
    tratando, e quem quiser o campo pergunta por `.campo`.
    """

    def __init__(self, campo: str, mensagem: str):
        super().__init__(mensagem)
        self.campo = campo


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

    # O pedido nasce sem saber de onde veio. Quatro colunas que um pedido
    # antigo nunca mais teria de onde tirar -- e sem valor_liquido o
    # relatorio de vendas mente, porque a comissao do marketplace sai do
    # bolso do Samir e nao do cliente.
    colunas = {r[1] for r in conn.execute("PRAGMA table_info(pedidos)")}
    for coluna, tipo in (("cliente_id", "INTEGER"), ("id_no_canal", "TEXT"),
                         ("comissao", "REAL"), ("valor_liquido", "REAL"),
                         ("criado_por", "TEXT")):
        if coluna not in colunas:
            conn.execute(f"ALTER TABLE pedidos ADD COLUMN {coluna} {tipo}")

    # QUANDO o pedido foi entregue. `criado_em` diz quando ele ENTROU, que num
    # pedido de festa e ate dois meses antes -- e sem esta coluna o painel nao
    # tem como responder "quanto entregamos neste mes".
    if "entregue_em" not in colunas:
        conn.execute("ALTER TABLE pedidos ADD COLUMN entregue_em TEXT")
        # Pedido ja entregue antes desta coluna: a melhor data disponivel e a
        # do historico, quando a ultima peca dele chegou em "entregue". Quem
        # foi marcado entregue direto na tela do pedido nao tem historico e
        # fica sem data -- e fica FORA do mes, que e melhor do que entrar num
        # mes inventado.
        conn.execute(
            "UPDATE pedidos SET entregue_em = (SELECT MAX(h.criado_em) FROM historico h"
            " JOIN pecas p ON p.id = h.peca_id"
            " WHERE p.pedido_id = pedidos.id AND h.para = 'entregue')"
            " WHERE status = 'entregue'")

    for tabela, coluna in (("filamentos", "preco_manual"), ("insumos", "valor_manual")):
        colunas = {r[1] for r in conn.execute(f"PRAGMA table_info({tabela})")}
        if colunas and coluna not in colunas:
            conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} REAL")
            # O que ja estava la foi digitado a mao: e esse o valor de reserva.
            origem = "preco_kg" if tabela == "filamentos" else "valor_unit"
            conn.execute(f"UPDATE {tabela} SET {coluna} = {origem}")

    colunas = {r[1] for r in conn.execute("PRAGMA table_info(movimentos)")}
    if colunas and "compra_id" not in colunas:
        conn.execute("ALTER TABLE movimentos ADD COLUMN compra_id INTEGER")

    colunas = {r[1] for r in conn.execute("PRAGMA table_info(pecas)")}
    for coluna, tipo in (("produto_id", "INTEGER"), ("quantidade", "REAL"),
                         ("valor_unit", "REAL"), ("criado_por", "TEXT")):
        if coluna not in colunas:
            conn.execute(f"ALTER TABLE pecas ADD COLUMN {coluna} {tipo}")
    conn.execute("UPDATE pecas SET quantidade = 1 WHERE quantidade IS NULL")

    # Situacao de pedido que na verdade era etapa de peca. "novo" virou
    # orcamento; "na fila"/"imprimindo"/"acabamento" eram producao, e
    # producao so acontece em pedido aprovado.
    # Etapas renomeadas para o vocabulario do Samir (o do Sistema3D).
    for antigo, novo in (("na fila", "aguardando"), ("acabamento", "montagem")):
        conn.execute("UPDATE pecas SET status = ? WHERE status = ?", (novo, antigo))

    conn.execute("UPDATE pedidos SET status = 'orcamento' WHERE status = 'novo'")
    conn.execute(
        "UPDATE pedidos SET status = 'aprovado' WHERE status IN"
        " ('na fila', 'imprimindo', 'acabamento', 'aguardando', 'montagem')")

    # O estoque inicial vira o primeiro movimento. Assim o saldo e a soma dos
    # movimentos, sempre -- e da para provar que a coluna `gramas` nao
    # desandou, em vez de torcer para nao ter desandado.
    for tabela, tipo, coluna in (("filamentos", "filamento", "gramas"),
                                 ("insumos", "insumo", "quantidade")):
        sem_inicial = conn.execute(
            f"SELECT id, {coluna} AS q, criado_em, criado_por FROM {tabela} t"
            f" WHERE NOT EXISTS (SELECT 1 FROM movimentos m WHERE m.tipo = ?"
            f" AND m.alvo_id = t.id AND m.motivo = 'inicial')", (tipo,)).fetchall()
        for linha in sem_inicial:
            conn.execute(
                "INSERT INTO movimentos (tipo, alvo_id, quantidade, motivo, criado_em,"
                " criado_por) VALUES (?, ?, ?, 'inicial', ?, ?)",
                (tipo, linha["id"], linha["q"] or 0, linha["criado_em"] or agora(),
                 linha["criado_por"] or "migracao"))

    # Cliente era texto solto no pedido. Vira cadastro, e o texto continua
    # no pedido como historico: se o cliente trocar de nome depois, o pedido
    # antigo tem que continuar dizendo com quem foi feito.
    if not conn.execute("SELECT 1 FROM clientes LIMIT 1").fetchone():
        antigos = conn.execute(
            "SELECT DISTINCT cliente, canal FROM pedidos WHERE cliente <> ''").fetchall()
        for linha in antigos:
            cur = conn.execute(
                "INSERT INTO clientes (nome, canal, criado_em, criado_por)"
                " VALUES (?, ?, ?, 'migracao')",
                (linha["cliente"], linha["canal"] or "", agora()))
            conn.execute("UPDATE pedidos SET cliente_id = ? WHERE cliente = ?",
                         (cur.lastrowid, linha["cliente"]))

    novos = [(c,) for c in CANAIS if not conn.execute(
        "SELECT 1 FROM canais WHERE nome = ?", (c,)).fetchone()]
    if novos:
        # Comissao fica em ZERO ate o Samir informar. As taxas de Shopee e
        # Mercado Livre mudam e variam por categoria: chutar aqui viraria
        # numero errado no relatorio de vendas, que e pior que numero nenhum.
        conn.executemany("INSERT INTO canais (nome, comissao) VALUES (?, 0)", novos)

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

    colunas = {r[1] for r in conn.execute("PRAGMA table_info(templates)")}
    if "tipo" not in colunas:
        # Ate o C4 so havia topo de bolo, entao todo template existente e topo.
        conn.execute("ALTER TABLE templates ADD COLUMN tipo TEXT NOT NULL DEFAULT 'topo'")

    # Desconto em REAIS, e nao em porcentagem: e assim que o desconto e dado
    # no balcao ("faco por 600"), e porcentagem obrigaria a arredondar duas
    # vezes -- uma para achar o valor, outra para escrever no papel.
    colunas = {r[1] for r in conn.execute("PRAGMA table_info(pedidos)")}
    for coluna, tipo in (("desconto", "REAL NOT NULL DEFAULT 0"),
                         ("token", "TEXT"), ("token_expira", "TEXT"),
                         ("aceito_em", "TEXT"), ("aceito_por", "TEXT")):
        if coluna not in colunas:
            conn.execute(f"ALTER TABLE pedidos ADD COLUMN {coluna} {tipo}")
    # Um token vale para UM orcamento. O indice unico e quem garante isso, e
    # nao a funcao que sorteia -- sorteio repetido acontece.
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_pedidos_token"
                 " ON pedidos (token) WHERE token IS NOT NULL")

    colunas = {r[1] for r in conn.execute("PRAGMA table_info(produtos)")}
    for coluna, tipo in (("dimensao_x", "REAL"), ("dimensao_y", "REAL"),
                         ("usa_preco_volume", "INTEGER NOT NULL DEFAULT 0"),
                         ("margem_volume", "REAL NOT NULL DEFAULT 150"),
                         ("taxa_setup", "REAL NOT NULL DEFAULT 5.0"),
                         ("preco_fixo", "REAL")):
        if coluna not in colunas:
            conn.execute(f"ALTER TABLE produtos ADD COLUMN {coluna} {tipo}")

    if not conn.execute("SELECT 1 FROM empresa WHERE id = 1").fetchone():
        conn.execute("INSERT INTO empresa (id, atualizado_em) VALUES (1, ?)", (agora(),))

    _semear_templates(conn)
    conn.commit()


CHAVE_SEMENTE = "semente_templates"
TEMPLATES_INICIAIS = Path(__file__).resolve().parent.parent / "web" / "nucleo" / "templates-iniciais.json"


def _semear_templates(conn: sqlite3.Connection) -> None:
    """Os seis templates que nasceram no C2, agora como DADO.

    Ate o C3 eles moravam dentro de topo.js: acrescentar um template pedia eu
    mexer no codigo, que e exatamente o que o §12 do documento veio resolver.

    Cada SKU e oferecido UMA VEZ, e a tabela `semente_vista` lembra quais ja
    foram. Duas coisas dependem disso, e as duas ja quebraram:

      * por SKU presente na tabela de templates (C3), apagar um template pela
        tela o trazia de volta na proxima conexao -- o Samir apagava, voltava,
        e nada na tela explicava;
      * "a semente ja rodou" (a primeira correcao) resolvia aquilo mas fechava
        a porta: o chaveiro do C4 nunca chegaria a um banco que ja existe, e a
        VPS do Samir e um banco que ja existe.

    Template novo que ELE cria continua sendo pela tela. E o ponto do C3.
    """
    if not TEMPLATES_INICIAIS.exists():
        return
    try:
        iniciais = json.loads(TEMPLATES_INICIAIS.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    # Cada entrada diz de qual sprint veio (`desde`). Num banco que ja existia
    # antes desta tabela, marca como vistos so os que aquele banco JA TINHA
    # recebido -- os do C2. Sem o `desde`, marcar "tudo que esta na semente"
    # fecharia a porta para os do C4, e o chaveiro nunca chegaria na VPS.
    antigo = conn.execute("SELECT 1 FROM parametros WHERE chave = ?",
                          (CHAVE_SEMENTE,)).fetchone()
    if antigo and not conn.execute("SELECT 1 FROM semente_vista").fetchone():
        conn.executemany(
            "INSERT OR IGNORE INTO semente_vista (sku, visto_em) VALUES (?, ?)",
            [(t["sku"], agora()) for t in iniciais if t.get("desde", "C2") <= "C3"])
    conn.execute("INSERT OR IGNORE INTO parametros (chave, valor) VALUES (?, 1)",
                 (CHAVE_SEMENTE,))

    vistos = {r["sku"] for r in conn.execute("SELECT sku FROM semente_vista")}
    tem = {r["sku"] for r in conn.execute("SELECT sku FROM templates")}
    novos = [t for t in iniciais
             if t.get("sku") and t["sku"] not in tem and t["sku"] not in vistos]
    if novos:
        conn.executemany(
            "INSERT OR IGNORE INTO semente_vista (sku, visto_em) VALUES (?, ?)",
            [(t["sku"], agora()) for t in novos])
    for t in novos:
        conn.execute(
            "INSERT INTO templates (sku, tipo, modelo, categoria, resumo, campos, frase,"
            " fonte, forma, arco, base, limite_nome, limite_numero, licenca, preco,"
            " publicado, ativo, criado_em, criado_por) VALUES (:sku, :tipo, :modelo,"
            " :categoria, :resumo, :campos, :frase, :fonte, :forma, :arco, :base,"
            " :limite_nome, :limite_numero, :licenca, :preco, :publicado, :ativo,"
            " :criado_em, 'semente')",
            {**t, "tipo": t.get("tipo", "topo"),
             "campos": ",".join(t.get("campos") or ["nome"]),
             "criado_em": agora()})


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


# ------------------------------------------------- os numeros que o topo mostra
#
# Cada numero do painel sai da MESMA funcao que a tela para onde ele aponta.
# Nao e preciosismo. Um total somado no painel por uma consulta e na tela por
# outra passa a discordar no dia em que uma das duas ganhar um filtro -- e
# quem olha nao tem como saber qual das duas esta certa. Entao a funcao e uma
# so, e recebe a LISTA que a tela ja tem em maos.

def total_do_pedido(pedido_: dict) -> float:
    """O que o cliente PAGA: a soma dos itens menos o desconto.

    Existe porque tres telas e o PDF precisam do mesmo numero. `valor` sozinho
    e a soma dos itens -- o preco de tabela -- e depois de dar 40 reais de
    desconto ele deixa de ser o que entra no caixa.
    """
    return round((pedido_["valor"] or 0) - (pedido_["desconto"] or 0), 2)


def somar_valor(pedidos_: list[dict]) -> float:
    """O quanto vale uma lista de pedidos. Serve ao painel e ao rodape da tabela."""
    return round(sum(total_do_pedido(p) for p in pedidos_), 2)


# `gramas_est` e `horas_est` sao o total da LINHA, e nao de uma unidade: quem
# multiplica e o app ao montar o item do pedido ("peso e tempo sao por peca no
# catalogo; a fila precisa do total"). Por isso somar aqui e somar direto -- e
# por isso a baixa de insumo multiplica e a de filamento nao: o que e por
# unidade la e a quantidade do vinculo produto-insumo.
#
# Ha teste que prende esse contrato (test_producao), porque so a leitura de
# `_baixar` faz a assimetria parecer defeito. Ela nao e.

def horas_na_mesa(fila: list[dict]) -> float:
    """Horas previstas do que esta na bancada. A entregar ja saiu da impressora."""
    return round(sum(p["horas_est"] or 0 for p in fila), 2)


def gramas_na_fila(pecas: list[dict]) -> float:
    """Quanto filamento uma pilha de pecas vai comer."""
    return round(sum(p["gramas_est"] or 0 for p in pecas), 1)


def parado_em_filamento(filamentos_: list[dict]) -> float:
    """Quanto dinheiro esta dormindo em rolo.

    So conta rolo COM preco: filamento sem preco de compra nao vale zero, vale
    desconhecido -- e somar zero faria o estoque parecer mais barato do que e.
    Quantos ficaram de fora e o que `sem_preco` conta, para a tela dizer.
    """
    return round(sum((f["gramas"] or 0) / 1000.0 * f["preco_kg"]
                     for f in filamentos_ if f["preco_kg"]), 2)


def sem_preco(filamentos_: list[dict]) -> int:
    return sum(1 for f in filamentos_ if not f["preco_kg"])


def limites_do_mes(quando: date | None = None) -> tuple[str, str]:
    """O primeiro instante deste mes e o do proximo, em UTC.

    O mes vira a meia-noite DAQUI e o banco grava em UTC: uma entrega das 21h
    de 31 de agosto esta gravada como 1º de setembro. Comparar o texto cru
    jogaria essa venda no mes errado.
    """
    quando = quando or formato.hoje()
    ano, mes = quando.year, quando.month
    seguinte = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
    inicio = datetime(ano, mes, 1, tzinfo=formato.AQUI)
    fim = datetime(seguinte[0], seguinte[1], 1, tzinfo=formato.AQUI)
    return (inicio.astimezone(timezone.utc).isoformat(),
            fim.astimezone(timezone.utc).isoformat())


def entregues_no_mes(quando: date | None = None) -> list[dict]:
    """Os pedidos entregues no mes corrente -- a lista, nao o total.

    Pedido entregue antes de a coluna `entregue_em` existir, e sem historico
    de onde tirar a data, fica de fora. Melhor faltar do que aparecer num mes
    que nao foi o dele.
    """
    inicio, fim = limites_do_mes(quando)
    with conectar() as conn:
        linhas = conn.execute(
            "SELECT d.*, (SELECT COUNT(*) FROM pecas WHERE pedido_id = d.id) AS itens"
            " FROM pedidos d WHERE d.status = 'entregue'"
            " AND d.entregue_em >= ? AND d.entregue_em < ?"
            " ORDER BY d.entregue_em DESC, d.id DESC", (inicio, fim)).fetchall()
    return [dict(l, dias=_dias_ate(l["prazo"])) for l in linhas]


def avisos(pedidos_: list[dict], filamentos_: list[dict]) -> list[dict]:
    """Um aviso so, ordenado por URGENCIA -- nao por tipo.

    A versao anterior tinha tres blocos: senha, depois TODO atraso, depois
    TODO filamento baixo. Entao um rolo ZERADO -- que para a impressora agora,
    no meio de uma peca -- aparecia embaixo de um pedido que atrasou ontem, e
    duas cores em 5 g apareciam na ordem alfabetica do nome do rolo.

    A urgencia parte o filamento em dois: acabou (para tudo) e esta acabando
    (da tempo de comprar). O atraso mora entre os dois, porque o cliente ja
    esta esperando mas a bancada nao parou.
    """
    fora = []
    for f in filamentos_:
        if (f["gramas"] or 0) <= 0:
            fora.append({"tipo": "filamento_zero", "nivel": "mal", "ordem": (1, 0), "item": f})
        elif f["gramas"] <= f["minimo"]:
            sobra = f["gramas"] / f["minimo"] if f["minimo"] else 1
            fora.append({"tipo": "filamento", "nivel": "atencao", "ordem": (3, sobra), "item": f})
    for p in pedidos_:
        if (p.get("dias") if p.get("dias") is not None else 99) < 0:
            fora.append({"tipo": "atraso", "nivel": "mal", "ordem": (2, p["dias"]), "item": p})
    return sorted(fora, key=lambda a: a["ordem"])


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

    pedidos = [dict(p, dias=_dias_ate(p["prazo"])) for p in pedidos]
    fila = [dict(p) for p in fila]
    filamento = [dict(f) for f in filamento]
    entregues = entregues_no_mes()

    return {
        "pedidos": pedidos,
        "fila": fila,
        "fila_por_cor": {c: [dict(p) for p in v] for c, v in por_cor.items()},
        "horas_fila": horas_na_mesa(fila),
        "trocas_de_cor": max(0, len(por_cor) - 1),
        "purga_g": max(0, len(por_cor) - 1) * 6,
        "filamento": filamento,
        "filamento_baixo": [f for f in filamento if f["gramas"] <= f["minimo"]],
        "atrasados": [p for p in pedidos if (p["dias"] or 99) < 0],
        "avisos": avisos(pedidos, filamento),
        "a_receber": somar_valor(pedidos),
        "parado": parado_em_filamento(filamento),
        "cores_sem_preco": sem_preco(filamento),
        "entregues": entregues,
        "entregue_no_mes": somar_valor(entregues),
        "mes": formato.mes_por_extenso(),
        "vazio": not pedidos and not fila and not filamento,
        "cores": CORES,
    }


RE_SKU = re.compile(r"^M3D-[A-Z]{2}-\d{3}$")


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
            f"SELECT *, {VEIO_DE_COMPRA.format(t='filamento', tab='filamentos')}"
            f" FROM filamentos {onde} ORDER BY gramas <= minimo DESC, cor, nome")]


def filamento(id_: int) -> dict | None:
    with conectar() as conn:
        linha = conn.execute(
            f"SELECT *, {VEIO_DE_COMPRA.format(t='filamento', tab='filamentos')}"
            f" FROM filamentos WHERE id = ?", (id_,)).fetchone()
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
        # So o MANUAL vem da tela. O preco em uso (`preco_kg`) e derivado por
        # _atualizar_preco: compra mais recente, e o digitado so na falta dela.
        # Deixar a tela escrever os dois apagava o numero do dono quando a
        # pessoa salvava a ficha sem mexer no preco -- o valor da compra, que
        # o campo estava exibindo, virava o "digitado".
        preco_manual=_numero(dados.get("preco_kg")) or None,
        ativo=1 if dados.get("ativo", "1") in (1, "1", True, "on") else 0,
    )


def salvar_filamento(dados: dict, autor: str, id_: int | None = None) -> int:
    campos = campos_filamento(dados)
    if not campos["nome"]:
        raise ErroDeCampo("nome", "Dê um nome ao filamento — é ele que aparece "
                                  "na hora de escolher no produto.")
    if campos["cor"] not in CORES:
        raise ErroDeCampo("cor", "Escolha uma das cores do catálogo. São as mesmas "
                                 "11 do gerador de letreiros, de propósito.")
    with conectar() as conn:
        if id_:
            # Mexer no estoque pela tela e um evento como qualquer outro. Sem
            # registrar, o saldo deixa de ser a soma dos movimentos e o
            # relatorio de filamento gasto passa a mentir em silencio.
            antes = conn.execute("SELECT gramas FROM filamentos WHERE id = ?",
                                 (id_,)).fetchone()
            # `gramas` fica DE FORA do UPDATE de proposito: o saldo so muda
            # por movimento. Escrever o valor absoluto aqui e depois somar a
            # diferenca aplicava a mudanca duas vezes -- 1000 para 1500 virava
            # 2000.
            conn.execute(
                "UPDATE filamentos SET nome=:nome, marca=:marca, tipo=:tipo, cor=:cor,"
                " minimo=:minimo, preco_manual=:preco_manual,"
                " ativo=:ativo WHERE id=:id", {**campos, "id": id_})
            _atualizar_preco(conn, "filamento", id_)
            if antes and abs(campos["gramas"] - antes["gramas"]) > 1e-9:
                _lancar(conn, "filamento", id_, campos["gramas"] - antes["gramas"],
                        "ajuste", autor)
            conn.commit()
            return id_
        cur = conn.execute(
            "INSERT INTO filamentos (nome, marca, tipo, cor, gramas, minimo,"
            " preco_manual, ativo, criado_em, criado_por) VALUES (:nome, :marca, :tipo,"
            " :cor, :gramas, :minimo, :preco_manual, :ativo, :criado_em, :criado_por)",
            {**campos, "criado_em": agora(), "criado_por": autor})
        _atualizar_preco(conn, "filamento", int(cur.lastrowid))
        _lancar(conn, "filamento", int(cur.lastrowid), campos["gramas"], "inicial", autor)
        conn.commit()
        return int(cur.lastrowid)


def insumos(so_ativos: bool = True) -> list[dict]:
    with conectar() as conn:
        onde = "WHERE ativo = 1" if so_ativos else ""
        return [dict(l) for l in conn.execute(
            f"SELECT *, {VEIO_DE_COMPRA.format(t='insumo', tab='insumos')}"
            f" FROM insumos {onde} ORDER BY quantidade <= minimo DESC, nome")]


def insumo(id_: int) -> dict | None:
    with conectar() as conn:
        linha = conn.execute(
            f"SELECT *, {VEIO_DE_COMPRA.format(t='insumo', tab='insumos')}"
            f" FROM insumos WHERE id = ?", (id_,)).fetchone()
    return dict(linha) if linha else None


def campos_insumo(dados: dict) -> dict:
    return dict(
        nome=_limpo(dados.get("nome")),
        unidade=_limpo(dados.get("unidade"), "un"),
        quantidade=_numero(dados.get("quantidade")),
        minimo=_numero(dados.get("minimo")),
        valor_manual=_numero(dados.get("valor_unit")) or None,   # ver campos_filamento
        descricao=_limpo(dados.get("descricao")),
        ativo=1 if dados.get("ativo", "1") in (1, "1", True, "on") else 0,
    )


def salvar_insumo(dados: dict, autor: str, id_: int | None = None) -> int:
    campos = campos_insumo(dados)
    if not campos["nome"]:
        raise ErroDeCampo("nome", "Dê um nome ao insumo.")
    with conectar() as conn:
        if id_:
            antes = conn.execute("SELECT quantidade FROM insumos WHERE id = ?",
                                 (id_,)).fetchone()
            # Mesma razao do filamento: quantidade so muda por movimento.
            conn.execute(
                "UPDATE insumos SET nome=:nome, unidade=:unidade, minimo=:minimo,"
                " valor_manual=:valor_manual,"
                " descricao=:descricao, ativo=:ativo WHERE id=:id", {**campos, "id": id_})
            _atualizar_preco(conn, "insumo", id_)
            if antes and abs(campos["quantidade"] - antes["quantidade"]) > 1e-9:
                _lancar(conn, "insumo", id_, campos["quantidade"] - antes["quantidade"],
                        "ajuste", autor)
            conn.commit()
            return id_
        cur = conn.execute(
            "INSERT INTO insumos (nome, unidade, quantidade, minimo,"
            " valor_manual, descricao, ativo, criado_em, criado_por)"
            " VALUES (:nome, :unidade, :quantidade, :minimo, :valor_manual,"
            " :descricao, :ativo, :criado_em, :criado_por)",
            {**campos, "criado_em": agora(), "criado_por": autor})
        _atualizar_preco(conn, "insumo", int(cur.lastrowid))
        _lancar(conn, "insumo", int(cur.lastrowid), campos["quantidade"], "inicial", autor)
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
        dimensao_x=_numero(dados.get("dimensao_x")) or None,
        dimensao_y=_numero(dados.get("dimensao_y")) or None,
        usa_preco_volume=1 if dados.get("usa_preco_volume", "") in (1, "1", "on") else 0,
        margem_volume=_numero(dados.get("margem_volume")) or 150,
        taxa_setup=_numero(dados.get("taxa_setup")) or 5.0,
        preco_fixo=_numero(dados.get("preco_fixo")) or None,
    )


def salvar_produto(dados: dict, autor: str, id_: int | None = None,
                   vinculos: list[tuple[int, float]] | None = None) -> int:
    campos = campos_produto(dados)
    if not campos["nome"]:
        raise ErroDeCampo("nome", "Dê um nome ao produto.")
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


# ------------------------------------------------------------ clientes
def clientes(so_ativos: bool = True) -> list[dict]:
    with conectar() as conn:
        onde = "WHERE ativo = 1" if so_ativos else ""
        return [dict(l) for l in conn.execute(
            f"SELECT * FROM clientes {onde} ORDER BY nome")]


def cliente(id_: int) -> dict | None:
    with conectar() as conn:
        linha = conn.execute("SELECT * FROM clientes WHERE id = ?", (id_,)).fetchone()
    return dict(linha) if linha else None


def campos_cliente(dados: dict) -> dict:
    return dict(
        nome=_limpo(dados.get("nome")),
        whatsapp=_limpo(dados.get("whatsapp")),
        canal=_limpo(dados.get("canal")),
        observacao=_limpo(dados.get("observacao")),
        ativo=1 if dados.get("ativo", "1") in (1, "1", True, "on") else 0,
    )


def salvar_cliente(dados: dict, autor: str, id_: int | None = None) -> int:
    campos = campos_cliente(dados)
    if not campos["nome"]:
        raise ErroDeCampo("nome", "Dê um nome ao cliente.")
    with conectar() as conn:
        if id_:
            conn.execute(
                "UPDATE clientes SET nome=:nome, whatsapp=:whatsapp, canal=:canal,"
                " observacao=:observacao, ativo=:ativo WHERE id=:id", {**campos, "id": id_})
            conn.commit()
            return id_
        cur = conn.execute(
            "INSERT INTO clientes (nome, whatsapp, canal, observacao, ativo, criado_em,"
            " criado_por) VALUES (:nome, :whatsapp, :canal, :observacao, :ativo,"
            " :criado_em, :criado_por)",
            {**campos, "criado_em": agora(), "criado_por": autor})
        conn.commit()
        return int(cur.lastrowid)


def canais(so_ativos: bool = True) -> list[dict]:
    with conectar() as conn:
        onde = "WHERE ativo = 1" if so_ativos else ""
        return [dict(l) for l in conn.execute(f"SELECT * FROM canais {onde} ORDER BY nome")]


def salvar_comissao(nome: str, comissao: float) -> None:
    with conectar() as conn:
        conn.execute("UPDATE canais SET comissao = ? WHERE nome = ?",
                     (max(float(comissao), 0.0), nome))
        conn.commit()


# ------------------------------------------------------------- pedidos
def pedidos(situacoes: tuple[str, ...] = ABERTOS) -> list[dict]:
    marcadores = ", ".join("?" for _ in situacoes)
    with conectar() as conn:
        linhas = conn.execute(
            f"SELECT d.*, (SELECT COUNT(*) FROM pecas WHERE pedido_id = d.id) AS itens"
            f" FROM pedidos d WHERE d.status IN ({marcadores})"
            f" ORDER BY d.prazo IS NULL, d.prazo, d.id DESC", situacoes).fetchall()
    return [dict(l, dias=_dias_ate(l["prazo"])) for l in linhas]


def pedido(id_: int) -> dict | None:
    with conectar() as conn:
        linha = conn.execute("SELECT * FROM pedidos WHERE id = ?", (id_,)).fetchone()
        if not linha:
            return None
        itens = conn.execute(
            "SELECT p.*, pr.nome AS produto_nome FROM pecas p"
            " LEFT JOIN produtos pr ON pr.id = p.produto_id"
            " WHERE p.pedido_id = ? ORDER BY p.id", (id_,)).fetchall()
    dados = dict(linha, dias=_dias_ate(linha["prazo"]))
    dados["itens"] = [dict(i) for i in itens]
    return dados


def _comissao_do_canal(conn, canal: str) -> float:
    linha = conn.execute("SELECT comissao FROM canais WHERE nome = ?", (canal,)).fetchone()
    return float(linha["comissao"]) if linha else 0.0


# ------------------------------------------------------------------ empresa
#
# Quem assina o orcamento. Uma linha so: e uma empresa.

CAMPOS_EMPRESA = ("nome", "documento", "telefone", "email", "endereco", "site",
                  "cor", "condicoes")


def campos_empresa(dados: dict) -> dict:
    campos = {c: _limpo(dados.get(c)) for c in CAMPOS_EMPRESA}
    campos["validade_dias"] = max(1, int(_numero(dados.get("validade_dias"), 7)))
    return campos


def empresa() -> dict:
    with conectar() as conn:
        return dict(conn.execute("SELECT * FROM empresa WHERE id = 1").fetchone())


RE_COR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def salvar_empresa(dados: dict, autor: str) -> None:
    campos = campos_empresa(dados)
    if not campos["nome"]:
        raise ErroDeCampo("nome", "O orçamento precisa sair assinado por alguém.")
    if not RE_COR.match(campos["cor"] or ""):
        raise ErroDeCampo("cor", "A cor tem que ser um código de seis dígitos, "
                                 "como #0040F0.")
    with conectar() as conn:
        colunas = ", ".join(f"{c}=:{c}" for c in campos)
        conn.execute(f"UPDATE empresa SET {colunas}, atualizado_em=:quando WHERE id = 1",
                     {**campos, "quando": agora()})
        conn.commit()


# ----------------------------------------------------- o link do orcamento
#
# O cliente aceita o orcamento SEM senha, por um endereco que so ele tem. Duas
# regras seguram isso:
#
#   * o token e sorteado por `secrets`, com 32 caracteres. Adivinhar um vale
#      tanto quanto adivinhar uma senha -- e ha indice unico no banco, porque
#      sorteio repetido acontece e nao pode virar dois pedidos com um link;
#   * ele EXPIRA. Orcamento e uma proposta de preco, e preco de tres meses
#     atras nao vale hoje -- o filamento subiu.

def _sortear_token() -> str:
    return secrets.token_urlsafe(24)


def token_do_orcamento(id_: int, dias: int | None = None) -> dict:
    """Cria (ou renova) o link deste orcamento e devolve token e validade."""
    if dias is None:
        dias = int(empresa()["validade_dias"])
    expira = (formato.hoje() + timedelta(days=max(1, dias))).isoformat()
    with conectar() as conn:
        if _aceito(conn, id_):
            # Renovar o link de um orcamento ja aceito reabriria o que ja foi
            # combinado. O link antigo continua valendo para LER.
            linha = conn.execute("SELECT token, token_expira FROM pedidos WHERE id = ?",
                                 (id_,)).fetchone()
            return {"token": linha["token"], "expira": linha["token_expira"]}
        for _ in range(5):        # sorteio repetido acontece; o indice barra
            token = _sortear_token()
            try:
                conn.execute("UPDATE pedidos SET token = ?, token_expira = ? WHERE id = ?",
                             (token, expira, id_))
                conn.commit()
                return {"token": token, "expira": expira}
            except sqlite3.IntegrityError:
                continue
    raise RuntimeError("nao consegui sortear um token livre")


def pedido_por_token(token: str) -> dict | None:
    """O pedido daquele link -- ou None se o link nao existe ou venceu."""
    if not token:
        return None
    with conectar() as conn:
        linha = conn.execute("SELECT * FROM pedidos WHERE token = ?", (token,)).fetchone()
        if not linha:
            return None
        # Vencido continua legivel para quem ja aceitou: o cliente guarda o
        # link e volta nele para conferir o que combinou.
        if not linha["aceito_em"] and (linha["token_expira"] or "") < formato.hoje().isoformat():
            return None
        itens = conn.execute(
            "SELECT * FROM pecas WHERE pedido_id = ? ORDER BY id", (linha["id"],)).fetchall()
    pedido_ = dict(linha, dias=_dias_ate(linha["prazo"]))
    pedido_["itens"] = [dict(i) for i in itens]
    return pedido_


def aceitar_orcamento(token: str, quem: str) -> dict | None:
    """O cliente aceita. Acontece UMA vez -- o segundo clique nao muda a data."""
    alvo = pedido_por_token(token)
    if not alvo:
        return None
    with conectar() as conn:
        conn.execute(
            "UPDATE pedidos SET aceito_em = ?, aceito_por = ?, status = 'aprovado'"
            " WHERE token = ? AND aceito_em IS NULL",
            (agora(), _limpo(quem)[:90], token))
        # Aceitar poe as pecas na fila: e o que "aprovado" significa aqui
        # dentro, e e a mesma regra de `mudar_situacao`.
        # ETAPAS[0], e nao "na fila": esse nome antigo so continua funcionando
        # em `mudar_situacao` porque a migracao o renomeia a cada conexao.
        conn.execute(
            f"UPDATE pecas SET status = '{ETAPAS[0]}'"
            f" WHERE pedido_id = ? AND status = 'orcamento'", (alvo["id"],))
        conn.commit()
    return pedido_por_token(token)


def _aceito(conn, id_: int) -> bool:
    linha = conn.execute("SELECT aceito_em FROM pedidos WHERE id = ?", (id_,)).fetchone()
    return bool(linha and linha["aceito_em"])


def _carimbar_entrega(conn, id_: int, situacao: str) -> None:
    """Grava QUANDO o pedido virou entregue -- ou apaga, se ele voltou atras.

    COALESCE de proposito: editar um pedido ja entregue nao pode mover a data
    da entrega para a data da edicao.
    """
    if situacao == "entregue":
        conn.execute("UPDATE pedidos SET entregue_em = COALESCE(entregue_em, ?)"
                     " WHERE id = ?", (agora(), id_))
    else:
        conn.execute("UPDATE pedidos SET entregue_em = NULL WHERE id = ?", (id_,))


def salvar_pedido(dados: dict, autor: str, id_: int | None = None,
                  itens: list[dict] | None = None) -> int:
    """Grava o pedido e seus itens.

    `valor` e `valor_liquido` sao GRAVADOS, e nao calculados na leitura. A
    comissao do canal muda com o tempo; um pedido de marco tem que continuar
    dizendo quanto sobrou em marco, e nao quanto sobraria com a taxa de hoje.
    """
    cliente_id = int(dados["cliente_id"]) if _limpo(dados.get("cliente_id")) else None
    nome = _limpo(dados.get("cliente"))
    canal = _limpo(dados.get("canal"))
    with conectar() as conn:
        if cliente_id:
            linha = conn.execute("SELECT nome, canal FROM clientes WHERE id = ?",
                                 (cliente_id,)).fetchone()
            if linha:
                nome = linha["nome"]
                canal = canal or (linha["canal"] or "")
        if not nome:
            raise ErroDeCampo("cliente_id",
                              "Escolha o cliente do pedido — é dele que vem o canal, "
                              "e é o canal que responde de onde vêm seus pedidos.")

        # Orcamento que o cliente ACEITOU e um acordo. Mudar item ou preco
        # depois do aceite e mudar o que foi combinado -- e o PDF que ele
        # guardou passaria a discordar do sistema, em silencio.
        if id_ and _aceito(conn, id_):
            raise ValueError(
                "Este orçamento já foi aceito pelo cliente e não pode mais ser "
                "editado. Para mudar o combinado, faça um pedido novo.")

        situacao = _limpo(dados.get("status"), "orcamento")
        if situacao not in SITUACOES:
            raise ValueError(f"situacao desconhecida: {situacao}")

        itens = itens or []
        valor = round(sum(i["quantidade"] * i["valor_unit"] for i in itens), 2)
        # Desconto em REAIS, e nao em porcentagem: e assim que ele e dado no
        # balcao ("faco por 600"). Preso ao valor, porque pedido negativo
        # entraria no "a receber" DIMINUINDO o total, e o erro so apareceria
        # no fim do mes.
        desconto = min(max(_numero(dados.get("desconto")), 0.0), valor)
        comissao = (_numero(dados.get("comissao")) if _limpo(dados.get("comissao"))
                    else _comissao_do_canal(conn, canal))
        # A comissao do marketplace incide sobre o que o cliente PAGA.
        liquido = round((valor - desconto) * (1 - comissao / 100.0), 2)
        campos = dict(
            cliente=nome, cliente_id=cliente_id, canal=canal,
            id_no_canal=_limpo(dados.get("id_no_canal")) or None,
            comissao=comissao, desconto=desconto,
            valor=valor, valor_liquido=liquido,
            prazo=_limpo(dados.get("prazo")) or None,
            status=situacao, observacao=_limpo(dados.get("observacao")),
        )
        if campos["id_no_canal"]:
            # O mesmo pedido chegando duas vezes da loja ou do marketplace nao
            # pode virar dois. E a falha classica de aviso reenviado.
            ja = conn.execute(
                "SELECT id FROM pedidos WHERE canal = ? AND id_no_canal = ? AND id <> ?",
                (canal, campos["id_no_canal"], id_ or -1)).fetchone()
            if ja:
                raise ErroDeCampo(
                    "id_no_canal",
                    f"O pedido {campos['id_no_canal']} de {canal} já entrou "
                    f"(nº {ja['id']}). O mesmo aviso chegando duas vezes não pode "
                    f"virar dois pedidos.")

        if id_:
            colunas = ", ".join(f"{c}=:{c}" for c in campos)
            conn.execute(f"UPDATE pedidos SET {colunas} WHERE id=:id", {**campos, "id": id_})
        else:
            nomes = ", ".join(campos)
            marcas = ", ".join(f":{c}" for c in campos)
            cur = conn.execute(
                f"INSERT INTO pedidos ({nomes}, criado_em, criado_por)"
                f" VALUES ({marcas}, :criado_em, :criado_por)",
                {**campos, "criado_em": agora(), "criado_por": autor})
            id_ = int(cur.lastrowid)

        _carimbar_entrega(conn, id_, situacao)

        conn.execute("DELETE FROM pecas WHERE pedido_id = ?", (id_,))
        for i in itens:
            conn.execute(
                "INSERT INTO pecas (pedido_id, produto_id, descricao, cor, quantidade,"
                " valor_unit, gramas_est, horas_est, status, criado_em, criado_por)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (id_, i.get("produto_id"), i["descricao"], i.get("cor", ""),
                 i["quantidade"], i["valor_unit"], i.get("gramas"), i.get("horas"),
                 "na fila" if situacao == "aprovado" else "orcamento", agora(), autor))
        conn.commit()
    return id_


def mudar_situacao(id_: int, situacao: str, autor: str) -> None:
    """Aprovar poe as pecas na fila; cancelar as tira."""
    if situacao not in SITUACOES:
        raise ValueError(f"situacao desconhecida: {situacao}")
    with conectar() as conn:
        conn.execute("UPDATE pedidos SET status = ? WHERE id = ?", (situacao, id_))
        _carimbar_entrega(conn, id_, situacao)
        if situacao == "aprovado":
            conn.execute(
                "UPDATE pecas SET status = 'na fila' WHERE pedido_id = ? AND status = 'orcamento'",
                (id_,))
        elif situacao in ("cancelado", "entregue"):
            alvo = "cancelado" if situacao == "cancelado" else "entregue"
            conn.execute(
                f"UPDATE pecas SET status = '{alvo}' WHERE pedido_id = ?"
                f" AND status IN ({', '.join('?' for _ in EM_PRODUCAO)})", (id_, *EM_PRODUCAO))
        conn.commit()


# ------------------------------------------------------------- producao
#
# O estoque nao e alterado direto: cada mudanca vira um MOVIMENTO, e o saldo
# e a soma deles. A coluna `gramas` do filamento e so um cache disso -- ha
# teste provando que os dois batem. Assim, mover a peca de volta uma etapa
# devolve o material sem precisar adivinhar quanto foi tirado, e o relatorio
# de filamento gasto (sprint 7) sai de graca.

CAMPO_SALDO = {"filamento": ("filamentos", "gramas"), "insumo": ("insumos", "quantidade")}


def _lancar(conn, tipo: str, alvo_id: int, quantidade: float, motivo: str,
            autor: str, peca_id: int | None = None, observacao: str = "",
            compra_id: int | None = None) -> None:
    """Grava o movimento e move o saldo junto, na mesma transacao."""
    conn.execute(
        "INSERT INTO movimentos (tipo, alvo_id, quantidade, motivo, peca_id, compra_id,"
        " observacao, criado_em, criado_por) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (tipo, alvo_id, quantidade, motivo, peca_id, compra_id, observacao, agora(), autor))
    if motivo != "inicial":
        tabela, coluna = CAMPO_SALDO[tipo]
        conn.execute(f"UPDATE {tabela} SET {coluna} = {coluna} + ? WHERE id = ?",
                     (quantidade, alvo_id))


def saldo_pelos_movimentos(tipo: str, alvo_id: int) -> float:
    """O saldo que os movimentos dizem. Existe para conferir o cache."""
    with conectar() as conn:
        linha = conn.execute(
            "SELECT COALESCE(SUM(quantidade), 0) AS s FROM movimentos"
            " WHERE tipo = ? AND alvo_id = ?", (tipo, alvo_id)).fetchone()
    return round(float(linha["s"]), 4)


def _filamento_da_peca(conn, peca) -> int | None:
    """Qual rolo sai do estoque.

    Pela COR da peca, que e o que o cliente pediu. Entre os rolos daquela
    cor, o do produto tem preferencia; sem ele, o mais cheio -- que e o que
    qualquer pessoa pegaria na bancada.
    """
    if not peca["cor"]:
        return None
    candidatos = conn.execute(
        "SELECT id FROM filamentos WHERE ativo = 1 AND cor = ? ORDER BY gramas DESC",
        (peca["cor"],)).fetchall()
    if not candidatos:
        return None
    if peca["produto_id"]:
        prod = conn.execute("SELECT filamento_id FROM produtos WHERE id = ?",
                            (peca["produto_id"],)).fetchone()
        if prod and prod["filamento_id"] in {c["id"] for c in candidatos}:
            return prod["filamento_id"]
    return candidatos[0]["id"]


def _baixar(conn, peca, autor: str) -> None:
    fil = _filamento_da_peca(conn, peca)
    if fil and (peca["gramas_est"] or 0) > 0:
        conn.execute("SAVEPOINT baixa")
        try:
            _lancar(conn, "filamento", fil, -float(peca["gramas_est"]), "producao",
                    autor, peca["id"])
        except sqlite3.IntegrityError:
            # Ja havia baixa de producao para esta peca. O indice unico do
            # banco e quem garante isso, e nao a ordem em que as telas chamam.
            conn.execute("ROLLBACK TO baixa")
        conn.execute("RELEASE baixa")
    if peca["produto_id"]:
        vinculos = conn.execute(
            "SELECT insumo_id, quantidade FROM produto_insumos WHERE produto_id = ?",
            (peca["produto_id"],)).fetchall()
        for v in vinculos:
            conn.execute("SAVEPOINT baixai")
            try:
                _lancar(conn, "insumo", v["insumo_id"],
                        -float(v["quantidade"]) * float(peca["quantidade"] or 1),
                        "producao", autor, peca["id"])
            except sqlite3.IntegrityError:
                conn.execute("ROLLBACK TO baixai")
            conn.execute("RELEASE baixai")


def _estornar(conn, peca_id: int, autor: str) -> None:
    """Voltar uma etapa devolve o material. Apaga a baixa, nao lanca outra:
    assim a peca pode ser baixada de novo depois, e o relatorio de gasto nao
    conta uma ida e volta como consumo."""
    baixas = conn.execute(
        "SELECT * FROM movimentos WHERE peca_id = ? AND motivo = 'producao'",
        (peca_id,)).fetchall()
    for m in baixas:
        tabela, coluna = CAMPO_SALDO[m["tipo"]]
        conn.execute(f"UPDATE {tabela} SET {coluna} = {coluna} - ? WHERE id = ?",
                     (m["quantidade"], m["alvo_id"]))
        conn.execute("DELETE FROM movimentos WHERE id = ?", (m["id"],))


def mover_peca(peca_id: int, para: str, autor: str, observacao: str = "") -> None:
    if para not in ETAPAS:
        raise ValueError(f"etapa desconhecida: {para}")
    with conectar() as conn:
        peca = conn.execute("SELECT * FROM pecas WHERE id = ?", (peca_id,)).fetchone()
        if not peca:
            raise ValueError("peca nao encontrada")
        de = peca["status"]
        if de == para:
            return
        indice = {e: i for i, e in enumerate(ETAPAS)}
        passou = indice.get(de, -1) >= indice[ETAPA_QUE_CONSOME]
        vai_passar = indice[para] >= indice[ETAPA_QUE_CONSOME]
        if vai_passar and not passou:
            _baixar(conn, peca, autor)
        elif passou and not vai_passar:
            _estornar(conn, peca_id, autor)
        conn.execute("UPDATE pecas SET status = ? WHERE id = ?", (para, peca_id))
        conn.execute(
            "INSERT INTO historico (peca_id, de, para, observacao, criado_em, criado_por)"
            " VALUES (?, ?, ?, ?, ?, ?)", (peca_id, de, para, observacao, agora(), autor))
        conn.commit()


def registrar_refugo(peca_id: int, autor: str, motivo: str = "") -> None:
    """A peca falhou. O material ja saiu e nao volta: vira PERDA.

    Converte a baixa de producao em refugo, em vez de lancar outra saida --
    senao o filamento sairia duas vezes do estoque para a mesma impressao. A
    peca volta para "aguardando", porque o cliente continua querendo a peca.
    """
    with conectar() as conn:
        peca = conn.execute("SELECT * FROM pecas WHERE id = ?", (peca_id,)).fetchone()
        if not peca:
            raise ValueError("peca nao encontrada")
        alterou = conn.execute(
            "UPDATE movimentos SET motivo = 'refugo', observacao = ?"
            " WHERE peca_id = ? AND motivo = 'producao'", (motivo, peca_id)).rowcount
        if not alterou:
            # Refugou antes de a peca ter passado pela producao: registra a
            # perda mesmo assim, senao o relatorio nao veria o prejuizo.
            fil = _filamento_da_peca(conn, peca)
            if fil and (peca["gramas_est"] or 0) > 0:
                _lancar(conn, "filamento", fil, -float(peca["gramas_est"]), "refugo",
                        autor, peca["id"], motivo)
        conn.execute("UPDATE pecas SET status = 'aguardando' WHERE id = ?", (peca_id,))
        conn.execute(
            "INSERT INTO historico (peca_id, de, para, observacao, criado_em, criado_por)"
            " VALUES (?, ?, 'aguardando', ?, ?, ?)",
            (peca_id, peca["status"], f"refugo: {motivo}" if motivo else "refugo",
             agora(), autor))
        conn.commit()


def quadro() -> dict:
    """As pecas por etapa, para o quadro e para a lista -- uma consulta so."""
    with conectar() as conn:
        linhas = conn.execute(
            "SELECT p.*, d.cliente, d.prazo, d.id AS pedido FROM pecas p"
            " LEFT JOIN pedidos d ON d.id = p.pedido_id"
            " WHERE p.status IN ({}) ORDER BY d.prazo IS NULL, d.prazo, p.id".format(
                ", ".join("?" for _ in ETAPAS)), ETAPAS).fetchall()
    pecas = [dict(l, dias=_dias_ate(l["prazo"])) for l in linhas]
    por_etapa = {e: [p for p in pecas if p["status"] == e] for e in ETAPAS}
    return {
        "etapas": ETAPAS,
        "rotulos": ROTULOS,
        "convites": CONVITES,
        "por_etapa": por_etapa,
        # Peca, hora e grama por coluna -- pelas MESMAS funcoes que o painel
        # usa. "Quantas peças" ja estava no cabecalho; sozinho ele nao diz se
        # a coluna e meia hora ou dois dias de mesa.
        "totais": {e: {"pecas": len(v),
                       "horas": horas_na_mesa(v),
                       "gramas": gramas_na_fila(v)} for e, v in por_etapa.items()},
        "pecas": pecas,
        # O mesmo numero que o painel mostra em "na mesa", pela mesma funcao.
        "horas_na_mesa": horas_na_mesa([p for p in pecas if p["status"] in EM_PRODUCAO]),
        "cores": CORES,
    }


def historico_da_peca(peca_id: int) -> list[dict]:
    with conectar() as conn:
        return [dict(l) for l in conn.execute(
            "SELECT * FROM historico WHERE peca_id = ? ORDER BY id", (peca_id,))]


# -------------------------------------------------------------- compras
#
# E aqui que o custo deixa de ser ficcao. Enquanto o preco do filamento for
# digitado uma vez e esquecido, o custo de toda peca e um chute com cara de
# numero. Lancando a compra, o preco passa a ser o que foi PAGO -- e o custo
# de todo produto que usa aquele filamento se corrige sozinho.

VEIO_DE_COMPRA = ("EXISTS (SELECT 1 FROM compra_itens i WHERE i.tipo = '{t}'"
                  " AND i.alvo_id = {tab}.id AND i.quantidade > 0) AS veio_de_compra")


def _preco_da_ultima_compra(conn, tipo: str, alvo_id: int) -> float | None:
    """O preco por unidade da compra mais recente. None se nunca comprou."""
    linha = conn.execute(
        "SELECT i.quantidade, i.valor FROM compra_itens i"
        " JOIN compras c ON c.id = i.compra_id"
        " WHERE i.tipo = ? AND i.alvo_id = ? AND i.quantidade > 0"
        " ORDER BY c.data DESC, c.id DESC LIMIT 1", (tipo, alvo_id)).fetchone()
    if not linha:
        return None
    # Filamento e comprado em gramas e custeado por quilo.
    divisor = linha["quantidade"] / 1000.0 if tipo == "filamento" else linha["quantidade"]
    return round(linha["valor"] / divisor, 4) if divisor else None


def _atualizar_preco(conn, tipo: str, alvo_id: int) -> None:
    """O preco em uso e o da ULTIMA COMPRA; sem compra, o digitado a mao.

    Sao dois donos e por isso duas colunas. Com uma so, apagar uma compra
    deixava na tela o preco dela -- fantasma de um registro que nao existe
    mais, com cara de numero conferido.
    """
    preco = _preco_da_ultima_compra(conn, tipo, alvo_id)
    if tipo == "filamento":
        conn.execute(
            "UPDATE filamentos SET preco_kg = COALESCE(?, preco_manual) WHERE id = ?",
            (preco, alvo_id))
    else:
        conn.execute(
            "UPDATE insumos SET valor_unit = COALESCE(?, valor_manual, 0) WHERE id = ?",
            (preco, alvo_id))


# ------------------------------------------------------------------ templates
FORMAS = ("", "coracao", "estrela")
CAMPOS_TEMPLATE = ("nome", "numero")

# Lido de web/nucleo/pecas.js, que e onde o registro de pecas mora. Escrever a
# lista aqui a mao seria a copia que ninguem lembra de atualizar no dia de
# acrescentar a terceira peca.
PECAS_JS = Path(__file__).resolve().parent.parent / "web" / "nucleo" / "pecas.js"


def tipos_de_peca() -> dict[str, str]:
    """{tipo: prefixo de SKU}, ex.: {"topo": "TB", "chaveiro": "CH"}."""
    try:
        texto = PECAS_JS.read_text(encoding="utf-8")
    except OSError:
        return {"topo": "TB"}
    achados = re.findall(r"tipo:\s*'(\w+)',[\s\S]{0,400}?sku:\s*'([A-Z]{2})'", texto)
    return dict(achados) or {"topo": "TB"}


def templates(so_publicados: bool = False, so_ativos: bool = True,
              tipo: str = "") -> list[dict]:
    """§10: "separar templates em teste dos publicados".

    `so_publicados` e a linha entre o painel e a loja. No painel voce ve tudo,
    com o selo de em-teste; na vitrine so entra o que ja saiu da impressora e
    voce publicou. Quem decide qual dos dois e a ROTA, e nao a tela.
    """
    onde, args = [], []
    if so_publicados:
        onde.append("publicado = 1")
    if so_ativos:
        onde.append("ativo = 1")
    if tipo:
        onde.append("tipo = ?")
        args.append(tipo)
    filtro = ("WHERE " + " AND ".join(onde)) if onde else ""
    with conectar() as conn:
        linhas = conn.execute(
            f"SELECT t.*, (SELECT COUNT(*) FROM geracoes g WHERE g.sku = t.sku) AS geracoes"
            f" FROM templates t {filtro} ORDER BY t.sku", args).fetchall()
    return [_template_dict(l) for l in linhas]


def template(sku: str) -> dict | None:
    with conectar() as conn:
        linha = conn.execute(
            "SELECT t.*, (SELECT COUNT(*) FROM geracoes g WHERE g.sku = t.sku) AS geracoes"
            " FROM templates t WHERE t.sku = ?", (sku,)).fetchone()
    return _template_dict(linha) if linha else None


def _template_dict(linha) -> dict:
    d = dict(linha)
    d["campos"] = [c for c in (d.get("campos") or "").split(",") if c]
    d["limites"] = {"nome": d["limite_nome"], "numero": d["limite_numero"]}
    d["emTeste"] = not d["publicado"]
    return d


def campos_template(dados: dict) -> dict:
    campos = [c for c in CAMPOS_TEMPLATE
              if dados.get(f"campo_{c}") in (1, "1", True, "on") or c == "nome"]
    return dict(
        sku=_limpo(dados.get("sku")).upper(),
        tipo=_limpo(dados.get("tipo"), "topo"),
        modelo=_limpo(dados.get("modelo")),
        categoria=_limpo(dados.get("categoria")),
        resumo=_limpo(dados.get("resumo")),
        campos=",".join(campos),
        frase=_limpo(dados.get("frase")).upper(),
        fonte=_limpo(dados.get("fonte"), "luckiest"),
        forma=_limpo(dados.get("forma")),
        arco=max(_numero(dados.get("arco")), 0.0),
        base=1 if dados.get("base", "1") in (1, "1", True, "on") else 0,
        limite_nome=int(_numero(dados.get("limite_nome"), 12)),
        limite_numero=int(_numero(dados.get("limite_numero"), 2)),
        licenca=_limpo(dados.get("licenca")),
        preco=max(_numero(dados.get("preco")), 0.0),
        publicado=1 if dados.get("publicado") in (1, "1", True, "on") else 0,
        ativo=1 if dados.get("ativo", "1") in (1, "1", True, "on") else 0,
    )


def salvar_template(dados: dict, autor: str, sku_antigo: str | None = None) -> str:
    campos = campos_template(dados)
    prefixos = tipos_de_peca()
    if campos["tipo"] not in prefixos:
        raise ValueError(f"nao existe gerador para a peca '{campos['tipo']}'")
    if not RE_SKU.match(campos["sku"]):
        raise ErroDeCampo("sku", "O SKU tem que seguir o padrão M3D-XX-000.")
    esperado = prefixos[campos["tipo"]]
    if campos["sku"].split("-")[1] != esperado:
        # SKU de topo num template de chaveiro nao quebra nada hoje, e por isso
        # mesmo passaria: seis meses depois ninguem sabe o que M3D-TB-042 e.
        raise ErroDeCampo("sku", f"Template de {campos['tipo']} usa SKU "
                                 f"M3D-{esperado}-000.")
    if not campos["modelo"]:
        raise ErroDeCampo("modelo", "Dê um nome ao modelo — é ele que aparece "
                                    "no gerador.")
    if campos["forma"] not in FORMAS:
        raise ErroDeCampo("forma", "Essa forma não existe no gerador.")
    if campos["limite_nome"] < 1:
        raise ErroDeCampo("limite_nome",
                          "O limite de letras do nome tem que ser maior que zero.")
    # §18 e §7: licenca e campo obrigatorio, e publicar sem ela e o erro caro.
    # Em teste, sem licenca, tudo bem -- e um rascunho seu.
    if campos["publicado"] and not campos["licenca"]:
        raise ErroDeCampo("licenca", "Não dá para publicar sem dizer a licença "
                                     "do template — de onde veio o desenho.")

    with conectar() as conn:
        existe = conn.execute("SELECT sku FROM templates WHERE sku = ?",
                              (campos["sku"],)).fetchone()
        if sku_antigo:
            if not conn.execute("SELECT 1 FROM templates WHERE sku = ?",
                                (sku_antigo,)).fetchone():
                raise ValueError("template nao encontrado")
            if existe and campos["sku"] != sku_antigo:
                raise ErroDeCampo("sku", "Já existe um template com esse SKU.")
            conn.execute(
                "UPDATE templates SET sku=:sku, tipo=:tipo, modelo=:modelo, categoria=:categoria,"
                " resumo=:resumo, campos=:campos, frase=:frase, fonte=:fonte, forma=:forma,"
                " arco=:arco, base=:base, limite_nome=:limite_nome,"
                " limite_numero=:limite_numero, licenca=:licenca, preco=:preco,"
                " publicado=:publicado, ativo=:ativo WHERE sku=:antigo",
                {**campos, "antigo": sku_antigo})
            # O historico de geracoes acompanha o SKU novo: renomear um
            # template nao pode desligar as geracoes que vieram dele.
            if campos["sku"] != sku_antigo:
                conn.execute("UPDATE geracoes SET sku = ? WHERE sku = ?",
                             (campos["sku"], sku_antigo))
        else:
            if existe:
                raise ErroDeCampo("sku", "Já existe um template com esse SKU.")
            conn.execute(
                "INSERT INTO templates (sku, tipo, modelo, categoria, resumo, campos,"
                " frase, fonte, forma, arco, base, limite_nome, limite_numero, licenca,"
                " preco, publicado, ativo, criado_em, criado_por) VALUES (:sku, :tipo,"
                " :modelo, :categoria, :resumo, :campos, :frase, :fonte, :forma, :arco,"
                " :base, :limite_nome, :limite_numero, :licenca, :preco, :publicado,"
                " :ativo, :criado_em, :criado_por)",
                {**campos, "criado_em": agora(), "criado_por": autor})
        conn.commit()
    return campos["sku"]


def publicar_template(sku: str, publicado: bool, autor: str) -> None:
    """§10 e §6: publicar e dizer "ja imprimi este e ele passou"."""
    atual = template(sku)
    if not atual:
        raise ValueError("template nao encontrado")
    if publicado and not atual["licenca"]:
        raise ErroDeCampo("licenca", "Não dá para publicar sem dizer a licença "
                                     "do template — de onde veio o desenho.")
    with conectar() as conn:
        conn.execute("UPDATE templates SET publicado = ? WHERE sku = ?",
                     (1 if publicado else 0, sku))
        conn.commit()


def apagar_template(sku: str) -> None:
    """Apaga o template. As geracoes dele FICAM.

    Um template apagado nao pode levar junto o registro de uma peca que ja foi
    entregue a um cliente -- o que aconteceu, aconteceu.
    """
    with conectar() as conn:
        conn.execute("DELETE FROM templates WHERE sku = ?", (sku,))
        conn.commit()


def registrar_geracao(dados: dict, autor: str) -> int:
    """§12: "acompanhar geracoes". Guarda a configuracao, nao o arquivo."""
    sku = _limpo(dados.get("sku"))
    nome = _limpo(dados.get("nome"))
    if not sku or not nome:
        raise ValueError("geracao precisa de template e nome")
    t = template(sku)
    with conectar() as conn:
        cur = conn.execute(
            "INSERT INTO geracoes (sku, modelo, nome, numero, tamanho, arquivo, gramas,"
            " preco, criado_em, criado_por) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (sku, (t or {}).get("modelo", ""), nome, _limpo(dados.get("numero")),
             int(_numero(dados.get("tamanho"))), _limpo(dados.get("arquivo")),
             _numero(dados.get("gramas")), _numero(dados.get("preco")), agora(), autor))
        conn.commit()
        return int(cur.lastrowid)


def geracoes(limite: int = 200, sku: str = "") -> list[dict]:
    onde = "WHERE sku = ?" if sku else ""
    args = ((sku, limite) if sku else (limite,))
    with conectar() as conn:
        return [dict(l) for l in conn.execute(
            f"SELECT * FROM geracoes {onde} ORDER BY id DESC LIMIT ?", args)]


def compras(limite: int = 100) -> list[dict]:
    with conectar() as conn:
        linhas = conn.execute(
            "SELECT c.*, (SELECT COUNT(*) FROM compra_itens WHERE compra_id = c.id) AS itens"
            " FROM compras c ORDER BY c.data DESC, c.id DESC LIMIT ?", (limite,)).fetchall()
    return [dict(l) for l in linhas]


def compra(id_: int) -> dict | None:
    with conectar() as conn:
        linha = conn.execute("SELECT * FROM compras WHERE id = ?", (id_,)).fetchone()
        if not linha:
            return None
        itens = conn.execute(
            "SELECT i.*, COALESCE(f.nome, s.nome) AS nome,"
            " COALESCE(f.cor, '') AS cor, COALESCE(s.unidade, 'g') AS unidade"
            " FROM compra_itens i"
            " LEFT JOIN filamentos f ON i.tipo = 'filamento' AND f.id = i.alvo_id"
            " LEFT JOIN insumos s ON i.tipo = 'insumo' AND s.id = i.alvo_id"
            " WHERE i.compra_id = ? ORDER BY i.id", (id_,)).fetchall()
    dados = dict(linha)
    dados["itens"] = [dict(i) for i in itens]
    return dados


def _desfazer_compra(conn, id_: int) -> set[tuple[str, int]]:
    """Tira do estoque o que a compra tinha posto. Devolve o que foi tocado."""
    tocados = set()
    for m in conn.execute("SELECT * FROM movimentos WHERE compra_id = ?", (id_,)).fetchall():
        tabela, coluna = CAMPO_SALDO[m["tipo"]]
        conn.execute(f"UPDATE {tabela} SET {coluna} = {coluna} - ? WHERE id = ?",
                     (m["quantidade"], m["alvo_id"]))
        tocados.add((m["tipo"], m["alvo_id"]))
    conn.execute("DELETE FROM movimentos WHERE compra_id = ?", (id_,))
    conn.execute("DELETE FROM compra_itens WHERE compra_id = ?", (id_,))
    return tocados


def salvar_compra(dados: dict, autor: str, id_: int | None = None,
                  itens: list[dict] | None = None) -> int:
    itens = [i for i in (itens or []) if i.get("alvo_id") and i.get("quantidade")]
    if not itens:
        raise ErroDeCampo("item_tipo", "A compra precisa de pelo menos um item com "
                                       "quantidade — é o item que move o estoque e "
                                       "corrige o preço.")
    campos = dict(
        data=_limpo(dados.get("data")) or agora()[:10],
        fornecedor=_limpo(dados.get("fornecedor")),
        nota=_limpo(dados.get("nota")),
        observacao=_limpo(dados.get("observacao")),
        valor=round(sum(float(i["valor"]) for i in itens), 2),
    )
    with conectar() as conn:
        tocados = set()
        if id_:
            if not conn.execute("SELECT 1 FROM compras WHERE id = ?", (id_,)).fetchone():
                raise ValueError("compra nao encontrada")
            tocados |= _desfazer_compra(conn, id_)
            conn.execute(
                "UPDATE compras SET data=:data, fornecedor=:fornecedor, nota=:nota,"
                " observacao=:observacao, valor=:valor WHERE id=:id", {**campos, "id": id_})
        else:
            cur = conn.execute(
                "INSERT INTO compras (data, fornecedor, nota, observacao, valor, criado_em,"
                " criado_por) VALUES (:data, :fornecedor, :nota, :observacao, :valor,"
                " :criado_em, :criado_por)",
                {**campos, "criado_em": agora(), "criado_por": autor})
            id_ = int(cur.lastrowid)

        for i in itens:
            conn.execute(
                "INSERT INTO compra_itens (compra_id, tipo, alvo_id, quantidade, valor)"
                " VALUES (?, ?, ?, ?, ?)",
                (id_, i["tipo"], int(i["alvo_id"]), float(i["quantidade"]), float(i["valor"])))
            _lancar(conn, i["tipo"], int(i["alvo_id"]), float(i["quantidade"]), "compra",
                    autor, observacao=campos["fornecedor"], compra_id=id_)
            tocados.add((i["tipo"], int(i["alvo_id"])))

        for tipo, alvo in tocados:
            _atualizar_preco(conn, tipo, alvo)
        conn.commit()
    return id_


def apagar_compra(id_: int) -> None:
    with conectar() as conn:
        tocados = _desfazer_compra(conn, id_)
        conn.execute("DELETE FROM compras WHERE id = ?", (id_,))
        for tipo, alvo in tocados:
            _atualizar_preco(conn, tipo, alvo)
        conn.commit()
