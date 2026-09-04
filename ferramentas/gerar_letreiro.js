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

const { execFileSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const CHROME =
  process.env.CHROME_BIN || "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const PAGINA = path.join(__dirname, "..", "web", "gerador-letreiros.html");

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
  function carregar(id) {
    const bin = atob(document.getElementById(id).textContent.trim());
    const buf = new ArrayBuffer(bin.length), u8 = new Uint8Array(buf);
    for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
    return buf;
  }
  function b64(buffer) {
    const u8 = new Uint8Array(buffer);
    let s = "";
    for (let i = 0; i < u8.length; i += 8192) {
      s += String.fromCharCode.apply(null, u8.subarray(i, i + 8192));
    }
    return btoa(s);
  }
  const saida = { erro: null, pecas: [] };
  try {
    const G = MorumbiNucleo.Gerador({
      luckiest: opentype.parse(carregar("fonte1")),
      gamer:    opentype.parse(carregar("fonte2")),
      cinema:   opentype.parse(carregar("fonte3")),
      futuro:   opentype.parse(carregar("fonte4")),
      terror:   opentype.parse(carregar("fonte5"))
    });
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
  const alvo = document.createElement("div");
  alvo.id = "RESULTADO_TESTE";
  alvo.textContent = JSON.stringify(saida);
  document.body.appendChild(alvo);
})();
</script>
`;

const html = fs.readFileSync(PAGINA, "utf8").replace("</body>", injecao + "</body>");
const temporario = fs.mkdtempSync(path.join(os.tmpdir(), "letreiro-"));
const arquivo = path.join(temporario, "pagina.html");
fs.writeFileSync(arquivo, html);

const dom = execFileSync(
  CHROME,
  ["--headless", "--disable-gpu", "--no-sandbox", "--virtual-time-budget=60000",
   "--dump-dom", "file://" + arquivo],
  { maxBuffer: 1024 * 1024 * 512, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }
);

const marca = dom.indexOf('id="RESULTADO_TESTE">');
if (marca < 0) {
  console.error("A pagina nao chegou a produzir resultado.");
  process.exit(1);
}
const inicio = marca + 'id="RESULTADO_TESTE">'.length;
const bruto = dom.slice(inicio, dom.indexOf("</div>", inicio));
const r = JSON.parse(
  bruto.replace(/&quot;/g, '"').replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
);

if (r.erro) {
  console.error("Erro dentro da pagina:\n" + r.erro);
  process.exit(1);
}

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
