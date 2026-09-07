#!/usr/bin/env node
/**
 * Banco de testes do gerador de letreiros.
 *
 * Roda o arquivo HTML DE VERDADE num Chromium sem tela — com as fontes
 * embutidas, o opentype, o ClipperLib e o earcut que ele ja carrega — pede
 * uma peca e grava os STL em disco. Assim da para conferir a saida com o
 * analisador de malha do pacote, em vez de confiar no olho.
 *
 * Uso:
 *   node ferramentas/gerar_letreiro.js --nome "MORUMBI" --produto classico \
 *        --largura 220 --espessura 12 --saida /tmp/stl
 */

const fs = require("fs");
const os = require("os");
const path = require("path");
const { rodar, PRELUDIO } = require("./pagina_temporaria.js");

function argumentos() {
  const a = { nome: "MORUMBI", produto: "classico", largura: 220,
              espessura: 12, altura: "auto", base: 0, duas: true,
              saida: path.join(os.tmpdir(), "letreiro") };
  const v = process.argv.slice(2);
  for (let i = 0; i < v.length; i += 2) {
    const chave = v[i].replace(/^--/, "");
    let valor = v[i + 1];
    if (["largura", "espessura", "base"].includes(chave)) valor = Number(valor);
    if (chave === "altura" && valor !== "auto") valor = Number(valor);
    if (chave === "duas") valor = valor !== "false";
    a[chave] = valor;
  }
  return a;
}

const a = argumentos();

// Injetado no fim da pagina: monta o proprio Gerador (o da interface fica
// preso no escopo dela), gera a peca e deixa o resultado no DOM em base64,
// que e o unico jeito de tirar binario de um --dump-dom.
const injecao = `
<script>
(function () {
${PRELUDIO}
  const saida = { erro: null, pecas: [] };
  try {
    const G = gerador();
    const R = G.gerar(${JSON.stringify(a.nome)}, ${a.largura}, ${a.espessura},
      ${JSON.stringify(a.produto)}, ${a.duas},
      ${typeof a.altura === "string" ? JSON.stringify(a.altura) : a.altura},
      ${a.base});
    saida.viavel = R.viavel;
    saida.motivo = R.motivo || null;
    saida.linhas = R.linhas;
    saida.larguraReal = R.larguraReal;
    saida.altUsada = R.altUsada;
    saida.delta = R.delta || null;
    const lista = (R.pecas && R.pecas.length) ? R.pecas : [R.simples];
    for (const p of lista) {
      const stl = MorumbiNucleo.stlBinario(p.camadas);
      saida.pecas.push({
        rot: p.rot || ${JSON.stringify(a.produto)},
        corpos: p.corpos, esperado: p.esperado,
        bb: p.bb, triangulos: stl.n, stl: b64(stl.buffer)
      });
    }
  } catch (e) {
    saida.erro = String((e && e.stack) || e);
  }
  entregar(saida);
})();
</script>
`;

const r = rodar(injecao, { minutos: 1 });

fs.mkdirSync(a.saida, { recursive: true });
console.log(`nome: ${a.nome} | produto: ${a.produto} | linhas: ${JSON.stringify(r.linhas)}`);
console.log(`largura real: ${r.larguraReal?.toFixed(1)} mm | altura usada: ${r.altUsada} mm` +
            (r.delta ? ` | moldura: ${r.delta} mm` : "") +
            (r.viavel === false ? ` | INVIAVEL: ${r.motivo}` : ""));
for (const p of r.pecas) {
  const destino = path.join(a.saida, `${a.nome.replace(/ /g, "-")}-${p.rot}.stl`);
  fs.writeFileSync(destino, Buffer.from(p.stl, "base64"));
  console.log(`  ${p.rot}: ${p.triangulos} triangulos, corpos=${p.corpos}` +
              (p.esperado ? `/esperado ${p.esperado}` : "") +
              ` -> ${destino}`);
}
