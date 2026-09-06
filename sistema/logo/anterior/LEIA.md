# O que era antes da junção

Estes arquivos vieram do `morumbi3d_web` como ele rodava sozinho no VPS.
Nenhum deles está em uso: cada um foi substituído por um equivalente que
agora serve o sistema inteiro, e não só o gerador de logo.

| Arquivo aqui | Quem faz o trabalho hoje |
| --- | --- |
| `wsgi.py` | [`/wsgi.py`](../../../wsgi.py) — monta painel, letreiros e logo juntos |
| `gunicorn.conf.py` | [`/gunicorn.conf.py`](../../../gunicorn.conf.py) — igual, mas 1 worker por padrão |
| `requirements.txt` | [`/requirements.txt`](../../../requirements.txt) — as duas listas somadas |
| `morumbi3d.service` | [`/implantar/morumbi3d.service`](../../implantar/morumbi3d.service) |
| `IMPLANTAR.txt`, `COMO_RODAR.txt` | [`/implantar/README.md`](../../implantar/README.md) |
| `nginx-morumbi3d.conf` | nada: quem faz o proxy hoje é o Caddy, em container |

Estão guardados porque só existiam no VPS, e a instalação lá vai ser
substituída. Nada aqui é lido pelo sistema — são referência.

O `CLAUDE.md` que veio junto foi para a raiz do repositório, e não para cá:
ele continua valendo, e é onde estão as regras de geometria e as
armadilhas do trimesh que o código todo respeita.
