#!/usr/bin/env node
/**
 * Impressao digital do gerador de letreiros: um sha256 por peca.
 *
 * Serve para provar que uma mudanca no codigo NAO mudou o que sai. Gera uma
 * matriz de pecas num Chromium sem tela e imprime `caso  sha256  triangulos`.
 * Rodar antes e depois de mexer, e comparar, e a unica forma honesta de
 * refatorar geometria: teste que so olha "malha fechada" passa feliz com a
 * peca virada do avesso.
 *
 * Uma execucao do navegador para a matriz inteira -- uma por caso custava
 * ~6 s cada.
 *
 *   node ferramentas/impressao_digital.js > docs/impressao-digital.txt
 *   node ferramentas/impressao_digital.js --conferir docs/impressao-digital.txt
 */

const crypto = require("crypto");
const fs = require("fs");
const { rodar, PRELUDIO } = require("./pagina_temporaria.js");

// nome | produto | largura | espessura | duas linhas | altura | base
// A matriz cobre os seis modelos, as duas disposicoes, a luminaria (60 mm),
// a base solta do Classico e um caso que o gerador precisa RECUSAR.
const CASOS = [
  ["MORUMBI",    "classico", 220, 12, false, "auto", 0],
  ["MORUMBI",    "classico", 220, 12, false, "auto", 8],
  ["MORUMBI",    "classico", 220,  6, false, "auto", 0],
  ["MORUMBI",    "classico", 220, 60, false, "auto", 0],
  ["MORUMBI",    "classico", 170, 12, false,     40, 0],
  ["Ana Clara",  "classico", 220, 12, true,  "auto", 0],
  ["Ana Clara",  "classico", 220, 12, false, "auto", 0],
  ["Ana Clara",  "magia",    220, 12, true,  "auto", 0],
  ["LOVE",       "magia",    220, 12, false, "auto", 0],
  ["LOVE",       "magia",     80, 12, false, "auto", 0],
  ["JOAO",       "gamer",    220, 12, false, "auto", 0],
  ["JOAO",       "gamer",    220, 60, false, "auto", 0],
  ["SOFIA",      "cinema",   220, 12, false, "auto", 0],
  ["SOFIA",      "cinema",   170, 60, false, "auto", 0],
  ["NOAH",       "futuro",   220, 12, false, "auto", 0],
  ["NOAH",       "futuro",   220, 60, false, "auto", 0],
  ["LUA",        "terror",   220, 12, false, "auto", 0],
  ["LUA",        "terror",   220, 60, false, "auto", 0],
  ["MM",         "classico", 220, 12, false, "auto", 0],
  ["Maria Eduarda Silva", "classico", 250, 12, true, "auto", 0],
];

const injecao = `
<script>
(function () {
${PRELUDIO}
  const casos = ${JSON.stringify(CASOS)};
  const saida = { erro: null, linhas: [] };
  try {
    const G = gerador();
    for (const [nome, produto, largura, esp, duas, alt, base] of casos) {
      const item = { caso: [nome, produto, largura, esp, duas, alt, base], pecas: [] };
      try {
        const R = G.gerar(nome, largura, esp, produto, duas, alt, base);
        item.viavel = R.viavel !== false;
        item.motivo = R.motivo || null;
        item.larguraReal = R.larguraReal == null ? null : Math.round(R.larguraReal * 1000) / 1000;
        item.altUsada = R.altUsada == null ? null : R.altUsada;
        const lista = (R.pecas && R.pecas.length) ? R.pecas : (R.simples ? [R.simples] : []);
        for (const p of lista) {
          const stl = MorumbiNucleo.stlBinario(p.camadas);
          item.pecas.push({ rot: p.rot || produto, corpos: p.corpos,
                            esperado: p.esperado || null, triangulos: stl.n,
                            stl: b64(stl.buffer) });
        }
      } catch (e) {
        item.erro = String((e && e.message) || e);
      }
      saida.linhas.push(item);
    }
  } catch (e) {
    saida.erro = String((e && e.stack) || e);
  }
  entregar(saida);
})();
</script>
`;

function linhas(r) {
  const saida = [];
  for (const item of r.linhas) {
    const [nome, produto, largura, esp, duas, alt, base] = item.caso;
    const chave = `${nome}|${produto}|${largura}|${esp}|${duas ? "2lin" : "1lin"}|${alt}|${base}`;
    if (item.erro) { saida.push(`${chave}  ERRO  ${item.erro}`); continue; }
    if (!item.viavel) { saida.push(`${chave}  RECUSADO  ${item.motivo}`); continue; }
    saida.push(`${chave}  largura=${item.larguraReal}  altura=${item.altUsada}`);
    for (const p of item.pecas) {
      const soma = crypto.createHash("sha256").update(Buffer.from(p.stl, "base64")).digest("hex");
      saida.push(`    ${p.rot}  ${soma}  tri=${p.triangulos}  corpos=${p.corpos}` +
                 (p.esperado ? `/${p.esperado}` : ""));
    }
  }
  return saida;
}

const conferir = process.argv.indexOf("--conferir");
const atual = linhas(rodar(injecao));

if (conferir < 0) {
  console.log("# Impressao digital do gerador de letreiros.");
  console.log("# Gerado por ferramentas/impressao_digital.js -- nao editar a mao.");
  console.log("# Um sha256 por peca. Mudou um hash sem que a peca devesse mudar?");
  console.log("# Entao a mudanca alterou a geometria, e nao so o arranjo do codigo.");
  console.log(atual.join("\n"));
} else {
  const esperado = fs.readFileSync(process.argv[conferir + 1], "utf8")
    .split("\n").filter(l => l && !l.startsWith("#"));
  const diferencas = [];
  for (let i = 0; i < Math.max(atual.length, esperado.length); i++) {
    if (atual[i] !== esperado[i]) diferencas.push(`  - esperado: ${esperado[i] ?? "(nada)"}\n  - saiu:     ${atual[i] ?? "(nada)"}`);
  }
  if (diferencas.length) {
    console.error(`${diferencas.length} diferenca(s) na impressao digital:\n` + diferencas.join("\n"));
    process.exit(1);
  }
  console.log(`Impressao digital identica: ${atual.length} linhas conferidas.`);
}
