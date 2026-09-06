#!/usr/bin/env bash
# Troca a instalacao solta do VPS pelo repositorio git, UMA VEZ.
# Roda NO VPS, como root:
#
#   bash instalar.sh git@github-morumbi3d:samirhamdan/morumbi3d.git
#
# O que ele preserva, sem pedir licenca:
#
#   * venv/            -- 180 MB de biblioteca ja instalada. Refazer num VPS
#                         de 2 GB demora e as vezes falha por falta de RAM;
#   * /var/lib/morumbi3d  -- os uploads e o banco. Nao encosta;
#   * morumbi3d.service   -- a senha real, o bind do Docker e os limites
#                         desta maquina moram nele. So mexe no WORKERS, e
#                         guarda copia antes.
#
# Se o servico nao voltar, ele DESFAZ TUDO sozinho: devolve os arquivos
# antigos, devolve o servico e reinicia. Voce fica como estava.
set -euo pipefail

URL="${1:-}"
REPO="${MORUMBI_REPO:-/opt/morumbi3d}"
BRANCH="${2:-main}"
SERVICO="${MORUMBI_SERVICO:-morumbi3d}"
UNIDADE="${MORUMBI_UNIDADE:-/etc/systemd/system/$SERVICO.service}"
DONO="${MORUMBI_DONO:-morumbi:morumbi}"
SYSTEMCTL="${SYSTEMCTL:-systemctl}"
CURL="${CURL:-curl}"

if [ -z "$URL" ]; then
  echo "uso: $0 <url-do-repositorio> [branch]" >&2
  exit 2
fi
if [ ! -d "$REPO" ]; then
  echo "ERRO: $REPO nao existe. E esta mesmo no VPS certo?" >&2
  exit 1
fi
if [ -d "$REPO/.git" ]; then
  echo "$REPO ja veio do git. Para atualizar use:  $REPO/implantar/atualizar.sh"
  exit 0
fi

CARIMBO=$(date +%Y%m%d-%H%M%S)
BACKUP="/root/morumbi3d-antes-da-juncao-$CARIMBO.tar.gz"
TMP=$(mktemp -d)
limpar() { rm -rf "$TMP"; }
trap limpar EXIT

echo "==> 1/6  Copia de seguranca em $BACKUP"
# --exclude tem que vir ANTES do alvo: depois, o tar ignora e sai com erro.
tar czf "$BACKUP" --exclude=venv --exclude=__pycache__ \
    -C "$(dirname "$REPO")" "$(basename "$REPO")"
cp -a "$UNIDADE" "$BACKUP.service" 2>/dev/null || true
echo "    guardado. O servico tambem: $BACKUP.service"

# Git 2.35.6 em diante recusa mexer em repositorio cujos arquivos sao de
# outro dono ("dubious ownership"). Aqui isso e o arranjo normal e nao o
# ataque que a checagem existe para pegar: os arquivos pertencem ao usuario
# do servico (o gunicorn roda como ele) e quem administra e o root. Marcar
# uma vez, sem duplicar a linha a cada execucao.
if ! git config --global --get-all safe.directory 2>/dev/null | grep -qxF "$REPO"; then
  git config --global --add safe.directory "$REPO"
fi

echo "==> 2/6  Baixando o repositorio (nada mudou em $REPO ainda)"
git clone --quiet --branch "$BRANCH" "$URL" "$TMP/novo"
for obrigatorio in wsgi.py gunicorn.conf.py requirements.txt sistema/logo/app.py; do
  if [ ! -e "$TMP/novo/$obrigatorio" ]; then
    echo "ERRO: o repositorio nao tem $obrigatorio. Nao e o repo certo." >&2
    exit 1
  fi
done

# Daqui em diante $REPO e mexido. Qualquer falha desfaz.
desfazer() {
  echo >&2
  echo "!!! Algo falhou. Desfazendo." >&2
  find "$REPO" -mindepth 1 -maxdepth 1 -not -name venv -exec rm -rf {} +
  tar xzf "$BACKUP" -C "$(dirname "$REPO")"
  [ -e "$BACKUP.service" ] && cp -a "$BACKUP.service" "$UNIDADE"
  "$SYSTEMCTL" daemon-reload || true
  "$SYSTEMCTL" restart "$SERVICO" || true
  echo "Voltou para como estava. A copia continua em $BACKUP" >&2
}
trap 'desfazer; limpar' ERR

