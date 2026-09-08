// Letreiro -- a PECA, e so ela.
//
// O que este arquivo tem e o que muda de um produto para outro: as medidas do
// letreiro, os seis modelos, e o desenho. Poligono, solido, STL e as medidas
// da mesa vem do nucleo -- se voce precisar mexer neles, mexa la, porque o
// proximo gerador usa os mesmos.
//
// A conta de por que isso vale a pena: das oito etapas que todo gerador
// percorre, sete sao do nucleo. Esta e a oitava.
(function (root, fabrica) {
  const N = (typeof module === 'object' && module.exports)
    ? Object.assign({}, require('./nucleo.js'), require('./texto.js'))
    : Object.assign({}, root.MorumbiNucleo, root.MorumbiTexto);
  const M = fabrica(root, N);
  if (typeof module === 'object' && module.exports) module.exports = M;
  else root.MorumbiLetreiro = M;
})(typeof window !== 'undefined' ? window : globalThis, function (root, N) {
  const { S, FT, MESA, cub, qua, pathToPolys, uniao, diferenca, inflar, mover,
          escalar, caixa, analisar, retangulo, grupos, stlBinario } = N;

  function api() { return root.ClipperLib || require('clipper-lib'); }

  const SIZE = 60;
  const MARGEM = 1.8;     // mm: invasao extra alem do contato minimo entre letras


  // Luminaria: a peca deixa de ser um bloco macico e vira caixa oca, com a
  // frente fina o bastante para passar luz e o fundo aberto para entrar a
  // fita de LED. Sem isso, os 60 mm imprimem 600 cm3 de plastico em 10 h e
  // nao ha onde por a fita.
  const LUMINARIA = {
    face: 1.6,        // mm de frente: acima de ~2 mm o PLA branco para de difundir
    parede: 2.4,      // 6 perimetros de 0,4 — aguenta o vao e nao deixa vazar luz
    canal: 10,        // largura util minima do canal, para a fita caber deitada
    cabo: 7,          // largura do rasgo de entrada do cabo
    alturaCabo: 6     // altura do rasgo, medida a partir do fundo aberto
  };

  const PRODUTOS = {
    classico: { nome: 'Clássico', fonte: 'luckiest', capa: 3 },
    magia:    { nome: 'Magia',    fonte: 'luckiest', faixa: 2.5, cores: 2 },
    gamer:    { nome: 'Gamer',    fonte: 'gamer',    capa: 3, alturaMin: 42, cores: 2 },
    cinema:   { nome: 'Cinema',   fonte: 'cinema',   capa: 3, cores: 2 },
    futuro:   { nome: 'Futuro',   fonte: 'futuro',   capa: 3, cores: 2 },
    terror:   { nome: 'Terror',   fonte: 'terror',   capa: 3, cores: 2 }
  };

  // Escava a peca para virar luminaria: parede em volta, frente fina na
  // saida da luz, fundo aberto e um rasgo lateral para o cabo.
  // Devolve null quando o traco e fino demais para parede dos dois lados --
  // ai a peca continua macica, e quem chamou avisa por que.
  function canalDeLuz(contorno, espessura) {
    const cavidade = uniao([inflar(contorno, -LUMINARIA.parede)]);
    if (!cavidade.length) return null;

    // A fita so entra se sobrar uma faixa da largura dela: erodir o canal
    // pela metade da largura e ver se algo resiste responde isso.
    const folga = uniao([inflar(cavidade, -LUMINARIA.canal/2)]);
    const bb = caixa(contorno);
    const meio = (bb.minX + bb.maxX) / 2;
    const rasgo = retangulo(meio - LUMINARIA.cabo/2, bb.minY - LUMINARIA.parede*2,
                            meio + LUMINARIA.cabo/2, bb.minY + LUMINARIA.parede*2);
    const anel = diferenca(contorno, cavidade);
    const zFace = espessura - LUMINARIA.face;
    const comRasgo = diferenca(anel, rasgo);
    const alturaCabo = Math.min(LUMINARIA.alturaCabo, zFace/2);

    return {
      cavidade, anel, zFace,
      passaFita: folga.length > 0,
      areaCanal: cavidade.length ? Math.abs(api().Clipper.Area(cavidade[0]))/(S*S) : 0,
      // O fundo (z=0) fica aberto de proposito: e por ele que entra a fita.
      camadasCorpo: [
        { paths: comRasgo, z0: 0,          z1: alturaCabo },
        { paths: anel,     z0: alturaCabo, z1: zFace }
      ],
      camadasFace: [ { paths: contorno, z0: zFace, z1: espessura } ]
    };
  }

  // divide o nome em ate 2 linhas, equilibrando o comprimento
  function dividirLinhas(word) {
    const ps = word.split(' ').filter(Boolean);
    if (ps.length <= 1) return [word];
    let corte = 1, dif = Infinity;
    for (let i=1;i<ps.length;i++) {
      const a = ps.slice(0,i).join('').length, b = ps.slice(i).join('').length;
      if (Math.abs(a-b) < dif) { dif = Math.abs(a-b); corte = i; }
    }
    return [ps.slice(0,corte).join(' '), ps.slice(corte).join(' ')];
  }

  // altura padrao por tamanho da maior linha: nome comprido pede letra menor
  function alturaAuto(linhas, larguraAlvo) {
    const n = Math.max(...linhas.map(l => l.replace(/ /g,'').length));
    const base = n <= 4 ? 60 : n <= 6 ? 55 : 48;
    return Math.round(base * ((larguraAlvo || 220) / 220));
  }

  function Gerador(fontes) {
    // A maquina de texto e da plataforma desde o C2: o topo de bolo precisa
    // dela letra por letra, com a mesma garantia de que as letras se tocam.
    const T = N.Texto(fontes, SIZE);
    const { letra, linhaEncaixada, linhaNatural, empilhar } = T;

    // 1o garante que a moldura une tudo numa peca so;
    // 2o, dentro do que une, pega a maior que ainda preserva os vazados
    function escolherMoldura(paths, teto) {
      const base = analisar(paths).vazados;
      const escala = [1.2, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 7, 8, 10, 12, 15];
      let dMin = null;
      for (const d of escala) {
        if (analisar(uniao([inflar(paths, d)])).corpos === 1) { dMin = d; break; }
      }
      if (dMin === null) return { d: 1.2, une: false, preserva: false };
      // maior valor ate o teto que une e preserva os vazados
      for (let i = escala.length - 1; i >= 0; i--) {
        const d = escala[i];
        if (d < dMin || d > teto) continue;
        const a = analisar(uniao([inflar(paths, d)]));
        if (a.corpos === 1 && a.vazados >= base) return { d, une: true, preserva: true };
      }
      // nenhuma ate o teto serviu: procura acima dele a menor que preserva
      for (const d of escala) {
        if (d < dMin || d > teto * 2) continue;
        const a = analisar(uniao([inflar(paths, d)]));
        if (a.corpos === 1 && a.vazados >= base) return { d, une: true, preserva: true, acimaDoTeto: true };
      }
      const a = analisar(uniao([inflar(paths, dMin)]));
      return { d: dMin, une: true, preserva: a.vazados >= base };
    }

    function gerar(nome, larguraAlvo, espessura, produto, duasLinhas, alturaMax, baseMM, luminaria) {
      const cfg = PRODUTOS[produto] || PRODUTOS.classico;
      // Peca grossa e luminaria por padrao: e o que a espessura de 60 mm da
      // interface sempre prometeu. Da para forcar dos dois lados passando o
      // ultimo argumento.
      if (luminaria === undefined) luminaria = espessura >= 40;
      T.usar(cfg.fonte);
      const word = nome.toUpperCase().trim().replace(/\s+/g, ' ');
      const linhas = duasLinhas === false ? [word] : dividirLinhas(word);

      const dils = T.dilatacoes(word);

      const altUsada = alturaMax === 'auto' ? alturaAuto(linhas, larguraAlvo) : alturaMax;
      const tetoAlt = altUsada ? altUsada * linhas.length : Infinity;
      // alguns produtos nao podem achatar: a peca cresce em largura para manter altura minima
      const pisoAlt = cfg.alturaMin ? cfg.alturaMin * linhas.length * ((larguraAlvo||220)/220) : 0;
      // com base: letras no espacamento natural, ligadas por uma barra na linha de base
      const comBase = baseMM > 0;
      const linhaComBase = (txt, esc) => {
        const L = linhaNatural(txt);
        const h = baseMM / esc, m = 0.5 / esc;
        // ancora a base no ponto mais baixo das letras, nao na linha de base da fonte
        const y0 = L.bb.minY, y1 = L.bb.minY + h;
        const barra = [[{X:Math.round((L.bb.minX-m)*S),Y:Math.round(y0*S)},{X:Math.round((L.bb.maxX+m)*S),Y:Math.round(y0*S)},
                        {X:Math.round((L.bb.maxX+m)*S),Y:Math.round(y1*S)},{X:Math.round((L.bb.minX-m)*S),Y:Math.round(y1*S)}]];
        const P = uniao([L.paths, barra]);
        return { paths: P, bb: caixa(P) };
      };
      let esc = 1, EMP;
      for (let i=0;i<3;i++) {
        const ls = linhas.map(t => comBase ? linhaComBase(t, esc) : linhaEncaixada(t, MARGEM/esc));
        EMP = empilhar(ls, 1.5/esc, true);
        const b = caixa(EMP.paths);
        const tetoMesa = (MESA * Math.SQRT2 - 12) / (b.w + b.h);   // limite fisico da impressora
        esc = Math.min(Math.max(Math.min(larguraAlvo / b.w, tetoAlt / b.h), pisoAlt / b.h), tetoMesa);
      }
      const encaixado = escalar(EMP.paths, esc);

      let escN = 1, NAT;
      for (let i=0;i<3;i++) {
        NAT = empilhar(linhas.map(t => linhaNatural(t)), 2.0/escN, false);
        const b = caixa(NAT.paths);
        const tetoMesaN = (MESA * Math.SQRT2 - 50) / (b.w + b.h);   // desconta a moldura que vem depois
        escN = Math.min(Math.max(Math.min(larguraAlvo / b.w, tetoAlt / b.h), pisoAlt / b.h), tetoMesaN);
      }
      const nat = escalar(NAT.paths, escN);

      const t = espessura;
      const simples = { rot:'', camadas:[{paths:encaixado, z0:0, z1:t}],
                        bb: caixa(encaixado), corpos: analisar(encaixado).corpos, esperado:1 };
      const base = { word, linhas, duas: linhas.length>1, dils, esc, produto,
                     nomeProduto: cfg.nome, simples, viavel:true, motivo:null,
                     larguraAlvo, larguraReal: caixa(encaixado).w, altUsada, comBase };

      if (luminaria) {
        const canal = canalDeLuz(encaixado, t);
        if (!canal) {
          // Traco fino demais para parede dos dois lados: sai macica mesmo,
          // e o aviso diz o que fazer (letra maior ou produto mais grosso).
          return Object.assign(base, { luminaria: { possivel: false, parede: LUMINARIA.parede,
            motivo: 'O traço da letra não comporta parede de ' + LUMINARIA.parede +
                    'mm dos dois lados. Aumente a largura ou escolha uma fonte mais cheia.' } });
        }
        const bbL = caixa(encaixado);
        const info = { possivel: true, passaFita: canal.passaFita, face: LUMINARIA.face,
                       parede: LUMINARIA.parede, canal: LUMINARIA.canal,
                       cabo: LUMINARIA.cabo, areaCanal: canal.areaCanal,
                       motivo: canal.passaFita ? null :
                         'O canal ficou mais estreito que os ' + LUMINARIA.canal +
                         'mm da fita. Serve para LED em fio, não para fita.' };
        // Peca UNICA, sempre. Separar a frente em outra cor parece bom, mas
        // nao fecha: numa letra com contra-forma ("O", "A", "e"), escavar
        // deixa a parede de dentro como um anel solto, preso a nada. Quem
        // segura essa parede e a frente — tirando a frente, ela cai.
        const inteira = { rot: 'LUMINARIA',
          camadas: canal.camadasCorpo.concat(canal.camadasFace),
          bb: bbL, corpos: analisar(encaixado).corpos, esperado: 1 };
        base.simples = inteira;
        const ilhas = analisar(canal.anel).corpos;
        if (ilhas > 1) {
          info.paredeSolta = ilhas - 1;
          info.motivoPecaUnica = (ilhas === 2
            ? 'A contra-forma da letra deixa uma parede interna que só a frente segura'
            : 'As contra-formas deixam ' + (ilhas-1) + ' paredes internas que só a frente segura')
            + ': a luminária sai em peça única.';
        }
        return Object.assign(base, { luminaria: info, pecas: [inteira] });
      }

      if (produto === 'magia') {
        const M = escolherMoldura(nat, 3.5), dA = M.une ? M.d : 0;
        if (!dA || !M.preserva) {
          return Object.assign(base, { viavel:false, pecas:[], delta:dA,
            motivo:'Nesse tamanho a moldura fecharia o miolo das letras. Use um tamanho maior ou o modelo Clássico.' });
        }
        const faixa = Math.min(cfg.faixa, (t-1)/2), h1 = t - faixa;
        const camadas = [
          { rot:'MAGIA-BASE', p: uniao([inflar(nat,dA)]), z0:0,  z1:h1 },
          { rot:'MAGIA-FACE', p: nat,                     z0:h1, z1:t }
        ];
        return Object.assign(base, { delta:dA, pecas: camadas.map((c,i) => ({
          rot:c.rot, camadas:[{paths:c.p, z0:c.z0, z1:c.z1}], bb:caixa(c.p),
          corpos: analisar(c.p).corpos, esperado: i===0 ? 1 : null })) });
      }

      const M = escolherMoldura(nat, 4.0);
      const delta = M.d;
      const moldura = uniao([inflar(nat, delta)]);
      const cap = Math.min(cfg.capa, t-1), corpo = t - cap;
      const anel = diferenca(moldura, nat);
      return Object.assign(base, { delta, molduraFechouVazados: M.une && !M.preserva, pecas: [
        { rot:'HIBRIDO-CORPO', camadas:[{paths:moldura,z0:0,z1:corpo},{paths:anel,z0:corpo,z1:t}],
          bb:caixa(moldura), corpos:analisar(moldura).corpos, esperado:1 },
        { rot:'HIBRIDO-CAPA', camadas:[{paths:nat,z0:corpo,z1:t}],
          bb:caixa(nat), corpos:analisar(nat).corpos, esperado:null }
      ]});
    }
    return { gerar, letra };
  }

  // Os parametros do letreiro, DECLARADOS -- nao desenhados.
  //
  // Hoje quem monta esses controles e o HTML da tela, a mao. Isto aqui e a
  // mesma verdade em forma de dado, e ha teste comparando as duas: opcao que
  // existe na tela e nao esta aqui (ou o contrario) e uma das duas mentindo.
  //
  // Nao ha renderizador. De proposito: um formulario generico escrito para um
  // unico formulario acerta por acaso. O C2 traz o topo de bolo, e ai sao
  // dois -- ai da para escrever o renderizador contra duas exigencias reais
  // em vez de contra uma imaginada.
  const PARAMETROS = [
    { campo: "nome",     tipo: "texto",  rotulo: "Nome",     padrao: "João Pedro" },
    { campo: "produto",  tipo: "escolha", rotulo: "Produto", padrao: "classico",
      opcoes: Object.keys(PRODUTOS).map(k => ({ valor: k, rotulo: PRODUTOS[k].nome })) },
    { campo: "largura",  tipo: "escolha", rotulo: "Tamanho", padrao: 220, unidade: "mm",
      opcoes: [{ valor: 170, rotulo: "17 cm" }, { valor: 220, rotulo: "22 cm" },
               { valor: 280, rotulo: "28 cm" }] },
    { campo: "esp",      tipo: "escolha", rotulo: "Espessura", padrao: 12, unidade: "mm",
      opcoes: [{ valor: 6, rotulo: "6 mm — parede" }, { valor: 12, rotulo: "12 mm — mesa" },
               { valor: 60, rotulo: "60 mm — luminária" }] },
    { campo: "versao",   tipo: "escolha", rotulo: "Cores", padrao: 1,
      opcoes: [{ valor: 1, rotulo: "1 cor" }, { valor: 2, rotulo: "2 cores" }],
      // Cinco dos seis modelos mandam no numero de cores; so o Classico deixa
      // escolher. A tela esconde este controle quando o modelo manda.
      quando: est => !(PRODUTOS[est.produto] || {}).cores },
    { campo: "duas",     tipo: "escolha", rotulo: "Nome composto", padrao: true,
      opcoes: [{ valor: true, rotulo: "Duas linhas" }, { valor: false, rotulo: "Uma linha" }],
      quando: est => /\s/.test(String(est.nome || "").trim()) },
    { campo: "alt",      tipo: "escolha", rotulo: "Altura da letra", padrao: "auto" },
    { campo: "base",     tipo: "escolha", rotulo: "Base", padrao: 8, unidade: "mm" },
  ];

  return { Gerador, alturaAuto, dividirLinhas, canalDeLuz, PARAMETROS,
           SIZE, MARGEM, LUMINARIA, PRODUTOS };
});
