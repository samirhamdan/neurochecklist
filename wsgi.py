"""Entrada do gunicorn: um processo servindo o sistema inteiro.

Por que um so e nao dois servicos: cada processo Python carrega opencv,
numpy, scipy e trimesh por conta propria — uns 300 a 400 MB. Numa maquina de
2 GB, dois servicos disputam a mesma memoria e o teto de 800 MB do
morumbi3d.service passa a valer para cada um deles separadamente. Junto, e um
teto so, uma configuracao so, um deploy so.

    /            painel e entrada        (sistema)
    /letreiros   gerador de letreiros    (arquivo unico, roda no navegador)
    /logo        gerador de logo 3D      (o morumbi3d_web, montado aqui)

A porta de autenticacao e UNICA: a sessao do sistema. O Basic auth que o
gerador de logo trazia sai de cena — dois cadeados na mesma porta so fariam o
navegador pedir senha duas vezes.
"""

from __future__ import annotations

import os
import traceback

from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.utils import redirect

from sistema import auth
from sistema.app import criar_app

sistema = criar_app()


def _explicar_falha(motivo: str):
    """App minimo que ocupa /logo quando o gerador nao pode ser carregado.

    Melhor uma pagina dizendo qual dependencia falta do que o sistema
    inteiro deixar de subir por causa de um gerador.
    """

    def aplicacao(environ, start_response):
        corpo = (
            "<!doctype html><meta charset='utf-8'>"
            "<title>Gerador de logo indisponível</title>"
            "<body style='font:16px/1.6 system-ui;max-width:60ch;margin:60px auto;padding:0 20px'>"
            "<h1 style='font-size:22px'>Gerador de logo indisponível</h1>"
            "<p>O sistema está no ar, mas este gerador não carregou:</p>"
            f"<pre style='background:#f4f2ee;padding:12px;overflow:auto;font-size:13px'>{motivo}</pre>"
            "<p>Quase sempre é dependência faltando. No servidor:</p>"
            "<pre style='background:#f4f2ee;padding:12px'>/opt/morumbi3d/venv/bin/pip install -r requirements.txt\n"
            "systemctl restart morumbi3d</pre>"
            "<p><a href='/'>Voltar ao painel</a></p></body>"
        ).encode("utf-8")
        start_response("503 Service Unavailable",
                       [("Content-Type", "text/html; charset=utf-8"),
                        ("Content-Length", str(len(corpo)))])
        return [corpo]

    return aplicacao


def _com_sessao(interno):
    """Exige a sessao do sistema antes de deixar passar para o app montado.

    Roda no nivel do WSGI porque o app de dentro nao conhece a sessao do de
    fora. Usa o contexto de requisicao do proprio Flask do sistema, entao a
    leitura do cookie assinado e a mesma do resto do sistema — nada de
    decodificar cookie na mao aqui.
    """

    def guarda(environ, start_response):
        with sistema.request_context(environ):
            if not auth.autenticado():
                # O DispatcherMiddleware ja tirou o /logo do PATH_INFO e o
                # guardou em SCRIPT_NAME; juntar os dois devolve o endereco
                # que a pessoa pediu, para voltar aqui depois de entrar.
                pedido = environ.get("SCRIPT_NAME", "") + environ.get("PATH_INFO", "")
                resposta = redirect(f"/entrar?destino={pedido or '/'}")
                return resposta(environ, start_response)
        return interno(environ, start_response)

    return guarda


def montar_logo():
    try:
        from sistema.logo import app as modulo_logo
    except Exception:
        return _explicar_falha(traceback.format_exc(limit=3))

    # O cadeado do gerador de logo sai: quem guarda a porta agora e a sessao
    # do sistema, no _com_sessao acima. Deixar os dois faria o navegador pedir
    # Basic auth por cima de quem ja entrou.
    modulo_logo.SENHA = ""
    return _com_sessao(modulo_logo.app.wsgi_app)


app = DispatcherMiddleware(sistema.wsgi_app, {"/logo": montar_logo()})
sistema.wsgi_app = app   # para o servidor de desenvolvimento tambem enxergar


if __name__ == "__main__":
    bind = os.environ.get("MORUMBI_BIND", "127.0.0.1:5000")
    host, _, porta = bind.rpartition(":")
    sistema.run(host=host or "127.0.0.1", port=int(porta or 5000), debug=False)
