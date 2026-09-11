/**
 * Roda a pagina do gerador num Chromium sem tela e traz o resultado de volta.
 *
 * As duas ferramentas que conferem letreiro precisam da mesma coisa: uma copia
 * da pagina com um script injetado, um Chromium sem tela, e o unico jeito de
 * tirar binario de um --dump-dom, que e base64 dentro de uma div.
 *
 * Desde o C1 a pagina carrega o nucleo por <script src> relativo, entao a
 * copia temporaria precisa levar a pasta nucleo/ junto -- e foi exatamente
 * isso que quebrou as duas ferramentas de uma vez quando o nucleo saiu do
 * HTML. Uma vez aqui, conserta-se num lugar.
 */
const { execFileSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const CHROME =
  process.env.CHROME_BIN || "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const WEB = path.join(__dirname, "..", "web");
const PAGINAS = {
  letreiro: path.join(WEB, "gerador-letreiros.html"),
  // Uma pagina para todas as pecas desde o C4; a peca vai no ?peca=.
  topo: path.join(WEB, "gerador.html"),
  display: path.join(WEB, "gerador.html"),
  chaveiro: path.join(WEB, "gerador.html"),
};
const PAGINA = PAGINAS.letreiro;      // o padrao, para quem ja usava
const MARCA = "RESULTADO_TESTE";

/** Copia a pagina e o nucleo para uma pasta temporaria, com o script injetado. */
function montar(injecao, qual) {
  const pagina = PAGINAS[qual || "letreiro"];
  if (!pagina) throw new Error(`pagina desconhecida: ${qual}`);
  const html = fs.readFileSync(pagina, "utf8").replace("</body>", injecao + "</body>");
  const pasta = fs.mkdtempSync(path.join(os.tmpdir(), "letreiro-"));
  for (const dir of ["nucleo", "fontes", "libs"]) {
    fs.cpSync(path.join(WEB, dir), path.join(pasta, dir), { recursive: true });
  }
  const arquivo = path.join(pasta, "pagina.html");
  fs.writeFileSync(arquivo, html);
  return { pasta, arquivo };
}

/** Abre a pagina, espera o script injetado terminar e devolve o JSON dele. */
function rodar(injecao, { minutos = 3, pagina = "letreiro", busca = "" } = {}) {
  const { pasta, arquivo } = montar(injecao, pagina);
  let dom;
  try {
    dom = execFileSync(
      CHROME,
      ["--headless", "--disable-gpu", "--no-sandbox",
       `--virtual-time-budget=${minutos * 60000}`, "--dump-dom", "file://" + arquivo + busca],
      { maxBuffer: 1024 * 1024 * 1024, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }
    );
  } finally {
    fs.rmSync(pasta, { recursive: true, force: true });
  }

  const abre = `id="${MARCA}">`;
  const i = dom.indexOf(abre);
  if (i < 0) throw new Error("a pagina nao chegou a produzir resultado");
  const bruto = dom.slice(i + abre.length, dom.indexOf("</div>", i));
  const r = JSON.parse(bruto.replace(/&quot;/g, '"').replace(/&amp;/g, "&")
                            .replace(/&lt;/g, "<").replace(/&gt;/g, ">"));
  if (r.erro) throw new Error("erro dentro da pagina:\n" + r.erro);
  return r;
}

/** As cinco fontes vem embutidas na pagina em base64; todo injetado precisa disto. */
const PRELUDIO = `
  function b64(buffer) {
    const u8 = new Uint8Array(buffer);
    let s = "";
    for (let i = 0; i < u8.length; i += 8192) s += String.fromCharCode.apply(null, u8.subarray(i, i + 8192));
    return btoa(s);
  }
  function fontes() { return MorumbiFontes.carregar(opentype); }
  function gerador() { return MorumbiLetreiro.Gerador(fontes()); }
  function entregar(saida) {
    const alvo = document.createElement("div");
    alvo.id = ${JSON.stringify(MARCA)};
    alvo.textContent = JSON.stringify(saida);
    document.body.appendChild(alvo);
  }
`;

module.exports = { rodar, montar, PRELUDIO, CHROME, PAGINA, PAGINAS, WEB };
