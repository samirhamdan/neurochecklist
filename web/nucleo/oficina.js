// Oficina -- os numeros DESTA casa, que todo gerador tem que obedecer.
//
// O nucleo e geometria: vale para qualquer um. Este arquivo e a Morumbi 3D:
// a mesa de 256 mm, a purga de 6 g por troca de cor, o piso de R$ 18, os
// R$ 0,60 por grama. Um gerador novo herda tudo isto sem reescrever nada --
// e, o que importa mais, sem CHUTAR diferente do que o letreiro chuta hoje.
//
// A densidade e a unica coisa aqui que veio de peca impressa e nao de tabela:
// esta calibrada no MUNIR de verdade, 66,19 g em 1h46 com 15 mm e 8% de
// preenchimento. Mexer nela sem imprimir de novo e trocar medida por palpite.
(function (root, fabrica) {
  const M = fabrica(root, typeof module === 'object' && module.exports
    ? require('./nucleo.js') : root.MorumbiNucleo);
  if (typeof module === 'object' && module.exports) module.exports = M;
  else root.MorumbiOficina = M;
})(typeof window !== 'undefined' ? window : globalThis, function (root, N) {
  const MESA = N.MESA;

  // O ClipperLib vem inline na pagina; em node so existe se alguem instalar.
  // Buscado na hora de usar, e nao na carga, para o resto do arquivo abrir em
  // node -- e o resto e onde moram os numeros que precisam de teste.
  function clipper() {
    const L = root.ClipperLib || (typeof require === 'function' ? require('clipper-lib') : null);
    if (!L) throw new Error("ClipperLib nao esta carregado");
    return L;
  }

  // Por espessura: quanto de preenchimento e como a peca fica em pe na mesa.
  const ESPESSURAS = {
     6: { infill: 25, rot: "parede" },
    12: { infill:  8, rot: "mesa" },
    60: { infill:  6, rot: "luminaria" },
  };

  // Cada troca de cor descarta filamento antes de voltar a imprimir a peca.
  // Sai do custo de toda peca de duas cores, e e o motivo de "1 cor" ser um
  // filtro de verdade na tela Criar.
  const PURGA_POR_TROCA = 6;    // g

  // O piso e o por-grama sao a regra COMERCIAL do Samir, nao um custo
  // calculado. O custo analitico mora no servidor (sistema/custo.py); estes
  // dois numeros sao o preco de balcao, e ha teste provando que a formula
  // daqui e a de la dao o mesmo numero.
  const PISO = 18, POR_GRAMA = 0.60;

  function volume(camadas) {
    let v = 0;
    for (const c of camadas) {
      let a = 0;
      for (const p of c.paths) a += clipper().Clipper.Area(p);
      v += (a / 1e8) * (c.z1 - c.z0);
    }
    return v / 1000;
  }

  function estimar(vol, esp, oca) {
    // Peca ja escavada (luminaria): o volume que sobrou E a parede, e parede
    // de 2,4 mm imprime cheia. Aplicar o preenchimento de 6% aqui erraria o
    // filamento por quase dez vezes -- para baixo, que e o lado que da
    // prejuizo na venda.
    if (oca) { const g = vol * 1.22; return { g, min: g * 1.6 }; }
    const inf = (ESPESSURAS[esp] || { infill: 8 }).infill / 100;
    const casca = Math.min(2.4 / esp, 1);          // ~1,2mm solido em cima e embaixo
    const d = Math.min(1.24 * (casca + inf * (1 - casca)) + 0.02, 1.24);
    const g = vol * d;
    return { g, min: g * 1.6 };
  }

  // Cabe na mesa? A diagonal e o truque que salva peca larga: virada a 45 graus
  // ela ganha 1,41x de comprimento util.
  function cabe(w, h) {
    if (w <= MESA && h <= MESA) return { ok: true, ang: 0, uso: Math.max(w, h) };
    const d = (w + h) / Math.SQRT2;
    return { ok: d <= MESA, ang: 45, uso: d };
  }

  function purga(cores) { return PURGA_POR_TROCA * Math.max(cores - 1, 0); }

  function precoComercial(gramas, piso, porGrama) {
    const p = piso == null ? PISO : piso;
    const g = porGrama == null ? POR_GRAMA : porGrama;
    if (!(gramas > 0)) return 0;
    return Math.ceil((p + gramas * g) / 5) * 5;
  }

  function nomeDeArquivo({ nome, rotulo, cor, bb, espessura, altura }) {
    const slug = String(nome).trim().replace(/ /g, "-");
    const inf = (ESPESSURAS[espessura] || { infill: 8 }).infill;
    const t = Math.round(altura);
    return `${slug}_${rotulo}_${cor}_${Math.round(bb.w)}x${Math.round(bb.h)}x${t}mm_inf${inf}.stl`;
  }

  // A vistoria: a unica porta entre a peca e o download.
  //
  // Antes do C1 a tela AVISAVA que a peca tinha saido em partes soltas e
  // deixava baixar assim mesmo -- o aviso rolava para fora do campo de visao
  // e o arquivo ia para a impressora. Agora reprovada e reprovada: quem
  // chama recebe `ok:false` e os motivos, em portugues, para mostrar.
  function vistoriar(peca) {
    const motivos = [];
    const enc = cabe(peca.bb.w, peca.bb.h);
    if (!enc.ok) {
      motivos.push(`Não cabe na mesa: precisa de ${Math.round(enc.uso)} mm de ${MESA} mm.`);
    }
    if (peca.esperado && peca.corpos !== peca.esperado) {
      motivos.push(`A peça saiu em ${peca.corpos} partes soltas em vez de ` +
                   `${peca.esperado}. Não imprima assim.`);
    }
    return { ok: motivos.length === 0, motivos, enc };
  }

  return { ESPESSURAS, PURGA_POR_TROCA, PISO, POR_GRAMA, MESA,
           volume, estimar, cabe, purga, precoComercial, nomeDeArquivo, vistoriar };
});
