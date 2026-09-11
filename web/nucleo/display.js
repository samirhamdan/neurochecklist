// Display de mesa -- a peca que fica em pe na mesa do bolo.
//
// Diferente do topo (que espeta no bolo com hastes) e do chaveiro (que vai
// no bolso com argola), o display FICA EM PE sozinho. Por isso ele tem um
// pe integrado: uma barra larga na parte de baixo que, quando a peca e
// colocada de pe, toca a mesa e segura a peca.
//
// A forma de fundo (retangulo, circulo, estrela, coracao) ENVOLVE o texto,
// e nao e colada ao lado dele como no topo de bolo. O texto fica centralizado
// dentro da forma, com uma moldura de respiro em volta.
//
// O pe e parte da mesma peca (mesma extrusao). Nao ha encaixe nem montagem:
// imprime plano, levanta e esta de pe. Ele e mais largo que a forma para
// nao tombar -- e o mesmo principio da base do topo, mas mais generoso.
(function (root, fabrica) {
  const N = (typeof module === 'object' && module.exports)
    ? Object.assign({}, require('./nucleo.js'), require('./texto.js'),
                    { O: require('./oficina.js') })
    : Object.assign({}, root.MorumbiNucleo, root.MorumbiTexto,
                    { O: root.MorumbiOficina });
  const M = fabrica(root, N);
  if (typeof module === 'object' && module.exports) module.exports = M;
  else root.MorumbiDisplay = M;
})(typeof window !== 'undefined' ? window : globalThis, function (root, N) {
  const { S, MESA, uniao, diferenca, interseccao, area, mover, escalar,
          caixa, analisar, retangulo, inflar, Texto, O } = N;

  const SIZE = 60;

  const MEDIDAS = {
    espessura: 5,        // mm: mais grosso que topo (3mm) para ficar em pe
    margemMesa: 12,
    moldura: 8,          // mm: borda em volta do texto na forma
    pe: {
      altura: 6,         // mm: altura da barra que toca a mesa
      orelha: 6,         // mm: quanto o pe passa da forma de cada lado
      folga: 0.5,        // mm de sobra em cada ponta
    },
  };

  var TAMANHOS = [100, 150, 200];

  function antiHorario(pts) {
    var soma = 0;
    for (var i = 0; i < pts.length; i++) {
      var a = pts[i], b = pts[(i + 1) % pts.length];
      soma += (b.X - a.X) * (b.Y + a.Y);
    }
    return soma > 0 ? pts.slice().reverse() : pts;
  }

  function retanguloArredondado(w, h, r) {
    r = Math.min(r || 0, w / 2, h / 2);
    if (r < 1) return retangulo(-w / 2, -h / 2, w / 2, h / 2);
    var pts = [], segs = 12;
    var cantos = [
      { cx:  w/2 - r, cy:  h/2 - r, a0: 0,              a1: Math.PI / 2 },
      { cx: -w/2 + r, cy:  h/2 - r, a0: Math.PI / 2,    a1: Math.PI },
      { cx: -w/2 + r, cy: -h/2 + r, a0: Math.PI,        a1: 3 * Math.PI / 2 },
      { cx:  w/2 - r, cy: -h/2 + r, a0: 3 * Math.PI / 2, a1: 2 * Math.PI },
    ];
    for (var ci = 0; ci < cantos.length; ci++) {
      var c = cantos[ci];
      for (var j = 0; j <= segs; j++) {
        var ang = c.a0 + (c.a1 - c.a0) * j / segs;
        pts.push({ X: Math.round((c.cx + Math.cos(ang) * r) * S),
                    Y: Math.round((c.cy + Math.sin(ang) * r) * S) });
      }
    }
    return [antiHorario(pts)];
  }

  function circuloForma(raio) {
    var n = 48, pts = [];
    for (var i = 0; i < n; i++) {
      var a = (i / n) * Math.PI * 2;
      pts.push({ X: Math.round(Math.cos(a) * raio * S),
                  Y: Math.round(Math.sin(a) * raio * S) });
    }
    return [antiHorario(pts)];
  }

  function coracaoForma(larg, alt) {
    var pts = [];
    for (var i = 0; i < 120; i++) {
      var t = (i / 120) * Math.PI * 2;
      var x = 16 * Math.pow(Math.sin(t), 3);
      var y = 13*Math.cos(t) - 5*Math.cos(2*t) - 2*Math.cos(3*t) - Math.cos(4*t);
      pts.push({ X: Math.round(x / 32 * larg * S), Y: Math.round(y / 27 * alt * S) });
    }
    return [antiHorario(pts)];
  }

  function estrelaForma(r, pontas) {
    pontas = pontas || 5;
    var pts = [], ri = r * 0.42;
    for (var i = 0; i < pontas * 2; i++) {
      var a = (i / (pontas * 2)) * Math.PI * 2 - Math.PI / 2;
      var raio = i % 2 ? ri : r;
      pts.push({ X: Math.round(Math.cos(a) * raio * S),
                  Y: Math.round(Math.sin(a) * raio * S) });
    }
    return [antiHorario(pts)];
  }

  function forma(tipo, w, h) {
    if (tipo === 'circulo')  return circuloForma(Math.min(w, h) / 2);
    if (tipo === 'estrela')  return estrelaForma(Math.min(w, h) / 2);
    if (tipo === 'coracao')  return coracaoForma(w, h);
    return retanguloArredondado(w, h, Math.min(w, h) * 0.08);
  }

  function Gerador(fontes) {
    var T = Texto(fontes, SIZE);

    function gerar(pedido) {
      var med = Object.assign({}, MEDIDAS, pedido.medidas || {});
      var esp = pedido.espessura || med.espessura;
      var larguraAlvo = pedido.tamanho || TAMANHOS[1];
      T.usar(pedido.fonte || Object.keys(fontes)[0]);

      var nome = String(pedido.nome || '').toUpperCase().trim().replace(/\s+/g, ' ');
      var numero = (pedido.numero !== undefined && pedido.numero !== null &&
                    String(pedido.numero) !== '') ? String(pedido.numero).trim() : '';

      if (!nome && !numero) {
        return { viavel: false, motivo: 'Escreva um nome ou número para o display.' };
      }

      var avisos = [];
      var linhas = [];

      if (nome) {
        linhas.push({ nome: 'nome', linha: T.linhaEncaixada(nome, 1.8), escala: 1 });
      }
      if (numero) {
        var n = T.linhaEncaixada(numero, 1.8);
        linhas.push({ nome: 'numero', linha: n, escala: nome ? 1.5 : 2.5 });
      }

      var postas = linhas.map(function (l) {
        var p = escalar(l.linha.paths, l.escala);
        return { nome: l.nome, paths: p, bb: caixa(p) };
      });

      var comp;
      if (postas.length > 1) {
        comp = T.empilhar(postas, 2.0, true, 1.2);
        if (comp.falhou) {
          avisos.push(['mal', 'As linhas não se ligam. Use um nome mais curto.']);
        }
      } else {
        comp = { paths: postas[0].paths };
      }

      var textoPaths = comp.paths;
      var bbTexto = caixa(textoPaths);

      // A forma de fundo envolve o texto com uma moldura de respiro.
      var moldura = med.moldura;
      var tipoForma = pedido.forma || 'retangulo';
      var fW = bbTexto.w + moldura * 2;
      var fH = bbTexto.h + moldura * 2;
      var fundo = forma(tipoForma, fW, fH);
      var bbFundo = caixa(fundo);

      // Centraliza o texto dentro da forma.
      var dx = (bbFundo.minX + bbFundo.maxX) / 2 - (bbTexto.minX + bbTexto.maxX) / 2;
      var dy = (bbFundo.minY + bbFundo.maxY) / 2 - (bbTexto.minY + bbTexto.maxY) / 2;
      textoPaths = mover(textoPaths, dx, dy);

      var paths = uniao([fundo, textoPaths]);

      // Escala para a largura pedida.
      var bb1 = caixa(paths);
      var util = MESA - med.margemMesa;
      var escalaPedida = larguraAlvo / bb1.w;
      var tetoMesa = util / Math.max(bb1.w, bb1.h + med.pe.altura);
      var esc = Math.min(escalaPedida, tetoMesa);
      if (esc < escalaPedida - 1e-9) {
        avisos.push(['bem', 'A peça foi reduzida para caber na mesa: sai com ' +
                            Math.round(bb1.w * esc) + ' mm em vez de ' + larguraAlvo + ' mm.']);
      }
      paths = escalar(paths, esc);
      var bb = caixa(paths);
      paths = mover(paths, -bb.minX, -bb.minY);
      bb = caixa(paths);

      // O pe: uma barra larga embaixo que segura a peca em pe na mesa.
      var pe = med.pe;
      var peBarra = retangulo(
        bb.minX - pe.orelha,
        bb.minY - pe.altura,
        bb.maxX + pe.orelha,
        bb.minY + pe.altura * 0.35
      );
      paths = uniao([paths, peBarra]);
      bb = caixa(paths);

      // Traco fino.
      var fino = O.tracosFinos(paths, O.TRACO_MINIMO);
      if (fino.tudo) {
        return { viavel: false, avisos: avisos,
                 motivo: 'A peça inteira ficou com traço abaixo de ' + O.TRACO_MINIMO +
                         ' mm. Escolha um tamanho maior.' };
      }
      if (fino.fracao > 0.04) {
        avisos.push(['mal', 'Partes da peça ficaram com traço abaixo de ' + O.TRACO_MINIMO +
                            ' mm e podem sair falhadas. Aumente o tamanho.']);
      }

      // Conexao fragil.
      var conexao = O.conexaoFragil(paths);
      if (conexao.fragil) {
        return { viavel: false, avisos: avisos,
                 motivo: 'Duas partes da peça só se encostam, sem largura de contato. ' +
                         'Use um nome mais curto ou um tamanho maior.' };
      }

      var corpos = analisar(paths).corpos;
      if (corpos !== 1) {
        avisos.push(['mal', 'A peça saiu em ' + corpos + ' partes soltas. Não imprima assim.']);
      }

      var camadas = [{ paths: paths, z0: 0, z1: esp }];
      return {
        viavel: true, avisos: avisos, paths: paths, camadas: camadas, bb: bb,
        escala: esc, corpos: corpos, esperado: 1,
        espessura: esp,
        nome: nome, numero: numero,
        larguraReal: bb.w, alturaReal: bb.h,
        temPe: true,
        dils: nome ? T.dilatacoes(nome) : {},
        finoArea: fino.area,
      };
    }

    return { gerar: gerar };
  }

  return { Gerador: Gerador, MEDIDAS: MEDIDAS, TAMANHOS: TAMANHOS, SIZE: SIZE,
           retanguloArredondado: retanguloArredondado, circuloForma: circuloForma,
           coracaoForma: coracaoForma, estrelaForma: estrelaForma };
});
