"""Autenticacao do sistema de gestao.

O gerador de logo usa Basic auth — o popup do navegador. Aqui a entrada e
por formulario, com sessao, porque uma tela de login precisa poder dizer o
que aconteceu quando da errado, e o popup nao diz.

O que se manteve do que ja existia: as mesmas variaveis MORUMBI_USUARIO e
MORUMBI_SENHA (nenhuma configuracao nova para administrar) e a comparacao em
tempo constante com hmac.compare_digest.
"""

from __future__ import annotations

import functools
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from flask import redirect, request, session, url_for

from .dados import PASTA, conectar

USUARIO = os.environ.get("MORUMBI_USUARIO", "")
SENHA = os.environ.get("MORUMBI_SENHA", "")

# Quantas tentativas erradas o mesmo endereco pode fazer antes de esperar.
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
    """Sem senha, o sistema so aceita subir preso ao proprio computador.

    O gerador de logo prometia isso num comentario mas nao verificava: sem
    MORUMBI_SENHA ele simplesmente liberava tudo, inclusive publicado na
    internet. Aqui a promessa e checada.
    """

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
    """Chave que assina o cookie, guardada em disco.

    Em memoria ela mudaria a cada restart e derrubaria todo mundo; e cada
    worker do gunicorn geraria a sua, entao a sessao valeria num processo e
    nao no outro.
    """

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
    """IP real do visitante. Atras do Caddy, o do proxy nao serve."""

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
    """Anota uma tentativa errada. Devolve quantas restam."""

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


def confere(usuario: str, senha: str) -> bool:
    """Compara em tempo constante, e sempre os dois campos.

    Sair mais cedo quando o usuario esta errado deixaria o tempo de resposta
    contar quem existe e quem nao existe.
    """

    ok_usuario = hmac.compare_digest(usuario or "", USUARIO)
    ok_senha = hmac.compare_digest(senha or "", SENHA)
    return ok_usuario and ok_senha


def autenticado() -> bool:
    if not SENHA:
        return True   # modo local, ja barrado por verificar_configuracao
    return session.get("usuario") == USUARIO


def exige_login(rota):
    @functools.wraps(rota)
    def envelope(*a, **kw):
        if not autenticado():
            return redirect(url_for("entrar", destino=request.full_path.rstrip("?")))
        return rota(*a, **kw)
    return envelope
