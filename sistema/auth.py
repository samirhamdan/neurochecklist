"""Autenticacao do sistema de gestao.

Dois modos, backwards compatible:

  1. Tabela `usuarios` com pelo menos um registro ativo: login contra o banco,
     senha conferida com werkzeug (bcrypt/scrypt). O perfil (admin, comercial,
     operacao) controla o que cada um ve.

  2. Fallback: variaveis MORUMBI_USUARIO / MORUMBI_SENHA, comparacao em tempo
     constante com hmac.compare_digest. Funciona enquanto a tabela nao existir
     ou estiver vazia — e o que mantem o sistema rodando na VPS ate o Samir
     criar o primeiro usuario pela tela.

A migracao em dados.py semeia o primeiro admin a partir das variaveis de
ambiente, entao em producao o modo 2 dura ate a primeira conexao com banco.
"""

from __future__ import annotations

import functools
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from flask import abort, redirect, request, session, url_for
from werkzeug.security import check_password_hash

from .dados import PASTA, conectar

USUARIO = os.environ.get("MORUMBI_USUARIO", "")
SENHA = os.environ.get("MORUMBI_SENHA", "")

LIMITE_TENTATIVAS = 5
JANELA_MINUTOS = 15

TABELA = """
CREATE TABLE IF NOT EXISTS tentativas_login (
    id      INTEGER PRIMARY KEY,
    ip      TEXT NOT NULL,
    quando  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_tentativas ON tentativas_login (ip, quando);
"""


class ConfiguracaoInsegura(RuntimeError):
    """Configuracao que exporia os dados. O app nao sobe assim."""


def _local(endereco: str) -> bool:
    return endereco.startswith(("127.", "localhost", "[::1]", "::1"))


def verificar_configuracao(bind: str | None = None) -> None:
    if SENHA:
        return
    bind = bind if bind is not None else os.environ.get("MORUMBI_BIND", "127.0.0.1:5000")
    if not _local(bind):
        raise ConfiguracaoInsegura(
            f"MORUMBI_SENHA nao esta definida e o sistema escutaria em {bind}, "
            "que nao e o proprio computador. Os pedidos e os dados de cliente "
            "ficariam abertos para quem alcancasse esse endereco.\n"
            "Defina MORUMBI_SENHA no servico, ou use MORUMBI_BIND=127.0.0.1:5000 "
            "para rodar so local."
        )


def chave_de_sessao() -> bytes:
    arquivo = PASTA / "chave_sessao"
    if arquivo.exists():
        dados = arquivo.read_bytes().strip()
        if len(dados) >= 32:
            return dados
    PASTA.mkdir(parents=True, exist_ok=True)
    chave = secrets.token_bytes(48)
    arquivo.write_bytes(chave)
    arquivo.chmod(0o600)
    return chave


def endereco_do_pedido() -> str:
    encaminhado = request.headers.get("X-Forwarded-For", "")
    if encaminhado:
        return encaminhado.split(",")[0].strip()
    return request.remote_addr or "desconhecido"


def _limpar_e_contar(conn, ip: str) -> int:
    corte = (datetime.now(timezone.utc) - timedelta(minutes=JANELA_MINUTOS)).isoformat()
    conn.execute("DELETE FROM tentativas_login WHERE quando < ?", (corte,))
    linha = conn.execute(
        "SELECT COUNT(*) AS n FROM tentativas_login WHERE ip = ?", (ip,)
    ).fetchone()
    return linha["n"]


def bloqueado(ip: str) -> bool:
    with conectar() as conn:
        conn.executescript(TABELA)
        return _limpar_e_contar(conn, ip) >= LIMITE_TENTATIVAS


def registrar_erro(ip: str) -> int:
    with conectar() as conn:
        conn.executescript(TABELA)
        conn.execute(
            "INSERT INTO tentativas_login (ip, quando) VALUES (?, ?)",
            (ip, datetime.now(timezone.utc).isoformat()),
        )
        return max(0, LIMITE_TENTATIVAS - _limpar_e_contar(conn, ip))


def limpar_tentativas(ip: str) -> None:
    with conectar() as conn:
        conn.executescript(TABELA)
        conn.execute("DELETE FROM tentativas_login WHERE ip = ?", (ip,))


def _tem_usuarios_no_banco() -> bool:
    try:
        with conectar() as conn:
            tabelas = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'")}
            if "usuarios" not in tabelas:
                return False
            return bool(conn.execute(
                "SELECT 1 FROM usuarios WHERE ativo = 1 LIMIT 1").fetchone())
    except Exception:
        return False


def confere(usuario: str, senha: str) -> dict | bool:
    """Confere credenciais. Devolve dict do usuario (banco) ou True (env) ou False."""
    if _tem_usuarios_no_banco():
        from . import dados
        reg = dados.usuario_por_login(usuario or "")
        if reg and check_password_hash(reg["senha_hash"], senha or ""):
            return reg
        return False

    ok_usuario = hmac.compare_digest(usuario or "", USUARIO)
    ok_senha = hmac.compare_digest(senha or "", SENHA)
    return ok_usuario and ok_senha


def autenticado() -> bool:
    if not SENHA and not _tem_usuarios_no_banco():
        return True
    return bool(session.get("usuario"))


def perfil_do_usuario() -> str:
    return session.get("perfil", "")


def exige_login(rota):
    @functools.wraps(rota)
    def envelope(*a, **kw):
        if not autenticado():
            return redirect(url_for("entrar", destino=request.full_path.rstrip("?")))
        return rota(*a, **kw)
    return envelope


def exige_perfil(*perfis):
    """Decorator que restringe a rota a certos perfis. Admin sempre entra."""
    def decorador(rota):
        @functools.wraps(rota)
        def envelope(*a, **kw):
            if not autenticado():
                return redirect(url_for("entrar", destino=request.full_path.rstrip("?")))
            atual = perfil_do_usuario()
            if atual and atual not in ("admin",) + perfis:
                abort(403)
            return rota(*a, **kw)
        return envelope
    return decorador
