#!/usr/bin/env node
/**
 * Gera uma matriz de PECAS (topo de bolo, chaveiro) e grava os STL, para o
 * analisador de malha do pacote conferir cada uma.
 *
 * E o §16 do documento de requisitos virado verificacao: "arquivo abre
 * corretamente no Bambu Studio, modelo fatia sem erros". O fatiador recusa
 * malha aberta, e malha aberta e invisivel na tela -- o desenho fica lindo e o
 * arquivo nao imprime.
 *
 *   node ferramentas/conferir_pecas.js /tmp/pecas            # tudo
 *   node ferramentas/conferir_pecas.js /tmp/pecas M3D-CH-001  # um template
 *   node ferramentas/conferir_pecas.js /tmp/pecas --rapido    # os extremos
 */
const fs = require("fs");
const path = require("path");
const { rodar, PRELUDIO, WEB } = require("./pagina_temporaria.js");

// Os templates moram no banco desde o C3. Esta ferramenta roda fora do
// servidor, entao le a SEMENTE -- que e a mesma lista com que o banco nasce.
const TEMPLATES = JSON.parse(
  fs.readFileSync(path.join(WEB, "nucleo", "templates-iniciais.json"), "utf8"));

const SAIDA = process.argv[2] || "/tmp/topos";
// Filtro opcional por SKU, para iterar num template so sem esperar a matriz
// inteira: node ferramentas/conferir_topos.js /tmp/topos M3D-TB-004
const SO = (process.argv[3] && !process.argv[3].startsWith("--")) ? process.argv[3] : "";

// Nomes escolhidos para doer: curto demais, longo demais, com acento, com
// espaco, e o "MM" que no letreiro ja tinha achado caso de letra grudada.
const NOMES = ["MARIA", "ANA", "MM", "José", "Ana Clara", "GUILHERME", "LARA", "SOFIA"];

// A matriz inteira sao 192 combinacoes e uns 6 minutos. `--rapido` corta para
// os extremos -- o nome mais curto e o mais longo, o menor e o maior tamanho --
// que e o que a suite roda a cada rodada. Os extremos sao onde quebra.
const RAPIDO = process.argv.includes("--rapido");

const injecao = `
<script>
(function () {
${PRELUDIO}
  const saida = { erro: null, pecas: [] };
  try {
    const O = MorumbiOficina;
    const tipo = "__TIPO__";
    const PECA = MorumbiPecas.peca(tipo);
    const G = PECA.geometria.Gerador(MorumbiFontes.carregar(opentype));
    const so = ${JSON.stringify(SO)};
    for (const t of ${JSON.stringify(TEMPLATES)}) {
      if ((t.tipo || "topo") !== tipo) continue;
      if (so && t.sku !== so) continue;
      for (const nome of ${JSON.stringify(RAPIDO ? ["MM", "GUILHERME"] : NOMES)}) {
        const todos = PECA.tamanhos;
        const tamanhos = ${RAPIDO} ? [todos[0], todos[todos.length-1]] : todos;
        for (const tamanho of tamanhos) {
          if (t.limite_nome && nome.trim().length > t.limite_nome) continue;  // §10
          const numero = t.campos.includes("numero") ? "5" : "";
          let R;
          try {
            R = G.gerar({ nome, numero, frase: t.frase, tamanho, fonte: t.fonte,
                          base: !!t.base, forma: t.forma, arco: t.arco });
          } catch (e) {
            saida.pecas.push({ sku: t.sku, tipo, nome, tamanho,
                               erro: String(e && e.message || e) });
            continue;
          }
          if (!R.viavel) {
            saida.pecas.push({ sku: t.sku, tipo, nome, tamanho, recusado: R.motivo });
            continue;
          }
          const vist = O.vistoriar(R);
          const stl = MorumbiNucleo.stlBinario(R.camadas);
          saida.pecas.push({
            sku: t.sku, tipo, nome, tamanho, corpos: R.corpos,
            hastes: R.hastes === undefined ? "-" : R.hastes,
            larg: Math.round(R.bb.w), alt: Math.round(R.bb.h),
            aprovada: vist.ok, motivos: vist.motivos,
            avisosMal: (R.avisos||[]).filter(a => a[0] === "mal").map(a => a[1]),
            arquivo: MorumbiPecas.nomeDeArquivo(t.sku, R.nome, R.numero, tamanho, "stl"),
            stl: vist.ok ? b64(stl.buffer) : null,
          });
        }
      }
    }
  } catch (e) { saida.erro = String((e && e.stack) || e); }
  entregar(saida);
})();
</script>`;

const TIPOS = [...new Set(TEMPLATES.map(t => t.tipo || "topo"))];
fs.rmSync(SAIDA, { recursive: true, force: true });
fs.mkdirSync(SAIDA, { recursive: true });

let ok = 0, recusadas = 0, reprovadas = 0, erros = 0;
const resumo = [];
const pecas = [];
// Uma abertura de navegador por PECA: cada uma tem a sua tela, e o Chromium
// custa ~50 s para abrir. Duas aberturas ainda sao mais baratas que uma por
// template.
for (const tipo of TIPOS) {
  const r = rodar(injecao.replace("__TIPO__", tipo),
                  { minutos: 8, pagina: tipo, busca: "?peca=" + tipo });
  pecas.push(...r.pecas);
}
for (const p of pecas) {
  const chave = `${p.sku} ${p.nome.padEnd(10)} ${String(p.tamanho).padStart(3)}mm`;
  if (p.erro) { erros++; resumo.push(`ERRO      ${chave}  ${p.erro}`); continue; }
  if (p.recusado) { recusadas++; resumo.push(`RECUSADA  ${chave}  ${p.recusado}`); continue; }
  if (!p.aprovada) {
    reprovadas++;
    resumo.push(`REPROVADA ${chave}  ${(p.motivos.concat(p.avisosMal)).join(" / ")}`);
    continue;
  }
  ok++;
  fs.writeFileSync(path.join(SAIDA, p.arquivo), Buffer.from(p.stl, "base64"));
  resumo.push(`OK        ${chave}  ${p.larg}x${p.alt}mm  corpos=${p.corpos}  ` +
              `hastes=${p.hastes}  ${p.arquivo}`);
}
console.log(resumo.join("\n"));
console.log(`\n${ok} gerada(s) em ${SAIDA} · ${recusadas} recusada(s) · ` +
            `${reprovadas} reprovada(s) · ${erros} erro(s)`);
if (erros) process.exit(1);
