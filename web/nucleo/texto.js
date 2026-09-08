// Texto vira geometria -- e da plataforma, nao do letreiro.
//
// Estava dentro do Gerador de letreiros, e la funcionava; mas a tabela
// "plataforma x peca" do plano sempre disse que este passo e comum a todo
// gerador, e o topo de bolo provou: ele precisa exatamente disto, letra por
// letra, com a mesma garantia de que as letras se TOCAM.
//
// Essa garantia e o coracao do arquivo. Uma peca de nome, impressa em FDM,
// so existe se as letras formarem um corpo so: letra solta cai do bolo. O
// `encaixeMinimo` acha, por busca binaria, o quanto duas letras precisam se
// invadir para virarem um corpo -- e nunca deixa a invasao comer mais de 28%
// da letra mais fina, que e o ponto em que a letra deixa de ser legivel.
//
// A unica mudanca em relacao ao que estava no letreiro: o tamanho do glifo
// vem por parametro. Era a constante SIZE=60, que e a medida do letreiro; o
// topo de bolo trabalha em outra.
(function (root, fabrica) {
  const M = fabrica(typeof module === 'object' && module.exports
    ? require('./nucleo.js') : root.MorumbiNucleo);
  if (typeof module === 'object' && module.exports) module.exports = M;
  else root.MorumbiTexto = M;
})(typeof window !== 'undefined' ? window : globalThis, function (N) {
  const { S, pathToPolys, uniao, inflar, mover, caixa, analisar } = N;

  /** Uma maquina de texto para um conjunto de fontes, num tamanho de glifo.
   *
   * O cache e por (fonte + letra), e nao por letra: trocar de fonte no meio
   * -- que e o que o letreiro faz a cada modelo -- nao pode devolver o
   * desenho da anterior.
   */
  function Texto(fontes, tamanho) {
    const SIZE = tamanho;
    const cacheG = {}, cacheO = {};
    let F = fontes[Object.keys(fontes)[0]], FN = Object.keys(fontes)[0];

    function usar(nome) {
      if (fontes[nome]) { FN = nome; F = fontes[nome]; }
      return F;
    }

    /** Quais letras precisaram engordar para virar um corpo so.
     *
     * A tela mostra isso ("Acentos tratados: Á (+1.2)") porque e uma peca de
     * informacao honesta: aquela letra saiu um pouco mais gorda que as outras,
     * e quem olha o desenho de perto vai reparar.
     */
    function dilatacoes(texto) {
      const fora = {};
      for (const ch of new Set(texto.replace(/ /g, ''))) {
        const d = letra(ch).dil;
        if (d) fora[ch] = d;
      }
      return fora;
    }

    function letra(ch) {
      const k = FN + ch;
      if (cacheG[k]) return cacheG[k];
      let paths = uniao([pathToPolys(F.charToGlyph(ch).getPath(0,0,SIZE))]);
      let dil = 0;
      if (analisar(paths).corpos > 1) {
        for (const d of [0.4,0.8,1.2,1.6,2.0,2.6,3.2,4.0]) {
          const t = uniao([inflar(paths, d)]);
          if (analisar(t).corpos === 1) { paths = t; dil = d; break; }
        }
      }
      return (cacheG[k] = { paths, dil, bb: caixa(paths) });
    }

    function encaixeMinimo(a, b) {
      const k = FN + a + b;
      if (k in cacheO) return cacheO[k];
      const A = letra(a), B = letra(b);
      const ok = ov => analisar(uniao([A.paths, mover(B.paths, (A.bb.maxX-ov)-B.bb.minX, 0)])).corpos === 1;
      let lo=0, hi=2, achou=false;
      while (hi <= 48) { if (ok(hi)) { achou=true; break; } lo=hi; hi*=2; }
      if (!achou) return (cacheO[k] = null);
      for (let i=0;i<14;i++){ const m=(lo+hi)/2; ok(m) ? hi=m : lo=m; }
      return (cacheO[k] = hi);
    }

    function linhaEncaixada(txt, margem) {
      const lista = []; let cursor = 0, prev = null;
      for (const ch of txt.replace(/ /g, '')) {
        const G = letra(ch);
        let tx;
        if (prev === null) tx = cursor - G.bb.minX;
        else {
          const P = letra(prev);
          const min = encaixeMinimo(prev, ch) || 0;
          const fina = Math.min(P.bb.maxX - P.bb.minX, G.bb.maxX - G.bb.minX);
          // a margem de seguranca nunca pode comer mais de 28% da letra mais fina
          const limite = 0.28 * fina;
          let ov = min + margem;
          if (ov > limite) ov = Math.max(limite, min + margem * 0.2);
          tx = (cursor - ov) - G.bb.minX;
        }
        lista.push(mover(G.paths, tx, 0));
        cursor = tx + G.bb.maxX; prev = ch;
      }
      const P = uniao(lista);
      return { paths: P, bb: caixa(P) };
    }

    function linhaNatural(txt) {
      const k = SIZE / F.unitsPerEm;
      const lista = []; let x = 0, ant = null;
      for (const ch of txt.replace(/ /g, '')) {
        const g = F.charToGlyph(ch);
        if (ant) x += (F.getKerningValue(ant, g) || 0) * k;
        lista.push(mover(letra(ch).paths, x, 0));
        x += g.advanceWidth * k; ant = g;
      }
      const P = uniao(lista);
      return { paths: P, bb: caixa(P) };
    }

    /** Empilha duas linhas centralizadas.
     *
     * Com `exigirContato`, procura o maior afastamento que ainda deixa a peca
     * em um corpo so -- ou seja, converge no ponto exato em que as linhas
     * COMECAM a se tocar. Isso e um corpo so para o Clipper e uma aresta
     * nao-manifold depois de extrudar: o fatiador recusa.
     *
     * `sobrepor` (em mm de glifo) recua desse ponto para dentro, dando largura
     * de contato de verdade. Sem ele o comportamento e o de antes -- e e por
     * isso que o letreiro, que nao passa o parametro, sai byte a byte igual.
     */
    function empilhar(linhas, folga, exigirContato, sobrepor) {
      if (linhas.length === 1) return { paths: linhas[0].paths, folga: 0 };
      const larg = Math.max(...linhas.map(l => l.bb.w));
      const c0 = mover(linhas[0].paths, (larg - linhas[0].bb.w)/2 - linhas[0].bb.minX, 0);
      const c1 = mover(linhas[1].paths, (larg - linhas[1].bb.w)/2 - linhas[1].bb.minX, 0);
      const b0 = linhas[0].bb, b1 = linhas[1].bb;
      const monta = f => uniao([ mover(c0, 0, (b1.maxY - b1.minY) + f - b0.minY), mover(c1, 0, -b1.minY) ]);
      if (!exigirContato) return { paths: monta(folga), folga };
      const recuo = sobrepor || 0;
      if (!recuo && analisar(monta(folga)).corpos === 1) return { paths: monta(folga), folga };
      let lo = -0.28 * (b0.maxY - b0.minY), hi = folga;
      if (analisar(monta(lo)).corpos !== 1) return { paths: monta(lo), folga: lo, falhou: true };
      for (let i=0;i<16;i++){ const m=(lo+hi)/2; analisar(monta(m)).corpos === 1 ? lo=m : hi=m; }
      if (!recuo) return { paths: monta(lo), folga: lo };
      // Entra `recuo` mm alem do ponto de toque, sem passar do limite de 28%
      // que mantem a letra legivel.
      const alvo = Math.max(lo - recuo, -0.28 * (b0.maxY - b0.minY));
      return { paths: monta(alvo), folga: alvo,
               falhou: analisar(monta(alvo)).corpos !== 1 };
    }
    return { usar, fonte: () => F, letra, encaixeMinimo, linhaEncaixada,
             linhaNatural, empilhar, dilatacoes };
  }

  return { Texto };
});
