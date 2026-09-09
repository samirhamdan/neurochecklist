// Topo de bolo -- a PECA. O documento de requisitos do Samir e a fonte:
// docs/topo-de-bolo-requisitos.md.
//
// A engenharia toda deste arquivo esta no §6 dele: "conexoes entre letras,
// decoracao e haste devem ser estruturalmente seguras". Um topo de bolo e uma
// peca fina, espetada num bolo, carregada por criança. Se as letras nao
// formarem UM corpo so, e se a haste nao nascer debaixo de material solido,
// a peca chega quebrada -- e nao ha aviso na tela que conserte isso depois.
//
// Entao a peca e montada nesta ordem, e cada passo tem uma garantia:
//
//   1. o nome vira uma linha de letras que se TOCAM      (texto.js)
//   2. a idade, se houver, empilha com contato exigido   (texto.js)
//   3. a composicao e escalada para o tamanho pedido
//   4. a base -- se o modelo tiver -- liga a linha de baixo inteira
//   5. as hastes descem de onde HA material, nunca do vazio
//
// O passo 5 e o unico que nao da para resolver com geometria bonita: a haste
// vai onde couber. O codigo procura, e se nao achar lugar solido ele DIZ, em
// vez de devolver uma peca que se parte na primeira festa.
(function (root, fabrica) {
  const N = (typeof module === 'object' && module.exports)
    ? Object.assign({}, require('./nucleo.js'), require('./texto.js'),
                    { O: require('./oficina.js') })
    : Object.assign({}, root.MorumbiNucleo, root.MorumbiTexto,
                    { O: root.MorumbiOficina });
  const M = fabrica(root, N);
  if (typeof module === 'object' && module.exports) module.exports = M;
  else root.MorumbiTopo = M;
})(typeof window !== 'undefined' ? window : globalThis, function (root, N) {
  const { S, MESA, uniao, diferenca, interseccao, area, rotacionar, inflar,
          mover, escalar, caixa, analisar, retangulo, Texto, O } = N;

  const SIZE = 60;          // tamanho do glifo antes de escalar, como no letreiro

  // As medidas que o §6 pede que existam, com o numero e o porque de cada uma.
  const MEDIDAS = {
    espessura: 3,        // mm: topo de bolo padrao, 12 camadas de 0,24
    // O traco minimo mora na oficina: e medida da impressora, nao do produto.
    haste: {
      largura: 8,        // mm: estreita o bastante para nao rasgar a cobertura
      altura: 45,        // mm: entra no bolo e sobra para segurar
      encaixe: 4,        // mm: quanto ela sobe para dentro da peca
      areaMinima: 20,    // mm2 de contato solido -- menos que isso e uma dobradiça
    },
    base: {
      altura: 4,         // mm da barra que liga as letras por baixo
      folga: 0.5,        // mm de sobra em cada ponta
    },
    margemMesa: 12,      // mm: a peca nunca encosta na borda da mesa
  };

  // Presets do §4. Largura total da peca, em mm.
  const TAMANHOS = [120, 150, 180, 200];

  // Os templates NAO moram mais aqui.
  //
  // Ate o C2 eram uma constante neste arquivo, e acrescentar um pedia eu
  // mexer no codigo -- que e exatamente o que o §12 do documento veio
  // resolver. Desde o C3 eles sao linhas no banco, editadas pela tela
  // /templates, e a pagina os busca em /topo/templates.
  //
  // web/nucleo/templates-iniciais.json guarda os seis primeiros, e serve
  // apenas de SEMENTE para o banco -- nao e lido em tempo de execucao.

  /** §11: M3D-TB-001_MARIA_5_18CM.3mf
   *
   * O tamanho e o PEDIDO (o preset que a pessoa escolheu), e nao a largura
   * medida da peca. Com a largura medida, dois pedidos diferentes viravam o
   * mesmo arquivo -- 180 mm e 175 mm arredondam para 17CM, e um sobrescrevia
   * o outro na pasta de downloads sem avisar.
   */
  function nomeDeArquivo(sku, nome, numero, tamanhoMM, extensao) {
    const limpo = String(nome || '').toUpperCase().normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '').replace(/[^A-Z0-9]+/g, '-')
      .replace(/^-|-$/g, '') || 'SEM-NOME';
    const partes = [sku, limpo];
    if (numero !== undefined && numero !== null && String(numero) !== '') {
      partes.push(String(numero).replace(/[^0-9A-Za-z]/g, ''));
    }
    partes.push(Math.round(tamanhoMM / 10) + 'CM');
    return partes.join('_') + '.' + (extensao || 'stl');
  }

  function barra(x0, x1, y0, y1) { return retangulo(x0, y0, x1, y1); }

  // TODA forma daqui sai no sentido anti-horario, que e como o resto do
  // sistema entende "solido" -- e o mesmo sentido do `retangulo` do nucleo.
  //
  // Isto custou caro: o coracao saia no sentido horario, e com preenchimento
  // NonZero o Clipper o tratava como FURO. Unir o coracao ao nome estava
  // SUBTRAINDO ele. Na tela dava para ver a peca certa (o desenho ignora
  // sentido) e o corpo saia separado -- 12 arquivos com aresta nao-manifold.
  function antiHorario(pts) {
    let soma = 0;
    for (let i = 0; i < pts.length; i++) {
      const a = pts[i], b = pts[(i + 1) % pts.length];
      soma += (b.X - a.X) * (b.Y + a.Y);
    }
    return soma > 0 ? pts.slice().reverse() : pts;   // soma > 0 = horario
  }

  /** Um coracao parametrico, largura x altura, centrado em (0,0). */
  function coracao(larg, alt) {
    const pts = [];
    for (let i = 0; i < 120; i++) {
      const t = (i / 120) * Math.PI * 2;
      const x = 16 * Math.pow(Math.sin(t), 3);
      const y = 13*Math.cos(t) - 5*Math.cos(2*t) - 2*Math.cos(3*t) - Math.cos(4*t);
      pts.push({ X: Math.round(x/32 * larg * S), Y: Math.round(y/27 * alt * S) });
    }
    return [antiHorario(pts)];
  }

  /** Uma estrela de `pontas` pontas, raio externo r. */
  function estrela(r, pontas) {
    pontas = pontas || 5;
    const pts = [], ri = r * 0.42;
    for (let i = 0; i < pontas * 2; i++) {
      const a = (i / (pontas * 2)) * Math.PI * 2 - Math.PI / 2;
      const raio = i % 2 ? ri : r;
      pts.push({ X: Math.round(Math.cos(a) * raio * S), Y: Math.round(Math.sin(a) * raio * S) });
    }
    return [antiHorario(pts)];
  }

  /** Curva o texto num arco, deformando o contorno ponto a ponto.
   *
   * A primeira versao fatiava a linha em colunas e girava cada fatia. Nao
   * funciona: cada fatia gira em torno de um angulo diferente e elas se
   * afastam onde a peca e mais fina -- justamente na juncao entre duas letras.
   * Saiu com 142 pedaços soltos, e depois com 5. Quem acusou foi a trava do
   * download; na tela o desenho parecia certo.
   *
   * Deformar e continuo: cada ponto do contorno vai para a sua posicao polar,
   * e o que estava junto continua junto. Segmento longo vira corda em vez de
   * arco, entao os longos sao subdivididos antes.
   */
  function arquear(linha, aberturaGraus) {
    const bb = caixa(linha.paths);
    if (!(bb.w > 0)) return { paths: linha.paths, bb };
    const raio = bb.w / (aberturaGraus * Math.PI / 180);
    const cx = (bb.minX + bb.maxX) / 2;
    const passoMax = bb.w / 240;          // mm de corda antes de subdividir

    const dobrar = pt => {
      const x = pt.X / S - cx, y = pt.Y / S;
      const ang = x / raio, r = raio + y;
      return { X: Math.round(r * Math.sin(ang) * S),
               Y: Math.round((r * Math.cos(ang) - raio) * S) };
    };

    const fora = [];
    for (const poly of linha.paths) {
      const novo = [];
      for (let i = 0; i < poly.length; i++) {
        const a = poly[i], b = poly[(i + 1) % poly.length];
        novo.push(dobrar(a));
        const dx = (b.X - a.X) / S, dy = (b.Y - a.Y) / S;
        const n = Math.floor(Math.hypot(dx, dy) / passoMax);
        for (let k = 1; k < n; k++) {
          novo.push(dobrar({ X: a.X + (b.X - a.X) * k / n, Y: a.Y + (b.Y - a.Y) * k / n }));
        }
      }
      fora.push(novo);
    }
    const P = uniao([fora]);
    return { paths: P, bb: caixa(P) };
  }

  function Gerador(fontes) {
    const T = Texto(fontes, SIZE);

    /** Onde a haste pode nascer: procura material solido na faixa de baixo.
     *
     * Devolve o x do centro de uma haste que encosta em material de verdade,
     * ou null. Nao inventa: se nao ha onde encaixar, quem chamou avisa, e a
     * peca sai reprovada em vez de sair pela metade.
     */
    function lugarDaHaste(paths, bb, alvoX, medidas) {
      const h = medidas.haste;
      const topo = bb.minY + h.encaixe;
      const testar = cx => {
        const dedo = retangulo(cx - h.largura/2, bb.minY - 1, cx + h.largura/2, topo);
        return area(interseccao(paths, dedo));
      };
      let melhor = null, melhorArea = 0;
      // Varre a partir do alvo para os dois lados: o lugar ideal e onde o
      // desenho pediu; o aceitavel e o mais proximo dele que aguenta.
      for (let d = 0; d <= bb.w / 2; d += 1) {
        for (const cx of (d === 0 ? [alvoX] : [alvoX - d, alvoX + d])) {
          if (cx - h.largura/2 < bb.minX || cx + h.largura/2 > bb.maxX) continue;
          const a = testar(cx);
          if (a > melhorArea) { melhorArea = a; melhor = cx; }
          if (a >= h.areaMinima) return { x: cx, area: a, deslocou: Math.abs(cx - alvoX) };
        }
      }
      return { x: melhor, area: melhorArea, deslocou: null, fraca: true };
    }

    /** A barra que liga a linha de baixo inteira. §6: conexoes seguras. */
    function comBase(paths, bb, medidas) {
      const b = medidas.base;
      const barra = retangulo(bb.minX - b.folga, bb.minY - b.altura,
                              bb.maxX + b.folga, bb.minY + b.altura * 0.35);
      return uniao([paths, barra]);
    }

    /**
     * Monta o topo de bolo.
     *
     * pedido: { nome, numero, frase, tamanho, fonte, base, haste, forma,
     *           arco, espessura }
     */
    function gerar(pedido) {
      const med = Object.assign({}, MEDIDAS, pedido.medidas || {});
      const esp = pedido.espessura || med.espessura;
      const larguraAlvo = pedido.tamanho || TAMANHOS[2];
      T.usar(pedido.fonte || Object.keys(fontes)[0]);

      const nome = String(pedido.nome || '').toUpperCase().trim().replace(/\s+/g, ' ');
      if (!nome) return { viavel: false, motivo: 'Escreva o nome que vai no topo.' };

      const avisos = [];
      const linhas = [];

      // A frase (§5) vai por cima, menor: e complemento, nao o assunto.
      if (pedido.frase) {
        const f = T.linhaEncaixada(String(pedido.frase).toUpperCase().trim(), 1.8);
        linhas.push({ nome: 'frase', linha: f, escala: 0.45 });
      }
      linhas.push({ nome: 'nome', linha: T.linhaEncaixada(nome, 1.8), escala: 1 });
      // A idade (§5) vai embaixo e maior: e ela que se le do outro lado da mesa.
      if (pedido.numero !== undefined && pedido.numero !== null && pedido.numero !== '') {
        const n = T.linhaEncaixada(String(pedido.numero).trim(), 1.8);
        linhas.push({ nome: 'numero', linha: n, escala: 1.35 });
      }

      // Cada linha entra na sua propria escala antes de empilhar, senao a
      // idade sai do mesmo tamanho do nome e o topo perde a hierarquia.
      const postas = linhas.map(l => {
        const p = escalar(l.linha.paths, l.escala);
        return { nome: l.nome, paths: p, bb: caixa(p) };
      });

      // 1,5 mm de glifo alem do toque: e o que transforma "as linhas se
      // encostam" em "as linhas estao ligadas". Sem isso, a peca sai com
      // aresta nao-manifold e o fatiador recusa -- foi o que os 8 topos
      // quebrados ensinaram.
      let comp = T.empilhar(postas, 2.2, true, 1.5);
      if (comp.falhou) {
        avisos.push(['mal', 'As linhas não se encostam nem coladas. Use um nome mais ' +
                            'curto, ou tire a frase.']);
      }
      let paths = pedido.arco ? arquear({ paths: comp.paths }, pedido.arco).paths : comp.paths;

      // A forma decorativa (§9) entra ANTES de escalar, para acompanhar a peca.
      //
      // Ela pousa na MESMA LINHA DE BASE das letras, ao lado do nome, e e a
      // barra da base que a segura -- como segura as letras. Duas versoes
      // anteriores tentaram fazer a decoracao se agarrar ao texto sozinha:
      // no canto de cima ela so alcancava pela ponta, e ao lado e centrada
      // ela encostava na diagonal da ultima letra. Nos dois casos a ligacao
      // era um beijo, e o fatiador recusa aresta nao-manifold.
      //
      // A conferencia nao acontece aqui: acontece na peca PRONTA, la embaixo,
      // depois da base. E la que a ligacao existe de verdade.
      if (pedido.forma) {
        const bb0 = caixa(paths);
        const alt = bb0.h * 0.9;
        const desenho = pedido.forma === 'coracao' ? coracao(alt * 1.05, alt)
                      : pedido.forma === 'estrela' ? estrela(alt / 2)
                      : null;
        if (desenho) {
          const bbF = caixa(desenho);
          // Sobe um pouco a ponta de baixo: pousada exatamente na linha de
          // base, ela ficava tangente a barra -- ponta aguda encostando numa
          // aresta reta e a receita da aresta nao-manifold.
          const dy = bb0.minY + bbF.h * 0.08 - bbF.minY;
          const areaForma = Math.abs(area(desenho));

          // Vai entrando ate a AREA de contato com o texto ser de verdade.
          // A versao anterior parava no primeiro `corpos === 1`, e ali o
          // coracao ainda era um corpo separado que so a barra da base
          // segurava: dois corpos ate a base entrar, e nao-manifold depois.
          let posto = null;
          for (let invade = 0.15; invade <= 0.95; invade += 0.05) {
            const tenta = mover(desenho, bb0.maxX - bbF.w * invade - bbF.minX, dy);
            if (area(interseccao(tenta, paths)) >= areaForma * 0.04) { posto = tenta; break; }
          }
          if (!posto) {
            return { viavel: false, avisos,
                     motivo: 'A decoração não alcança o nome de jeito nenhum. Use um ' +
                             'nome mais longo, ou escolha um modelo sem decoração.' };
          }
          paths = uniao([paths, posto]);
        }
      }

      // Escala para a largura pedida, sem passar do que a mesa aguenta.
      const bb1 = caixa(paths);
      const util = MESA - med.margemMesa;
      const alturaComHaste = bb1.h + med.haste.altura;
      const escalaPedida = larguraAlvo / bb1.w;
      const tetoMesa = Math.min(util / bb1.w, (util - med.haste.altura) / bb1.h);
      const escala = Math.min(escalaPedida, tetoMesa);
      if (escala < escalaPedida - 1e-9) {
        avisos.push(['bem', `A peça foi reduzida para caber na mesa: sai com ` +
                            `${Math.round(bb1.w * escala)} mm em vez de ${larguraAlvo} mm.`]);
      }
      paths = escalar(paths, escala);
      let bb = caixa(paths);
      paths = mover(paths, -bb.minX, -bb.minY);
      bb = caixa(paths);

      // A base entra em MILIMETROS, depois da escala: uma barra de 4 mm e de
      // 4 mm no topo de 12 cm e no de 20 cm. Escalar junto faria a peca
      // pequena sair com base de papel.
      const temBase = pedido.base !== false;
      if (temBase) { paths = comBase(paths, bb, med); bb = caixa(paths); }

      // As hastes, pelo mesmo motivo, tambem sao em mm.
      const hastes = [];
      if (pedido.haste !== false) {
        const alvos = [bb.minX + bb.w * 0.28, bb.minX + bb.w * 0.72];
        for (const alvo of alvos) {
          const achado = lugarDaHaste(paths, bb, alvo, med);
          if (!achado || achado.x === null) {
            avisos.push(['mal', 'Não há material sólido para a haste nascer. ' +
                                'Ligue a base ou use um nome mais longo.']);
            continue;
          }
          if (achado.fraca) {
            avisos.push(['mal', 'A haste encosta em pouco material e a peça quebraria ' +
                                'no encaixe. Ligue a base.']);
          }
          if (achado.deslocou > 3) {
            avisos.push(['bem', `Uma haste andou ${Math.round(achado.deslocou)} mm para ` +
                                `nascer debaixo de material sólido.`]);
          }
          const h = med.haste;
          hastes.push(retangulo(achado.x - h.largura/2, bb.minY - h.altura,
                                achado.x + h.largura/2, bb.minY + h.encaixe));
        }
        if (hastes.length) { paths = uniao([paths].concat(hastes)); bb = caixa(paths); }
      }

      // §10: bloquear configuracoes frageis. O traco fino e o que mais some
      // na impressao, e e invisivel na tela: 1,2 mm parece linha, sai buraco.
      const fino = O.tracosFinos(paths, O.TRACO_MINIMO);
      if (fino.tudo) {
        return { viavel: false, avisos,
                 motivo: `A peça inteira ficou com traço abaixo de ${O.TRACO_MINIMO} mm. ` +
                         `Escolha um tamanho maior.` };
      }
      if (fino.fracao > 0.04) {
        avisos.push(['mal', `Partes da peça ficaram com traço abaixo de ${O.TRACO_MINIMO} mm ` +
                            `e podem sair falhadas. Aumente o tamanho.`]);
      }

      // O que fez oito topos passarem na vistoria e falharem no fatiador: o
      // coracao encostava no nome num PONTO. Um corpo so pelo Clipper, aresta
      // nao-manifold depois de extrudar.
      const conexao = O.conexaoFragil(paths);
      if (conexao.fragil) {
        return { viavel: false, avisos,
                 motivo: pedido.forma
                   ? 'A decoração só encosta no nome, sem largura de contato: ela sairia ' +
                     'solta na primeira festa. Use um nome mais longo ou um tamanho maior.'
                   : 'Duas partes da peça só se encostam, sem largura de contato: a malha ' +
                     'sai inválida e o fatiador recusa. Use um tamanho maior.' };
      }

      const corpos = analisar(paths).corpos;
      if (corpos !== 1) {
        avisos.push(['mal', `A peça saiu em ${corpos} partes soltas. Não imprima assim.`]);
      }

      const camadas = [{ paths, z0: 0, z1: esp }];
      return {
        viavel: true, avisos, paths, camadas, bb, escala,
        corpos, esperado: 1,
        espessura: esp,
        nome, numero: pedido.numero == null ? '' : String(pedido.numero),
        larguraReal: bb.w, alturaReal: bb.h,
        temBase, hastes: hastes.length,
        dils: T.dilatacoes(nome),
        finoArea: fino.area,
      };
    }

    return { gerar, lugarDaHaste };
  }

  return { Gerador, MEDIDAS, TAMANHOS, nomeDeArquivo,
           coracao, estrela, arquear, barra, SIZE };
});