echo "==> 3/6  Trocando os arquivos (o venv fica)"
find "$REPO" -mindepth 1 -maxdepth 1 -not -name venv -exec rm -rf {} +
find "$TMP/novo" -mindepth 1 -maxdepth 1 -exec mv {} "$REPO/" \;
chown -R "$DONO" "$REPO" 2>/dev/null || true

echo "==> 4/6  Conferindo as bibliotecas"
# Quase tudo ja esta no venv. Na pratica isto instala so networkx e rtree,
# que o trimesh usa para contar corpos e cortar peca grande.
"$REPO/venv/bin/pip" install --quiet -r "$REPO/requirements.txt"

echo "==> 5/6  Ajustando o servico"
# O ExecStart NAO muda: wsgi.py e gunicorn.conf.py ficaram na raiz, que ja
# e o WorkingDirectory. So o numero de workers precisa cair: o processo
# agora carrega painel e gerador juntos.
if grep -q 'MORUMBI_WORKERS=[^1]' "$UNIDADE" 2>/dev/null; then
  sed -i 's/MORUMBI_WORKERS=[0-9]\+/MORUMBI_WORKERS=1/' "$UNIDADE"
  echo "    MORUMBI_WORKERS baixado para 1 (o processo ficou mais pesado)"
  "$SYSTEMCTL" daemon-reload
else
  echo "    nada a mudar."
fi

BIND=$("$SYSTEMCTL" show "$SERVICO" -p Environment --value 2>/dev/null \
       | tr ' ' '\n' | sed -n 's/^MORUMBI_BIND=//p' | head -1)
BIND="${BIND:-127.0.0.1:5000}"

echo "==> 6/6  Reiniciando e conferindo em http://$BIND/saude"
"$SYSTEMCTL" restart "$SERVICO"
echo -n "    aguardando o servico subir (leva uns 10s, ele carrega opencv e trimesh)"
OK=0
for _ in $(seq 1 20); do
  # -s sem -S: enquanto o gunicorn carrega, a recusa de conexao e esperada,
  # nao e erro. Imprimir cada tentativa fazia um deploy BEM SUCEDIDO mostrar
  # "Failed to connect" em vermelho logo antes de "Pronto, esta no ar" --
  # assustador e sem motivo. Se as 20 falharem, a tentativa final abaixo
  # mostra o erro de verdade.
  if "$CURL" -fs -o /dev/null --max-time 4 "http://$BIND/saude"; then OK=1; break; fi
  echo -n "."
  sleep 2
done
echo

if [ "$OK" != "1" ]; then
  trap - ERR   # a partir daqui quem desfaz sou eu, e nao o trap
  echo "ERRO: o servico nao respondeu em 40 segundos. O motivo:" >&2
  "$CURL" -fsS -o /dev/null --max-time 4 "http://$BIND/saude" || true
  desfazer
  echo "Veja o que aconteceu:  journalctl -u $SERVICO -n 50" >&2
  exit 1
fi

trap limpar ERR
cat <<FIM

==============================================================
 Pronto. O sistema esta no ar.
==============================================================

    https://morumbi3d.duckdns.org/          painel (pede senha)
    https://morumbi3d.duckdns.org/letreiros gerador de letreiro
    https://morumbi3d.duckdns.org/logo/     gerador de logo, como sempre

A senha e a mesma de antes, mas agora vem numa tela de entrada, e nao
mais naquele popup do navegador.

Daqui em diante, para atualizar:

    $REPO/implantar/atualizar.sh

Se algo estiver errado, para voltar ao que era:

    systemctl stop $SERVICO
    find $REPO -mindepth 1 -maxdepth 1 -not -name venv -exec rm -rf {} +
    tar xzf $BACKUP -C $(dirname "$REPO")
    cp -a $BACKUP.service $UNIDADE
    systemctl daemon-reload && systemctl start $SERVICO
FIM
