"""Catalogo local de candidatos (SQLite, sem servidor).

Guarda tudo o que foi encontrado, com licenca, analise de malha, orcamento e
status de curadoria — para nao baixar duas vezes o mesmo modelo e para
responder perguntas do tipo "o que ja aprovei para a linha churrasco?" sem ir
a internet (secao 3.4 da especificacao).
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from .brands import normalizar
from .config import Config
from .licensing import Licenca, RiscoMarca, classificar, avaliar_risco
from .mesh import RelatorioMalha
from .models import Candidato, STATUS_NOVO, STATUS_VALIDOS
from .pricing import Orcamento

ESQUEMA = """
CREATE TABLE IF NOT EXISTS modelos (
    id                INTEGER PRIMARY KEY,
    fonte             TEXT NOT NULL,
    fonte_id          TEXT NOT NULL,
    titulo            TEXT NOT NULL,
    url               TEXT NOT NULL,
    autor             TEXT DEFAULT '',
    descricao         TEXT DEFAULT '',
    tags              TEXT DEFAULT '[]',
    formatos          TEXT DEFAULT '[]',
    gratuito          INTEGER,
    preco             REAL,
    downloads         INTEGER,
    curtidas          INTEGER,
    thumb_url         TEXT DEFAULT '',
    thumb_local       TEXT DEFAULT '',
    arquivo_url       TEXT DEFAULT '',
    arquivo_local     TEXT DEFAULT '',
    licenca_raw       TEXT DEFAULT '',
    licenca_codigo    TEXT DEFAULT 'DESCONHECIDA',
    licenca_nome      TEXT DEFAULT '',
    licenca_comercial TEXT DEFAULT 'desconhecido',
    licenca_atribuicao INTEGER DEFAULT 0,
    licenca_share_alike INTEGER DEFAULT 0,
    licenca_sem_derivados INTEGER DEFAULT 0,
    licenca_obs       TEXT DEFAULT '[]',
    risco_nivel       TEXT DEFAULT 'nenhum',
    risco_termos      TEXT DEFAULT '[]',
    risco_mensagem    TEXT DEFAULT '',
    linha             TEXT DEFAULT 'Sem linha',
    colecao           TEXT DEFAULT '',
    status            TEXT DEFAULT 'novo',
    motivo            TEXT DEFAULT '',
    chave_dedupe      TEXT DEFAULT '',
    duplicado_de      INTEGER,
    termo_busca       TEXT DEFAULT '',
    criado_em         TEXT NOT NULL,
    atualizado_em     TEXT NOT NULL,
    UNIQUE (fonte, fonte_id)
);
CREATE INDEX IF NOT EXISTS ix_modelos_status ON modelos (status);
CREATE INDEX IF NOT EXISTS ix_modelos_linha ON modelos (linha, colecao);
CREATE INDEX IF NOT EXISTS ix_modelos_dedupe ON modelos (chave_dedupe);

