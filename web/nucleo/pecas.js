// O registro de pecas: o que a plataforma precisa saber para desenhar UMA
// tela que serve qualquer gerador.
//
// No C1 eu declarei os parametros do letreiro como dado e nao escrevi o
// renderizador, dizendo: "formulario generico escrito contra UM formulario
// acerta por acaso; o C2 traz o segundo". O C2 trouxe o topo de bolo, o C4
// traz o chaveiro -- e agora sao dois, com exigencias que brigam entre si:
//
//   topo de bolo   12 a 20 cm   nome + idade   quebra na CONEXAO das letras
//   chaveiro        3 a  7 cm   so o nome      quebra na PAREDE do furo
//
// Escrever a tela contra os dois de uma vez e o que separa abstracao de
// adivinhacao. O que sobrou aqui e exatamente o que difere; tudo que e igual
// ficou na tela.
//
// Acrescentar uma peca nova e: um modulo de geometria com `gerar(pedido)`,
// mais uma entrada aqui. A tela, as rotas, o catalogo, a vistoria, a
// estimativa, o preco e o registro de geracao vem de graca.
(function (root, fabrica) {
  const M = fabrica(root);
  if (typeof module === 'object' && module.exports) module.exports = M;
  else root.MorumbiPecas = M;
})(typeof window !== 'undefined' ? window : globalThis, function (root) {

  function modulo(nome) {
    if (typeof module === 'object' && module.exports) return require('./' + nome + '.js');
    return root['Morumbi' + nome.charAt(0).toUpperCase() + nome.slice(1)];
  }

  const PECAS = {
    topo: {
      tipo: 'topo',
      nome: 'Topo de bolo',
      rotulo: 'topo de bolo',
      sku: 'TB',                      // §11: M3D-TB-001
      campos: ['nome', 'numero'],     // quais o cadastro pode oferecer
      rotuloNumero: 'Idade ou número',
      chamada: 'GERAR MEU TOPO',
      passo2: 'Escreva o que vai no topo',
      tudoCerto: 'Peça inteira, com haste firme e dentro da mesa.',
      // O documento do Samir manda: docs/topo-de-bolo-requisitos.md §4.
      get tamanhos() { return modulo('topo').TAMANHOS; },
      get geometria() { return modulo('topo'); },
      /** O que esta peca mostra nas medidas, alem do que toda peca mostra. */
      medidas(R) {
        return [['Hastes', `${R.hastes} de ${modulo('topo').MEDIDAS.haste.altura} mm`]];
      },
      aviso: 'Modelo <b>em teste</b>: o desenho está pronto e a peça é gerada, mas ela ' +
             'ainda não foi impressa e aprovada. Nenhum template vai para venda antes de ' +
             'sair da impressora e passar na mão — é a regra do §6 do documento.',
    },
    display: {
      tipo: 'display',
      nome: 'Display de mesa',
      rotulo: 'display de mesa',
      sku: 'DM',
      campos: ['nome', 'numero'],
      rotuloNumero: 'Idade ou número',
      chamada: 'GERAR MEU DISPLAY',
      passo2: 'Escreva o que vai no display',
      tudoCerto: 'Peça inteira, com pé firme e dentro da mesa.',
      get tamanhos() { return modulo('display').TAMANHOS; },
      get geometria() { return modulo('display'); },
      medidas(R) {
        return [['Pé', 'integrado, ' + modulo('display').MEDIDAS.pe.altura + ' mm']];
      },
      aviso: 'Modelo <b>em teste</b>: o desenho está pronto e a peça é gerada, mas ela ' +
             'ainda não foi impressa e aprovada. O display precisa ficar em pé na mesa ' +
             'sem apoio — imprima e confira antes de vender.',
    },
    chaveiro: {
      tipo: 'chaveiro',
      nome: 'Chaveiro de nome',
      rotulo: 'chaveiro',
      sku: 'CH',
      campos: ['nome'],
      chamada: 'GERAR MEU CHAVEIRO',
      passo2: 'Escreva o nome',
      tudoCerto: 'Peça inteira, com a argola no sólido e dentro da mesa.',
      get tamanhos() { return modulo('chaveiro').TAMANHOS; },
      get geometria() { return modulo('chaveiro'); },
      medidas(R) {
        return [['Argola', `furo de ${R.furo} mm, parede de ${R.parede} mm`]];
      },
      aviso: 'Chaveiro é peça de bolso: puxada por argola todo dia. O sistema recusa ' +
             'qualquer combinação em que a parede em volta do furo fique fina demais — ' +
             'mas o teste que vale continua sendo imprimir e pendurar na chave.',
    },
  };

  /** §11: M3D-TB-001_MARIA_5_18CM.3mf
   *
   * Vale para qualquer peca que venha de template -- e onde ela mora desde o
   * C4. Estava em topo.js, e o chaveiro precisaria da mesma regra: duas
   * copias e o dia em que uma delas ganha um traco a mais.
   *
   * O tamanho e o PEDIDO (o preset escolhido), e nao a largura medida: com a
   * medida, dois pedidos diferentes viravam o mesmo arquivo e um sobrescrevia
   * o outro na pasta de downloads.
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

  function peca(tipo) { return PECAS[tipo] || null; }
  function tipos() { return Object.keys(PECAS); }

  /** O prefixo de SKU de cada peca, para o cadastro validar. */
  function prefixos() {
    const fora = {};
    for (const t of tipos()) fora[t] = PECAS[t].sku;
    return fora;
  }

  return { PECAS, peca, tipos, prefixos, nomeDeArquivo };
});
