# -*- coding: utf-8 -*-
"""
Configuracao do gunicorn para o gerador de logo 3D.

Os numeros aqui sao pensados para VPS pequeno. Cada worker carrega
opencv, numpy, trimesh e matplotlib, o que da uns 300 a 400 MB de RAM
por processo. Em maquina de 1 GB use 1 worker; de 2 GB para cima, 2.
"""
import os

bind = os.environ.get("MORUMBI_BIND", "127.0.0.1:5000")

# Workers em processo separado. Ajuste conforme a RAM da maquina.
workers = int(os.environ.get("MORUMBI_WORKERS", "2"))

# Gerar STL de logo complexo passa facil de 30s, que e o padrao.
timeout = 180
graceful_timeout = 30

# Recicla o worker de tempos em tempos. Bibliotecas cientificas
# fragmentam memoria com o uso; reciclar segura o consumo estavel
# sem derrubar requisicao no meio.
max_requests = 200
max_requests_jitter = 25

# Upload de 25 MB em conexao lenta nao pode ser cortado.
keepalive = 5

accesslog = "-"
errorlog = "-"
loglevel = "info"