CREATE TABLE IF NOT EXISTS analises (
    id            INTEGER PRIMARY KEY,
    modelo_id     INTEGER NOT NULL REFERENCES modelos (id) ON DELETE CASCADE,
    arquivo       TEXT DEFAULT '',
    relatorio     TEXT NOT NULL,
    orcamento     TEXT DEFAULT '{}',
    nota          INTEGER DEFAULT 0,
    criado_em     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_analises_modelo ON analises (modelo_id);

CREATE TABLE IF NOT EXISTS buscas (
    id          INTEGER PRIMARY KEY,
    termo       TEXT NOT NULL,
    variantes   TEXT DEFAULT '[]',
    fontes      TEXT DEFAULT '[]',
    encontrados INTEGER DEFAULT 0,
    novos       INTEGER DEFAULT 0,
    erros       TEXT DEFAULT '[]',
    criado_em   TEXT NOT NULL
);
"""

_STOPWORDS = {
    "de", "da", "do", "das", "dos", "para", "com", "the", "a", "o", "and",
    "of", "for", "in", "3d", "print", "printable", "stl", "model", "modelo",
    "v1", "v2", "remix",
}


def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def chave_dedupe(titulo: str, autor: str = "") -> str:
    """Assinatura estavel de um modelo, para reconhece-lo em outra fonte."""

    palavras = sorted(
        {p for p in normalizar(titulo).split() if p and p not in _STOPWORDS}
    )
    return f"{'-'.join(palavras)}|{normalizar(autor)}"


class Catalogo:
    """Acesso ao banco. Use como context manager."""

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        cfg.preparar_diretorios()
        self.conn = sqlite3.connect(cfg.banco)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(ESQUEMA)
        self.conn.commit()

    # ------------------------------------------------------------------ util
    def __enter__(self) -> "Catalogo":
        return self

    def __exit__(self, *exc) -> None:
        self.fechar()

    def fechar(self) -> None:
        self.conn.close()

    @contextmanager
    def transacao(self) -> Iterator[sqlite3.Connection]:
        try:
            yield self.conn
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    # -------------------------------------------------------------- escrita
    def registrar(
        self,
        candidato: Candidato,
        termo_busca: str = "",
        licenca: Licenca | None = None,
        risco: RiscoMarca | None = None,
        linha: str = "",
        colecao: str = "",
    ) -> tuple[int, bool]:
        """Insere (ou atualiza) um candidato. Devolve ``(id, era_novo)``."""

        from .lines import classificar as classificar_linha

        licenca = licenca or classificar(candidato.licenca_raw)
        risco = risco or avaliar_risco(
            candidato.titulo, candidato.descricao, candidato.tags, self.cfg.raiz
        )
        if not linha:
            linha, colecao, _ = classificar_linha(
                candidato.titulo, candidato.descricao, candidato.tags
            )

        chave = chave_dedupe(candidato.titulo, candidato.autor)
        instante = agora()
        existente = self.conn.execute(
            "SELECT id, status FROM modelos WHERE fonte = ? AND fonte_id = ?",
            (candidato.fonte, candidato.fonte_id),
        ).fetchone()

        dados = {
            "fonte": candidato.fonte,
            "fonte_id": candidato.fonte_id,
            "titulo": candidato.titulo,
            "url": candidato.url,
            "autor": candidato.autor,
            "descricao": candidato.descricao,
            "tags": json.dumps(candidato.tags, ensure_ascii=False),
            "formatos": json.dumps(candidato.formatos, ensure_ascii=False),
            "gratuito": None if candidato.gratuito is None else int(candidato.gratuito),
            "preco": candidato.preco,
            "downloads": candidato.downloads,
            "curtidas": candidato.curtidas,
            "thumb_url": candidato.thumb_url,
            "arquivo_url": candidato.arquivo_url,
            "licenca_raw": licenca.raw,
            "licenca_codigo": licenca.codigo,
            "licenca_nome": licenca.nome,
            "licenca_comercial": licenca.comercial,
            "licenca_atribuicao": int(licenca.atribuicao),
            "licenca_share_alike": int(licenca.share_alike),
            "licenca_sem_derivados": int(licenca.sem_derivados),
            "licenca_obs": json.dumps(list(licenca.observacoes), ensure_ascii=False),
            "risco_nivel": risco.nivel,
            "risco_termos": json.dumps([list(t) for t in risco.termos], ensure_ascii=False),
            "risco_mensagem": risco.mensagem,
            "linha": linha or "Sem linha",
            "colecao": colecao,
            "chave_dedupe": chave,
            "termo_busca": termo_busca,
            "atualizado_em": instante,
        }

        with self.transacao() as conn:
            if existente:
                colunas = ", ".join(f"{k} = :{k}" for k in dados)
                conn.execute(
                    f"UPDATE modelos SET {colunas} WHERE id = :id",
                    {**dados, "id": existente["id"]},
                )
                modelo_id, novo = existente["id"], False
            else:
                dados["criado_em"] = instante
                dados["status"] = STATUS_NOVO
                colunas = ", ".join(dados)
                marcadores = ", ".join(f":{k}" for k in dados)
                cur = conn.execute(
                    f"INSERT INTO modelos ({colunas}) VALUES ({marcadores})", dados
                )
                modelo_id, novo = int(cur.lastrowid), True

            gemeo = conn.execute(
                "SELECT id FROM modelos WHERE chave_dedupe = ? AND id != ? "
                "AND duplicado_de IS NULL ORDER BY id LIMIT 1",
                (chave, modelo_id),
            ).fetchone()
            if gemeo and chave.strip("|"):
                conn.execute(
                    "UPDATE modelos SET duplicado_de = ? WHERE id = ?",
                    (gemeo["id"], modelo_id),
                )
        return modelo_id, novo

    def salvar_analise(
        self,
        modelo_id: int,
        relatorio: RelatorioMalha,
        orcamento: Orcamento | None = None,
        arquivo_local: str = "",
    ) -> int:
        with self.transacao() as conn:
            cur = conn.execute(
                "INSERT INTO analises (modelo_id, arquivo, relatorio, orcamento, "
                "nota, criado_em) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    modelo_id,
                    arquivo_local or relatorio.arquivo,
                    json.dumps(relatorio.como_dict(), ensure_ascii=False),
                    json.dumps(orcamento.como_dict() if orcamento else {}, ensure_ascii=False),
                    relatorio.nota,
                    agora(),
                ),
            )
            if arquivo_local:
                conn.execute(
                    "UPDATE modelos SET arquivo_local = ?, atualizado_em = ? WHERE id = ?",
                    (arquivo_local, agora(), modelo_id),
                )
        return int(cur.lastrowid)

    def mudar_status(self, modelo_id: int, status: str, motivo: str = "") -> bool:
        if status not in STATUS_VALIDOS:
            raise ValueError(
                f"status invalido: {status!r} (use {', '.join(STATUS_VALIDOS)})"
            )
        with self.transacao() as conn:
            cur = conn.execute(
                "UPDATE modelos SET status = ?, motivo = ?, atualizado_em = ? WHERE id = ?",
                (status, motivo, agora(), modelo_id),
            )
        return cur.rowcount > 0

    def salvar_thumb(self, modelo_id: int, caminho: str) -> None:
        with self.transacao() as conn:
            conn.execute(
                "UPDATE modelos SET thumb_local = ?, atualizado_em = ? WHERE id = ?",
                (caminho, agora(), modelo_id),
            )

    def registrar_busca(
        self,
        termo: str,
        variantes: list[str],
        fontes: list[str],
        encontrados: int,
        novos: int,
        erros: list[str],
    ) -> None:
        with self.transacao() as conn:
            conn.execute(
                "INSERT INTO buscas (termo, variantes, fontes, encontrados, novos, "
                "erros, criado_em) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    termo,
                    json.dumps(variantes, ensure_ascii=False),
                    json.dumps(fontes, ensure_ascii=False),
                    encontrados,
                    novos,
                    json.dumps(erros, ensure_ascii=False),
                    agora(),
                ),
            )

    # -------------------------------------------------------------- leitura
    def obter(self, modelo_id: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM modelos WHERE id = ?", (modelo_id,)
        ).fetchone()

    def ultima_analise(self, modelo_id: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM analises WHERE modelo_id = ? ORDER BY id DESC LIMIT 1",
            (modelo_id,),
        ).fetchone()

    def listar(
        self,
        status: str | None = None,
        linha: str | None = None,
        colecao: str | None = None,
        texto: str | None = None,
        fonte: str | None = None,
        so_seguros: bool = False,
        so_gratuitos: bool = False,
        incluir_duplicados: bool = False,
        limite: int = 50,
        ordem: str = "recentes",
    ) -> list[sqlite3.Row]:
        sql = ["SELECT * FROM modelos WHERE 1 = 1"]
        params: list = []
        if status:
            sql.append("AND status = ?")
            params.append(status)
        if linha:
            sql.append("AND linha = ?")
            params.append(linha)
        if colecao:
            sql.append("AND colecao = ?")
            params.append(colecao)
        if fonte:
            sql.append("AND fonte = ?")
            params.append(fonte)
        if texto:
            sql.append("AND (LOWER(titulo) LIKE ? OR LOWER(descricao) LIKE ? OR LOWER(tags) LIKE ?)")
            alvo = f"%{texto.lower()}%"
            params.extend([alvo, alvo, alvo])
        if so_seguros:
            sql.append("AND licenca_comercial = 'permitido' AND risco_nivel = 'nenhum'")
        if so_gratuitos:
            sql.append("AND (gratuito = 1 OR gratuito IS NULL)")
        if not incluir_duplicados:
            sql.append("AND duplicado_de IS NULL")
        ordens = {
            "recentes": "ORDER BY atualizado_em DESC, id DESC",
            "titulo": "ORDER BY titulo COLLATE NOCASE",
            "populares": "ORDER BY COALESCE(downloads, 0) DESC, COALESCE(curtidas, 0) DESC",
        }
        sql.append(ordens.get(ordem, ordens["recentes"]))
        sql.append("LIMIT ?")
        params.append(max(1, limite))
        return list(self.conn.execute(" ".join(sql), params).fetchall())

    def estatisticas(self) -> dict:
        linhas = self.conn.execute(
            "SELECT status, COUNT(*) AS n FROM modelos WHERE duplicado_de IS NULL "
            "GROUP BY status"
        ).fetchall()
        por_status = {r["status"]: r["n"] for r in linhas}
        total = sum(por_status.values())
        seguros = self.conn.execute(
            "SELECT COUNT(*) AS n FROM modelos WHERE duplicado_de IS NULL "
            "AND licenca_comercial = 'permitido' AND risco_nivel = 'nenhum'"
        ).fetchone()["n"]
        bloqueados = self.conn.execute(
            "SELECT COUNT(*) AS n FROM modelos WHERE duplicado_de IS NULL "
            "AND (licenca_comercial != 'permitido' OR risco_nivel != 'nenhum')"
        ).fetchone()["n"]
        duplicados = self.conn.execute(
            "SELECT COUNT(*) AS n FROM modelos WHERE duplicado_de IS NOT NULL"
        ).fetchone()["n"]
        por_linha = {
            r["linha"]: r["n"]
            for r in self.conn.execute(
                "SELECT linha, COUNT(*) AS n FROM modelos WHERE duplicado_de IS NULL "
                "GROUP BY linha ORDER BY n DESC"
            ).fetchall()
        }
        por_fonte = {
            r["fonte"]: r["n"]
            for r in self.conn.execute(
                "SELECT fonte, COUNT(*) AS n FROM modelos GROUP BY fonte ORDER BY n DESC"
            ).fetchall()
        }
        return {
            "total": total,
            "por_status": por_status,
            "seguros_para_venda": seguros,
            "bloqueados": bloqueados,
            "duplicados": duplicados,
            "por_linha": por_linha,
            "por_fonte": por_fonte,
        }


def abrir(cfg: Config) -> Catalogo:
    return Catalogo(cfg)
