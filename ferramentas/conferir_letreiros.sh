#!/usr/bin/env bash
# Regressao do gerador de letreiros: gera uma matriz de pecas no navegador e
# confere cada STL com o analisador de malha do pacote. Nenhuma peca pode sair
# com malha aberta — e o que o fatiador recusa.
set -u
cd "$(dirname "$0")/.."
SAIDA="${1:-/tmp/letreiros-regressao}"
rm -rf "$SAIDA"; mkdir -p "$SAIDA"

CASOS=(
  "LOVE|classico|12"      "LOVE|classico|60"
  "MORUMBI|classico|6"    "MORUMBI|classico|12"   "MORUMBI|classico|60"
  "Ana Clara|classico|12" "Ana Clara|classico|60"
  "Ana Clara|magia|12"    "JOAO|gamer|12"         "JOAO|gamer|60"
  "LUA|terror|60"         "MM|classico|60"
  "SOFIA|cinema|12"       "NOAH|futuro|60"
)

for caso in "${CASOS[@]}"; do
  IFS='|' read -r nome produto esp <<< "$caso"
  pasta="$SAIDA/$(echo "$nome$produto$esp" | tr -d ' ')"
  if ! node ferramentas/gerar_letreiro.js --nome "$nome" --produto "$produto" \
       --espessura "$esp" --largura 220 --saida "$pasta" > "$pasta.log" 2>&1; then
    echo "ERRO ao gerar: $nome / $produto / ${esp}mm"; cat "$pasta.log"
  fi
done

python3 - "$SAIDA" <<'PY'
import sys, pathlib
sys.path.insert(0, '.')
from morumbi3d.config import carregar_config
from morumbi3d.mesh import analisar_arquivo

cfg = carregar_config()
falhas = []
for arquivo in sorted(pathlib.Path(sys.argv[1]).rglob('*.stl')):
    r = analisar_arquivo(arquivo, cfg)
    marca = 'OK  ' if r.fechada else 'ABERTA'
    if not r.fechada:
        falhas.append(arquivo.name)
    print(f"{marca} {arquivo.parent.name:22} {arquivo.name:36} "
          f"abertas={r.arestas_abertas:3} partes={r.partes_soltas:2} tri={r.triangulos}")
print()
if falhas:
    print(f"{len(falhas)} peca(s) com malha aberta: {', '.join(falhas)}")
    sys.exit(1)
print("Todas as pecas sairam com malha fechada.")
PY
