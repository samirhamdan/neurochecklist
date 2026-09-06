#!/usr/bin/env bash
# Atualiza a instalacao do VPS a partir do git. Roda NO VPS, como root.
#
#   /opt/morumbi3d/implantar/atualizar.sh            # branch padrao (main)
#   /opt/morumbi3d/implantar/atualizar.sh alguma-br  # outra branch
#
# O que ele NAO faz, de proposito:
#
#   * nao encosta em /etc/systemd/system/morumbi3d.service. O arquivo que
#     esta rodando tem a senha real, o bind do gateway do Docker e os
#     limites ajustados para esta maquina — coisas que o repositorio nao
#     sabe e nao deve saber. Sobrescrever derruba o site;
#   * nao roda `git clean`. O venv mora dentro de /opt/morumbi3d e nao esta
#     versionado: um clean apagaria ele;
#   * nao mexe em /var/lib/morumbi3d, onde ficam os uploads.
set -euo pipefail

REPO="${MORUMBI_REPO:-/opt/morumbi3d}"
BRANCH="${1:-main}"
DONO="${MORUMBI_DONO:-morumbi:morumbi}"
SERVICO="${MORUMBI_SERVICO:-morumbi3d}"
SYSTEMCTL="${SYSTEMCTL:-systemctl}"
CURL="${CURL:-curl}"

cd "$REPO"

if [ ! -d .git ]; then
  echo "ERRO: $REPO nao e um clone git. Rode implantar/instalar.sh primeiro." >&2
  exit 1
fi

# O endereco de escuta sai do proprio servico: em producao ele e o gateway
# do Docker (172.18.0.1), nao 127.0.0.1, porque quem faz o proxy e o Caddy
# de dentro de um container. Chutar isso aqui daria um teste que passa com
# o site fora do ar.
BIND=$("$SYSTEMCTL" show "$SERVICO" -p Environment --value 2>/dev/null \
       | tr ' ' '\n' | sed -n 's/^MORUMBI_BIND=//p' | head -1)
BIND="${BIND:-127.0.0.1:5000}"

# Git 2.35.6 em diante recusa mexer em repositorio cujos arquivos sao de
# outro dono ("dubious ownership"). Aqui isso e o arranjo normal e nao o
# ataque que a checagem existe para pegar: os arquivos pertencem ao usuario
# do servico (o gunicorn roda como ele) e quem administra e o root. Marcar
# uma vez, sem duplicar a linha a cada execucao.
if ! git config --global --get-all safe.directory 2>/dev/null | grep -qxF "$REPO"; then
  git config --global --add safe.directory "$REPO"
fi

ANTES=$(git rev-parse HEAD)
echo "==> Estava em $(git log --oneline -1)"

git fetch --prune origin "$BRANCH"
DEPOIS=$(git rev-parse "origin/$BRANCH")

if [ "$ANTES" = "$DEPOIS" ]; then
  echo "==> Ja esta na ultima versao. Nada a fazer."
  exit 0
fi

echo "==> Mudancas que vao entrar:"
git log --oneline "$ANTES..$DEPOIS" | sed 's/^/      /'

# Mexida feita direto no servidor seria perdida agora: melhor avisar.
if ! git diff --quiet HEAD; then
  echo "AVISO: ha alteracao local nao commitada em $REPO. Ela sera descartada."
  git diff --stat HEAD | sed 's/^/      /'
  echo "       Guardei uma copia em /tmp/morumbi3d-local-$(date +%s).patch"
  git diff HEAD > "/tmp/morumbi3d-local-$(date +%s).patch"
fi

git checkout -q "$BRANCH" 2>/dev/null || git checkout -q -B "$BRANCH" "origin/$BRANCH"
git reset --hard "origin/$BRANCH"

# Dependencia so quando o requirements mudou: pip install a cada deploy
# gasta minutos e RAM que esta maquina nao tem sobrando.
if ! git diff --quiet "$ANTES" "$DEPOIS" -- requirements.txt 2>/dev/null; then
  echo "==> requirements.txt mudou: atualizando o venv"
  ./venv/bin/pip install --quiet -r requirements.txt
fi

chown -R "$DONO" "$REPO"

echo "==> Reiniciando $SERVICO"
"$SYSTEMCTL" restart "$SERVICO"

# Conferir que subiu. Sem isso, um deploy quebrado so aparece quando um
# cliente reclama.
# /saude responde sem senha; a raiz redirecionaria para a tela de entrada.
echo "==> Conferindo em http://$BIND/saude ..."
OK=0
for _ in $(seq 1 15); do
  if "$CURL" -fsS -o /dev/null --max-time 4 "http://$BIND/saude"; then OK=1; break; fi
  sleep 2
done

if [ "$OK" = "1" ]; then
  echo "==> No ar: $(git log --oneline -1)"
  exit 0
fi

echo "ERRO: o servico nao respondeu depois do restart. Voltando para $ANTES." >&2
git reset --hard "$ANTES"
chown -R "$DONO" "$REPO"
"$SYSTEMCTL" restart "$SERVICO"
echo "Voltou para a versao anterior. Veja o log:  journalctl -u $SERVICO -n 50" >&2
exit 1
