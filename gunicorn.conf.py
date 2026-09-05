# -*- coding: utf-8 -*-
"""Configuracao do gunicorn para o sistema inteiro.

Um processo serve as tres coisas: painel, gerador de letreiros e gerador de
logo. Cada worker carrega opencv, numpy, scipy e trimesh por conta propria —
uns 300 a 400 MB. Por isso o padrao aqui e 1, e nao 2 como era quando o
gerador de logo rodava sozinho: agora o mesmo processo carrega mais coisa.
Suba para 2 so em maquina com 4 GB ou mais.
"""
import os

bind = os.environ.get("MORUMBI_BIND", "127.0.0.1:5000")
workers = int(os.environ.get("MORUMBI_WORKERS", "1"))

# Gerar STL de logo complexo passa facil de 30s, que e o padrao do gunicorn.
timeout = 180
graceful_timeout = 30

# Bibliotecas cientificas fragmentam memoria com o uso. Reciclar o worker de
# tempos em tempos segura o consumo estavel sem derrubar requisicao no meio.
max_requests = 200
max_requests_jitter = 25

# Upload de 25 MB em conexao lenta nao pode ser cortado.
keepalive = 5

accesslog = "-"
errorlog = "-"
loglevel = "info"
