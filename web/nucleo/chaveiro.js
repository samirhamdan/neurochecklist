// Chaveiro de nome -- a segunda peca de verdade da plataforma.
//
// Escolhido porque e o unico dos dez do plano com demanda dentro do proprio
// projeto: esta nos pedidos de exemplo ("Chaveiro personalizado x6"), e o
// exemplo de custo nos testes (9 g, 0,4 h), e e o caso que o modulo de
// licencas ja tratava ("Chaveiro do Corinthians"). Os outros nove esperam
// cliente pedindo.
//
// A engenharia dele e diferente da do topo de bolo, e e por isso que ele
// prova a plataforma: o topo se quebra na CONEXAO (letra solta cai do bolo);
// o chaveiro se quebra no FURO. Uma argola puxa a peca todo dia, e um furo
// perto da borda rasga na terceira semana. Entao aqui a garantia e outra:
//
//   * o furo nasce numa aba REDONDA, e nao no meio de uma letra: assim a
//     parede em volta dele e a mesma dos dois lados, independente do desenho;
//   * a aba invade o nome ate ter area de contato de verdade -- mesma regra
//     que o topo aprendeu a duras penas;
//   * a peca e pequena (3 a 7 cm), entao o traco minimo da oficina passa a
//     ser o limite que mais aparece, e nao um extremo raro.
(function (root, fabrica) {
  const N = (typeof module === 'object' && module.exports)
    ? Object.assign({}, require('./nucleo.js'), require('./texto.js'),
                    { O: require('./oficina.js') })
    : Object.assign({}, root.MorumbiNucleo, root.MorumbiTexto,
                    { O: root.MorumbiOficina });
  const M = fabrica(root, N);
  if (typeof module === 'object' && module.exports) module.exports = M;
  else root.MorumbiChaveiro = M;
})(typeof window !== 'undefined' ? window : globalThis, function (root, N) {
  const { S, MESA, uniao, diferenca, interseccao, area, inflar, mover, escalar,
          caixa, analisar, retangulo, Texto, O } = N;

  const SIZE = 60;

  const MEDIDAS = {
    espessura: 3,        // mm: 12 camadas de 0,24 -- aguenta bolso e chave
    furo: 4,             // mm de diametro: passa argola de 25 mm folgada
    parede: 2.2,         // mm de material em volta do furo, em toda a volta
    invasao: 0.35,       // quanto da aba entra no nome, em fracao da aba
    contatoMinimo: 0.05, // fracao da area da aba que precisa encostar no nome
    margemMesa: 12,
  };

  // Chaveiro e peca de bolso: 3 a 7 cm. Acima disso vira pingente de mochila,
  // e ai o nome ja e outro produto.
  const TAMANHOS = [30, 40, 50, 60, 70];

  /** Um circulo de `n` lados, anti-horario, centrado em (0,0). */
  function circulo(raio, n) {
    n = n || 48;
    const pts = [];
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2;
      pts.push({ X: Math.round(Math.cos(a) * raio * S), Y: Math.round(Math.sin(a) * raio * S) });
    }
    return [pts];
  }

  function Gerador(fontes) {
    const T = Texto(fontes, SIZE);

    /** A aba do furo: um disco que encosta no nome e leva o furo no centro.
     *
     * Por que aba, e nao furo direto na letra: a parede em volta do furo
     * precisa ser a mesma nos quatro lados, e no meio de um "A" ou de um "I"
     * ela nao e. Com a aba, a garantia e geometrica e nao depende do nome.
     */
    function aba(paths, bb, med, ladoDireito) {
      const raio = med.furo / 2 + med.parede;
      const disco = circulo(raio);
      const meioY = (bb.minY + bb.maxY) / 2;
      const areaDisco = Math.abs(area(disco));
      // Vai entrando ate a area de contato ser de verdade -- o mesmo criterio
      // que a decoracao do topo de bolo aprendeu.
      for (let invade = med.invasao; invade <= 1.2; invade += 0.05) {
        const cx = ladoDireito ? bb.maxX + raio - raio * 2 * invade
                               : bb.minX - raio + raio * 2 * invade;
        const posto = mover(disco, cx, meioY);
        if (area(interseccao(posto, paths)) >= areaDisco * med.contatoMinimo) {
          return { paths: posto, cx, cy: meioY, raio };
        }
      }
      return null;
    }

    function gerar(pedido) {
      const med = Object.assign({}, MEDIDAS, pedido.medidas || {});
      const esp = pedido.espessura || med.espessura;
      const larguraAlvo = pedido.tamanho || TAMANHOS[2];
      T.usar(pedido.fonte || Object.keys(fontes)[0]);

      const nome = String(pedido.nome || '').toUpperCase().trim().replace(/\s+/g, ' ');
      if (!nome) return { viavel: false, motivo: 'Escreva o nome que vai no chaveiro.' };

      const avisos = [];
      let paths = T.linhaEncaixada(nome, 1.8).paths;
      let bb = caixa(paths);

      // Escala primeiro: a aba e o furo sao medidas de MILIMETRO -- uma argola
      // de 4 mm e de 4 mm no chaveiro de 3 cm e no de 7 cm. Escalar junto
      // faria o furo do chaveiro pequeno virar um alfinete.
      const util = MESA - med.margemMesa;
      const escalaPedida = larguraAlvo / bb.w;
      const escala = Math.min(escalaPedida, util / bb.w, util / bb.h);
      paths = escalar(paths, escala);
      bb = caixa(paths);
      paths = mover(paths, -bb.minX, -bb.minY);
      bb = caixa(paths);

      const ladoDireito = pedido.lado === 'direita';
      const posto = aba(paths, bb, med, ladoDireito);
      if (!posto) {
        return { viavel: false, avisos,
                 motivo: 'A argola não encontra material sólido para se agarrar. ' +
                         'Use um nome mais longo ou um tamanho maior.' };
      }
      paths = uniao([paths, posto.paths]);
      bb = caixa(paths);

      // O furo, por ultimo. A parede em volta dele nao precisa ser MEDIDA: ela
      // e garantida pela construcao, porque a aba e um disco de raio
      // (furo/2 + parede) que so ACRESCENTA material -- nada no desenho pode
      // comer para dentro dele.
      //
      // A primeira versao media assim mesmo, comparando corpos antes e depois
      // de encolher, e por isso acusava "a parede ficou fina" em pecas cuja
      // causa real era outra: nome comprido em chaveiro pequeno, letra fina.
      // A mensagem mandava aumentar o tamanho por um motivo que nao era o
      // verdadeiro.
      const furo = mover(circulo(med.furo / 2), posto.cx, posto.cy);
      paths = diferenca(paths, furo);
      bb = caixa(paths);

      // O que precisa ser conferido, na ordem em que as coisas realmente
      // quebram numa peca pequena:
      const fino = O.tracosFinos(paths, O.TRACO_MINIMO);
      if (fino.tudo) {
        return { viavel: false, avisos,
                 motivo: `A peça inteira ficou com traço abaixo de ${O.TRACO_MINIMO} mm. ` +
                         `Chaveiro pequeno com nome comprido não imprime: use um tamanho ` +
                         `maior ou um nome mais curto.` };
      }
      if (fino.fracao > 0.10) {
        return { viavel: false, avisos,
                 motivo: `Boa parte da peça ficou com traço abaixo de ${O.TRACO_MINIMO} mm ` +
                         `e sairia falhada. ${nome.length} letras em ${Math.round(bb.w)} mm ` +
                         `é apertado: use um tamanho maior ou um nome mais curto.` };
      }
      if (fino.fracao > 0.04) {
        avisos.push(['mal', `Partes da peça ficaram com traço abaixo de ${O.TRACO_MINIMO} mm ` +
                            `e podem sair falhadas. Aumente o tamanho.`]);
      }

      const conexao = O.conexaoFragil(paths);
      if (conexao.fragil) {
        return { viavel: false, avisos,
                 motivo: 'Duas partes da peça só se encostam, sem largura de contato: a ' +
                         'malha sai inválida e o fatiador recusa. Use um tamanho maior.' };
      }

      // O furo tem que ter SOBRADO. Se o recorte comeu a peca inteira ali, a
      // argola nao tem onde entrar -- e o chaveiro sem furo e um pingente.
      if (analisar(paths).vazados < 1) {
        return { viavel: false, avisos,
                 motivo: 'O furo da argola não sobrou na peça. Use um tamanho maior.' };
      }

      const corpos = analisar(paths).corpos;
      if (corpos !== 1) {
        avisos.push(['mal', `A peça saiu em ${corpos} partes soltas. Não imprima assim.`]);
      }

      return {
        viavel: true, avisos, paths, camadas: [{ paths, z0: 0, z1: esp }], bb, escala,
        corpos, esperado: 1, espessura: esp,
        nome, numero: '',
        larguraReal: bb.w, alturaReal: bb.h,
        furo: med.furo, parede: med.parede,
        dils: T.dilatacoes(nome),
        finoArea: fino.area,
      };
    }

    return { gerar, aba };
  }

  return { Gerador, MEDIDAS, TAMANHOS, circulo, SIZE };
});
