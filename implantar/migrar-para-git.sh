#!/usr/bin/env bash
# Converte a instalacao do VPS (hoje uma pasta solta) em clone git, UMA VEZ.
# Roda NO VPS, como root:
#
#   bash migrar-para-git.sh git@github.com:samirhamdan/morumbi3d.git
#
# A armadilha que este script existe para evitar: o que esta rodando no VPS
# pode estar MAIS NOVO do que a copia que foi para o repositorio. Se voce
# apontar o git para /opt/morumbi3d e der um `git reset --hard`, a producao
# volta no tempo sem avisar. Entao aqui nada e sobrescrito: o script monta o
# git por cima dos arquivos existentes e MOSTRA a diferenca. Quem decide e
# voce, com a lista na frente.
set -euo pipefail

URL="${1:-}"
REPO="${MORUMBI_REPO:-/opt/morumbi3d}"
BRANCH="${2:-main}"
SUBPASTA="${MORUMBI_SUBPASTA:-sistema/logo}"   # onde o gerador de logo mora no repo

if [ -z "$URL" ]; then
  echo "uso: $0 <url-do-repositorio> [branch]" >&2
  exit 2
fi
if [ ! -d "$REPO" ]; then
  echo "ERRO: $REPO nao existe." >&2
  exit 1
fi
if [ -d "$REPO/.git" ]; then
  echo "$REPO ja e um clone git. Use implantar/atualizar.sh daqui em diante."
  exit 0
fi

CARIMBO=$(date +%Y%m%d-%H%M%S)
BACKUP="/root/morumbi3d-backup-$CARIMBO.tar.gz"
echo "==> Copia de seguranca em $BACKUP"
# --exclude tem que vir ANTES do alvo: depois, o tar ignora e sai com erro.
tar czf "$BACKUP" --exclude=venv --exclude=__pycache__ \
    -C "$(dirname "$REPO")" "$(basename "$REPO")"

TMP=$(mktemp -d)
echo "==> Buscando o repositorio (sem escrever nada em $REPO ainda)"
git clone --quiet --no-checkout --branch "$BRANCH" "$URL" "$TMP/git"

# Puxa so os arquivos, para comparar com o que esta rodando.
git -C "$TMP/git" archive "origin/$BRANCH" | (mkdir -p "$TMP/repo" && tar x -C "$TMP/repo")

echo
echo "==> Comparando o que esta RODANDO com o que esta no repositorio"
DIFERE=0
if [ -d "$TMP/repo/$SUBPASTA" ]; then
  while IFS= read -r arquivo; do
    nome=$(basename "$arquivo")
    if [ ! -e "$REPO/$nome" ] && [ ! -e "$REPO/${arquivo#"$TMP/repo/$SUBPASTA/"}" ]; then
      echo "    so no repositorio : ${arquivo#"$TMP/repo/$SUBPASTA/"}"
      DIFERE=1
    fi
  done < <(find "$TMP/repo/$SUBPASTA" -type f)

  while IFS= read -r arquivo; do
    rel="${arquivo#"$REPO/"}"
    alvo="$TMP/repo/$SUBPASTA/$rel"
    if [ ! -e "$alvo" ]; then
      echo "    so no servidor    : $rel"
      DIFERE=1
    elif ! cmp -s "$arquivo" "$alvo"; then
      echo "    DIFERENTE         : $rel"
      DIFERE=1
    fi
  done < <(find "$REPO" -type f -not -path "*/venv/*" -not -path "*/__pycache__/*")
else
  echo "    O repositorio nao tem a pasta '$SUBPASTA/'. Coloque o app Flask la antes."
  DIFERE=1
fi

if [ "$DIFERE" = "1" ]; then
  echo
  echo "PAREI AQUI, de proposito."
  echo
  echo "O que esta no servidor nao bate com o repositorio. Se eu conectasse o"
  echo "git agora, o primeiro deploy sobrescreveria essas diferencas — e se o"
  echo "servidor for o mais novo, voce perde trabalho."
  echo
  echo "O caminho seguro: leve o que esta RODANDO para o repositorio primeiro."
  echo "  1. no seu computador:  scp -r root@SERVIDOR:$REPO/'*' morumbi3d/$SUBPASTA/"
  echo "     (sem a pasta venv)"
  echo "  2. confira, commite e envie"
  echo "  3. rode este script de novo"
  echo
  echo "A copia de seguranca continua em $BACKUP"
  rm -rf "$TMP"
  exit 1
fi

echo "    tudo igual."

# No servidor o app mora na raiz de /opt/morumbi3d; no repositorio ele mora
# em $SUBPASTA/, porque o repositorio guarda mais coisa (o pacote Python, o
# gerador de letreiros, as ferramentas). Sem mover, o git veria todo arquivo
# como apagado-da-subpasta e recriado-na-raiz.
echo
echo "==> Movendo o app para $SUBPASTA/ (o venv fica onde esta)"
mkdir -p "$REPO/$SUBPASTA"
# A subpasta tem mais de um nivel ("sistema/logo"), mas o find abaixo lista
# so o primeiro. Comparar com $SUBPASTA inteiro nunca casaria, e o laco
# tentaria mover $REPO/sistema para dentro de $REPO/sistema/logo.
RAIZ_SUB="${SUBPASTA%%/*}"
while IFS= read -r item; do
  nome=$(basename "$item")
  [ "$nome" = "venv" ] && continue
  [ "$nome" = "$RAIZ_SUB" ] && continue
  mv "$item" "$REPO/$SUBPASTA/"
done < <(find "$REPO" -mindepth 1 -maxdepth 1)

echo "==> Conectando o git em $REPO"
mv "$TMP/git/.git" "$REPO/.git"
cd "$REPO"
git config core.bare false
# Seguro neste ponto: acabamos de conferir, arquivo a arquivo, que o app do
# servidor e identico ao do repositorio. O reset so traz o que falta (pacote
# Python, ferramentas, gerador de letreiros).
git reset --hard --quiet HEAD

RESTO=$(git status --porcelain)
if [ -n "$RESTO" ]; then
  echo "AVISO: sobrou diferenca depois de conectar:"
  echo "$RESTO" | sed "s/^/      /"
else
  echo "    arvore limpa: o que esta no disco e exatamente o do repositorio."
fi
rm -rf "$TMP"

cat <<FIM

Pronto. Falta UM ajuste manual, uma vez so.

O gerador de logo agora mora em $REPO/$SUBPASTA/, e quem sobe o servico e o
$REPO/wsgi.py, que serve o painel em / e o gerador em /logo/. Edite
/etc/systemd/system/morumbi3d.service:

    WorkingDirectory=$REPO
    ExecStart=$REPO/venv/bin/gunicorn -c $REPO/gunicorn.conf.py wsgi:app

Repare que o WorkingDirectory continua na RAIZ, e nao na subpasta: o wsgi.py
e o gunicorn.conf.py ficam la. Apontar para a subpasta faz o servico nao subir.

O sistema pede senha por formulario agora, e nao mais pelo popup do navegador.
Confira que MORUMBI_USUARIO e MORUMBI_SENHA continuam no arquivo: sem senha o
app se recusa a subir em endereco publico, de proposito.

NAO mexa em mais nada nesse arquivo: a senha, o MORUMBI_BIND do gateway do
Docker e os limites de memoria dessa maquina estao nele e o repositorio nao
os conhece.

    systemctl daemon-reload && systemctl restart morumbi3d
    systemctl status morumbi3d

Daqui em diante, atualizar e:

    $REPO/implantar/atualizar.sh

Copia de seguranca desta migracao: $BACKUP
FIM
