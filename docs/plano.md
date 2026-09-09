# Plano de construção — do gerador de peça ao controle da oficina

Duas trilhas, numeradas **por dependência** e não por preferência.

- **Gestão (1 a 9)** — o que registra: cadastros, pedidos, produção,
  financeiro, loja, marketplace.
- **Criação (C1 a C4)** — o que gera: a plataforma de geradores e os
  produtos personalizáveis que nascem dela.

As duas se encontram em dois pontos, e só neles: o **produto** (sprint 1) e
a **loja** (sprint 8). Fora disso, avançam independentes — e você escolhe
qual anda primeiro.

Versão em página: publicada como artefato, mesma matéria deste arquivo.
Este arquivo é a fonte da verdade; a página é a leitura.

## Ponto de partida

Três coisas já rodam em `morumbi3d.duckdns.org`. Todas **leem ou geram**.
Nenhuma **registra** — e é esse o buraco que o plano fecha.

| No ar | O quê |
| --- | --- |
| Painel | Fila agrupada por cor, pedidos abertos, estoque de filamento. Só lê |
| Gerador de letreiros | Nome digitado vira placa. 6 temas, 3 tamanhos, luminária de 60 mm |
| Gerador de logo 3D | Imagem vira STL: recorte de fundo, vetorização, traço fino |
| **Falta** | **Tudo que escreve.** Sem isso o painel não sai do lugar |

## O que o Sistema3D mostrou

22 telas analisadas. As anotações do Samir no PDF decidiram três linhas.

| Tela deles | Decisão | Por quê |
| --- | --- | --- |
| Produtos | Adaptar | Peso, tempo e filamento geram o custo. No nosso, **solta o STL e o peso vem do analisador de malha que já existe** — eles digitam à mão |
| Filamentos | Usar | Estoque em gramas com mínimo. O painel já mostra; falta cadastrar |
| Insumos | Usar | Parafuso, imã, embalagem. Baixa junto com a produção |
| Clientes | Adaptar | Mais o **canal de origem**, que responde de onde vêm os pedidos |
| Orçamento | Adaptar | Vira o mesmo registro do pedido, em outra situação |
| Produção · 5 telas | Adaptar | São cinco telas idênticas. Viram **uma só**, kanban e lista |
| Compras | Usar | É o que faz o custo ser real: preço da última compra, não chute |
| Financeiro | Usar | Categorias, contas a pagar e receber, parcelamento e recorrência |
| Relatórios · 5 | Usar | Produzidos, vendas, financeiro, perda, filamento gasto |
| Parâmetros | Usar | Logo e cores dos PDFs |
| Precificação | Adaptar | A deles é hora × valor + margem. **A nossa já é melhor** — casca, preenchimento, suporte, purga por troca e piso de R$ 18 + R$ 0,60/g |
| Comodato | **Fora** | Decisão do Samir: locação é da Morumbi Festas |
| Planos e assinatura | **Fora** | Eles vendem para muitas empresas; este sistema serve uma |
| Instância e perfil | **Fora** | Mesma razão |

## Um pedido, uma vida

Orçamento e pedido deixam de ser dois cadastros e viram **um registro que
muda de situação**:

```
Orçamento → Aprovado → Em produção → Montagem → À entregar → Entregue
```

Cada passagem faz algo acontecer sozinho: entrar em **produção** baixa
filamento e insumo; sair como **entregue** gera a conta a receber.

---

## Sprint 1 — Cadastros e custo da peça ✅ FEITO
**Tamanho M · sem dependência**

Sem produto não existe pedido; sem filamento o produto não tem custo.

**Entra:** filamento (marca, tipo, cor, estoque g, mínimo); insumo (unidade,
estoque, mínimo, valor); produto (peso, tempo, filamento padrão, insumos,
fotos, arquivos STL/3MF). **Soltar o STL preenche peso e tempo** pelo
analisador de malha — e também **as medidas da caixa**, porque o mesmo
analisador já calcula a caixa que envolve a peça. Isso é o que faz a cotação
de frete do sprint 8 sair sozinha.

Produto guarda ainda **preço por canal**. Vender na Shopee pelo preço do
balcão é vender no prejuízo: a comissão sai do seu bolso, não do cliente.

**Eu testo:** peso lido do STL bate com o do analisador, peça a peça ·
produto sem filamento não salva com custo zero fingido · estoque abaixo do
mínimo aparece no painel · caixa calculada cabe a peça girada, e não só reta.

**Você confere:** cadastre o letreiro ANA de 22 cm soltando o STL que o
gerador já produz; peso e custo têm que aparecer sozinhos e bater com a
balança depois de imprimir.

## Sprint 2 — Clientes e pedidos ✅ FEITO
**Tamanho M · depende do 1**

**Uma distinção que só apareceu ao construir:** o **pedido** tem *situação
comercial* (orçamento → aprovado → entregue → cancelado) e a **peça** tem
*etapa de produção* (na fila → imprimindo → acabamento). Estavam misturadas:
o semeador gravava pedido com status "imprimindo", que é etapa de peça. Um
pedido de cinco peças tem peças em etapas diferentes ao mesmo tempo — por
isso a etapa não cabe no pedido. O kanban do sprint 3 move **peças**.

O buraco de hoje. Sem tela de cadastrar pedido, o painel repete a mesma
mensagem para sempre.

**Entra:** cliente (nome, WhatsApp, canal, observações); pedido (cliente,
itens, quantidade, valor, prazo); orçamento é o pedido antes de aprovar.
**Todo registro grava quem o criou e quando** — hoje é sempre você, mas o
campo já nasce.

O pedido nasce **sem saber de onde veio**, e é isso que deixa a Shopee e o
Mercado Livre entrarem depois sem reescrever nada. Quatro campos que custam
nada agora e não têm como ser preenchidos no passado:

| Campo | Para quê |
| --- | --- |
| `canal` | Balcão, Instagram, WhatsApp, indicação, Morumbi Festas, loja, Shopee, Mercado Livre |
| `id_no_canal` | O número do pedido lá fora. É por ele que se confere o que caiu e o que faltou |
| `comissao` | O que o canal cobra. Fica em cadastro, porque as taxas mudam |
| `valor_liquido` | O que sobra de verdade. Sem ele, o relatório de vendas mente |

**Eu testo:** pedido novo entra na fila agrupado pela cor certa · prazo
vencido marca atrasado e o grupo sobe na fila · aprovar orçamento não
duplica o pedido · o mesmo `id_no_canal` não entra duas vezes.

**Você confere:** cadastre um pedido real vindo do Instagram; o painel tem
que sair do vazio e mostrar a peça na cor certa.

## Sprint 3 — Produção numa tela só ✅ FEITO
**Tamanho G · depende do 2**

**A decisão de fundo:** o estoque não é alterado direto. Cada mudança vira um
**movimento**, e o saldo é a soma deles — a coluna `gramas` do filamento é só
um cache, com teste provando que os dois batem. Três coisas vêm de graça:
voltar a peça uma etapa devolve o material sem precisar adivinhar quanto
saiu; o relatório de filamento gasto (sprint 7) sai da própria tabela; e dá
para *provar* que o saldo não desandou, em vez de torcer. Uma peça só tem
uma baixa de produção, e quem garante isso é um **índice único no banco** —
não a ordem em que as telas chamam.

A anotação do Samir vira código. Entra também o que nem eles nem nós
registramos hoje: a peça que deu errado.

**Entra:** quadro kanban com as cinco etapas, arrastando a peça · lista com
seleção múltipla na mesma tela · entrar em produção baixa filamento e
insumo · registrar refugo (gramas e motivo) · **histórico de quem moveu cada
peça, para qual etapa e quando**.

**Eu testo:** mover a peça baixa exatamente o peso dela · voltar uma etapa
devolve o estoque · refugo não baixa o mesmo filamento duas vezes · cada
movimento aparece no histórico com autor e hora.

**Você confere:** arraste uma peça para "em produção" e olhe o estoque
antes e depois; a diferença tem que ser o peso da peça mais a purga.

## Sprint 4 — Compras: o custo vira real ✅ FEITO
**Tamanho P · depende do 1**

Pequeno e vale muito. Enquanto o preço do filamento for digitado uma vez e
esquecido, o custo é ficção.

**A decisão de fundo:** o preço em uso passa a ter **dois donos possíveis**, e
por isso mora em duas colunas. O da **última compra** manda; o **digitado à
mão** é reserva, e só vale enquanto não houver nota daquele item. Com uma
coluna só, apagar uma compra deixava na tela o preço dela — número de um
registro que não existe mais, com cara de número conferido. A entrada de
estoque passa pelo mesmo livro de movimentos da sprint 3: compra não é uma
porta lateral para mexer no saldo.

**Entra:** compra (fornecedor, nota, data, vários itens) · entrada no estoque
e no último valor de compra · custo do produto passa a usar o preço pago de
verdade · a ficha do filamento mostra qual preço está valendo e de onde ele
veio.

**Eu testo:** compra nova muda o custo de todo produto que usa aquele
filamento · compra não some do histórico quando o preço muda · estoque
somado das compras bate com o saldo do painel · editar a compra não soma
duas vezes · apagar volta ao preço anterior, e depois ao digitado · salvar a
ficha do filamento não rouba o preço da compra · o preço que você digitou
sobrevive à atualização da VPS.

**Você confere:** lance a última compra de PLA preto com o valor da nota; o
custo do letreiro preto tem que mudar na hora.

## Sprint 5 — Financeiro
**Tamanho M · depende do 2 e do 4**

**Entra:** categorias de receita e despesa · contas a pagar com parcelamento
e recorrência · contas a receber geradas pela entrega · recebido, a receber,
pago, a pagar e a diferença no painel.

**Eu testo:** entregar um pedido gera exatamente uma conta a receber ·
parcelamento em 3× soma o total original, sem centavo perdido · conta
recorrente não duplica no mesmo mês.

**Você confere:** marque um pedido como entregue e veja a conta a receber
com o valor e o nome do cliente.

## Sprint 6 — Orçamento em PDF
**Tamanho P · depende do 2**

**Entra:** dados da empresa e cores do documento · PDF com marca, itens,
prazo e total · link para o cliente aprovar sem senha.

**Eu testo:** total do PDF bate com a soma dos itens, com desconto e sem ·
link de aprovação vale para um orçamento só e expira · orçamento aprovado
não pode ser editado depois.

**Você confere:** gere o PDF e mande no seu WhatsApp; tem que abrir no
celular com a marca e o valor certos.

## Sprint 7 — Relatórios
**Tamanho M · depende do 3 e do 5**

**Entra:** itens produzidos · vendas por canal de origem · financeiro
(entradas, saídas, saldo) · perda de material (ocorrências, gramas, peças
que mais refugam) · filamento gasto por cor. Todos com período e PDF.

**Eu testo:** a soma de cada relatório bate com a soma dos registros que o
alimentam · período de um dia não vaza o dia seguinte · PDF sai com os
mesmos números da tela.

**Você confere:** rode o de filamento gasto do mês e compare com o que sumiu
dos rolos; diferença grande é refugo não registrado ou peso errado.

## Sprint 8 — Loja própria
**Tamanho G · depende do 2, 5 e 6**

O único item que traz cliente novo em vez de organizar o que já existe. Por
isso é o último dos que dependem só de nós: precisa que todo o resto
funcione, senão a venda cai num sistema que não sabe o que fazer com ela.

```
Vitrine → Pedido ou orçamento → Pagamento → Aguardando produção → Conta a receber
```

**Entra:** vitrine pública com foto, prazo e **preço à vista para peça de
catálogo** · peça personalizada entra como **sob consulta**, virando orçamento
no sprint 6 · **Mercado Pago** por checkout hospedado, com PIX · **entrega e
retirada**, com frete cotado no **Melhor Envio** usando peso e caixa que o
sprint 1 já calculou · pagou, entra em aguardando produção e gera a conta a
receber.

**Eu testo:** **aviso de pagamento repetido não cria dois pedidos** — o
Mercado Pago reenvia o aviso quando não tem resposta, e essa é a falha
clássica que faz o cliente ser cobrado uma vez e o pedido nascer duas ·
pedido só entra na produção depois do pagamento confirmado · frete cotado
bate com o peso real da caixa, e não com o da peça nua · retirada não cobra
frete · preço da vitrine é o mesmo que o sistema calcula.

**Você confere:** compre de você mesmo, PIX de R$ 1 num produto de teste,
uma vez com entrega e uma vez com retirada. O pedido aparece em aguardando
produção e a conta em contas a receber, cada um uma vez só.

## Sprint 9 — Shopee e Mercado Livre
**Tamanho G · depende do 8 · o único que depende de terceiros**

O pedido do marketplace entra pela **mesma porta** que a loja usa no sprint
8 — é por isso que os quatro campos do sprint 2 existem desde o começo. O que
muda é quem bate na porta.

**Entra:** conexão com Shopee e Mercado Livre · pedido de lá vira pedido
aqui, com o número de lá guardado · estoque de peça pronta sincronizado nos
dois sentidos, para não vender o que não existe · comissão de cada
marketplace no cadastro, alimentando o valor líquido.

**Eu testo:** o mesmo pedido chegando duas vezes vira um pedido só · vender
no balcão baixa o anúncio nos dois marketplaces · marketplace fora do ar não
derruba a loja nem o painel · valor líquido bate com o extrato deles, não com
o preço anunciado.

**Você confere:** faça uma venda de teste na Shopee. Ela tem que aparecer no
painel com o número do pedido de lá, e o valor líquido tem que bater com o
que a Shopee diz que vai te pagar.

**O que pode travar:** este é o único sprint que depende de coisa fora do
nosso alcance. Os dois exigem conta de desenvolvedor aprovada, e as regras e
taxas deles mudam sem avisar. Antes de começar, você vai precisar criar as
duas contas e me passar as credenciais.

---

# Trilha de Criação — a plataforma de geradores

## A descoberta que barateia tudo

Antes de planejar, fui olhar o que já existe. O núcleo do gerador de
letreiros exporta isto:

```js
const M = { Gerador, alturaAuto, stlBinario, caixa, analisar,
            grupos, MESA, SIZE, PRODUTOS };
```

Ali já estão geometria, exportação de STL, caixa envolvente, **análise de
malha rodando no navegador**, agrupamento por cor e as constantes da mesa.
A plataforma não precisa ser inventada: ela existe pela metade, presa dentro
de um arquivo de 8 mil linhas que só sabe fazer letreiro.

Então C1 não é *construir* uma plataforma. É **soltar a que já está lá**.

## O corte: plataforma × peça

Todo gerador — letreiro, logo, topo de bolo, chaveiro, vaso, cortador — faz
a mesma sequência. Só um passo dela é diferente em cada um.

| Passo | De quem é |
| --- | --- |
| Formulário de parâmetros | Plataforma |
| Texto vira geometria | Plataforma (o gerador de letreiro já faz) |
| **Desenhar a peça** | **Da peça — é a única parte que muda** |
| Validar a malha: fechada, espessura mínima, cabe na mesa | Plataforma |
| Prévia 3D | Plataforma |
| Estimar gramas, horas, custo e preço | Plataforma |
| Nome de arquivo padronizado | Plataforma |
| Guardar a configuração | Plataforma |

Sete oitavos são escritos uma vez. Um gerador novo passa a ser **um módulo
de geometria mais um punhado de templates** — e herda de graça a validação
que já pegou junta em T, malha aberta e erro de preço de 9×.

## O que eu acrescento ao seu documento

Seu documento de topo de bolo está completo — mais do que a maioria das
especificações que recebo prontas. Duas coisas eu acrescento, e uma delas
mexe numa decisão sua.

**1. O filtro de marca vale para o texto do cliente, não só para o template.**
Seu §18 trata da origem de cada template, e está certo. Mas a exposição maior
é a outra ponta: o cliente digita "Homem Aranha" no campo de nome de um topo
que **você** vende. O `brands.py` da curadoria já detecta termos de marca,
time, personagem e franquia, com lista que você amplia sem mexer em código.
Ligar os dois é quase de graça, e é a diferença entre uma regra escrita e uma
regra que funciona sozinha às onze da noite de sábado.

**2. Peça de template pode ter preço na hora — e não "sob consulta".**
Você decidiu que personalizado é sob consulta. Para trabalho realmente sob
medida, continua certo. Mas topo de bolo de template **não é** sob medida: o
gerador desenha a peça, o analisador pesa, e o preço sai na hora, pelo mesmo
cálculo do balcão. Deixar "sob consulta" numa peça que o sistema sabe
precificar é perder venda por conversa que não precisava existir. Minha
sugestão: **template tem preço; sob consulta fica para o que não tem
template** — um logo novo, um projeto de fato único.

## Sprint C0 — A tela Criar ✅ FEITO
**Tamanho P · sem dependência**

O menu tinha dois links soltos: "Gerar letreiro" e "Gerar logo". Dois cabem.
Doze não — e o C4 tem uma dezena pela frente. Pior: o link escondia que
**dentro do gerador de letreiros moram seis modelos diferentes**. Quem abria
achava que tinha uma opção; tinha seis.

**A decisão de fundo:** o catálogo não lista *geradores*, lista o que dá para
**fazer**. Cada modelo é uma linha em `sistema/criar.py`, e a tela e os
filtros saem dela — acrescentar um modelo é acrescentar uma linha, sem mexer
em template. Duas regras seguram a honestidade: modelo sem rota aparece como
*em construção* e **não ganha botão**, e todo modelo marcado *no ar* tem
teste que abre a rota dele.

O filtro por **cores** é o que faz esta tela ser sua e não genérica: ele
pergunta *o que dá para fazer sem trocar filamento* — cada troca custa 6 g de
purga mais o tempo de parar a máquina. Hoje a resposta é dois modelos de oito.

**Entra:** tela `/criar` com um cartão por modelo · busca por tema ("princesa",
"halloween", "empresa") e não só por nome · filtros de categoria, cores e
situação · o cartão abre o gerador **no modelo escolhido** · volta do gerador
para o catálogo · o menu passa a ter um item "Criar" no lugar dos dois.

**Eu testo:** cartão que promete um modelo que o gerador não conhece é
barrado · modelo que existe no gerador e não está no catálogo é barrado (venda
parada) · toda rota marcada *no ar* responde · modelo em construção não ganha
botão · **e no navegador de verdade: filtrar esconde mesmo o que sobrou de
fora**.

**Você confere:** clique em "1 cor" e veja sobrar só o Clássico e o Logo.
Depois clique no cartão do Terror: o gerador tem que abrir já no Terror.

## Sprint C1 — Soltar o núcleo ✅ FEITO
**Tamanho M · sem dependência · pode andar em paralelo com a trilha de gestão**

**A decisão de fundo:** o corte não foi em dois, foi em **três**, e é a tabela
"plataforma × peça" virada arquivo:

| Arquivo | O que é | Serve para |
| --- | --- | --- |
| `nucleo.js` | polígono, sólido, STL, a mesa | qualquer gerador, de qualquer casa |
| `oficina.js` | os números **desta** casa | qualquer gerador da Morumbi 3D |
| `letreiro.js` | o desenho do letreiro | só ele |

A oficina é a peça que faltava no plano original. A estimativa de gramas, o
que cabe na mesa, a purga de 6 g, o preço de balcão e o nome do arquivo
estavam **dentro da tela** do letreiro — não no núcleo. Se o topo de bolo
fosse escrito com o plano como estava, ele reescreveria todos esses números,
e no dia em que um fosse corrigido a casa passaria a ter dois preços.

**A prova:** `docs/impressao-digital.txt` — um sha256 por peça de uma matriz
de vinte casos, conferido a cada rodada da suíte. Um teste que só olha "malha
fechada" passa feliz com a peça virada do avesso; um hash não. Inverti a
normal de um triângulo de propósito para ver o teste ficar vermelho.

**Entra:** o núcleo vira três módulos de verdade, fora do HTML · carregam em
navegador e em node · **validação de malha obrigatória antes de qualquer
download** · estimativa, preço e nome de arquivo passam a ser da plataforma ·
parâmetros do letreiro declarados como dado · configuração salva, para
reimprimir sem procurar arquivo antigo.

**O que eu testei:** os STL saem **byte a byte idênticos** depois da extração ·
malha reprovada não gera download, nunca · o preço da tela e o do servidor dão
o mesmo número · o núcleo não sabe o que é um letreiro (e há teste que
reprova se alguém escrever `'magia'` lá dentro) · configuração inválida
guardada não passa por cima do que a tela mostra.

**Você confere:** gere um letreiro que já gerou antes — sai igual. Escolha
Cinema em 28 cm, feche a aba e volte: está como você deixou. Clique no cartão
do Terror no Criar: ganha do que estava guardado, porque foi o que você pediu
agora.

**Duas coisas do plano original que NÃO entraram, e por quê:**

**Prévia 3D de verdade** (girar a peça na tela) — a prévia de hoje é um
desenho da peça em pé, que responde a mesma pergunta na maior parte dos casos.
Um visualizador WebGL é um sprint inteiro sozinho, e entra melhor depois do
topo de bolo, quando houver duas peças para girar.

**O renderizador de formulário** — os parâmetros do letreiro estão declarados
como dado (`PARAMETROS`, com teste comparando com os controles da tela), mas
nada os renderiza ainda. Formulário genérico escrito contra **um** formulário
acerta por acaso. O C2 traz o segundo: aí ele se escreve contra duas
exigências reais em vez de uma imaginada.

## Sprint C2 — Gerador de topo de bolo ✅ FEITO (o código)
**Tamanho G · depende do C1 · o gargalo não é código**

**O que ficou pronto:** a tela `/topo/`, mobile-first, com o fluxo do seu §3;
seis templates paramétricos; a nomenclatura do §11; o alerta de marca do §18
ligado ao `brands.py` da curadoria; e a validação do §10 — nome longo barrado
**antes** de gerar, traço fino detectado, e malha reprovada sem botão.

**A prova:** 192 peças — 6 templates × 8 nomes × 4 tamanhos — geradas num
navegador de verdade e passadas pelo analisador de malha do pacote. Todas
fechadas, manifold, em uma peça só, cabendo na mesa. **Nota 100 em todas.**

**O que o C1 provou valer:** o topo de bolo não reescreveu uma linha de
geometria, de estimativa, de preço ou de nome de arquivo. Ele declarou o
desenho e herdou o resto. Duas coisas subiram da peça para a plataforma no
caminho, porque o segundo gerador mostrou que eram de todos: a **máquina de
texto** (letra vira geometria, com a garantia de que as letras se tocam) e a
**regra de conexão** (`conexaoFragil`: duas partes que só se encostam não
estão ligadas).

**Os três bugs que só a impressora acusaria:**

1. **O coração saía no sentido horário.** Com preenchimento NonZero, o Clipper
   trata caminho horário como *furo* — unir o coração ao nome estava
   **subtraindo** ele. Na tela o desenho parecia certo (canvas ignora sentido
   de polígono) e doze arquivos foram para o disco com aresta não-manifold.
2. **O empilhamento parava no ponto exato do toque.** Duas linhas que *começam*
   a se tocar são um corpo só para o Clipper e uma aresta não-manifold depois
   de extrudar. Agora entram 1,5 mm além do toque.
3. **Dois pedidos diferentes viravam o mesmo arquivo.** O nome usava a largura
   medida; 180 mm e 175 mm arredondavam ambos para 17CM e um sobrescrevia o
   outro na pasta de downloads.

**O que falta, e é seu:** o §6 — **imprimir**. Os seis templates nascem
marcados *em teste* e nenhum vai para venda antes de sair da mesa e passar na
mão. O código está pronto antes dos templates, exatamente como este plano
previu.

O MVP do seu documento: 10 templates, nome, idade, tamanho, prévia, preço,
pedido.

**Entra:** os campos do seu §5 · presets de 12, 15, 18 e 20 cm · fontes
testadas · limites de caracteres e área segura por template · haste e base
padronizadas · saída em 3MF, com STL quando o modelo não exigir mais
informação · nomenclatura `M3D-TB-001_MARIA_5_18CM.3mf`.

**Eu testo:** nome longo demais é barrado antes de gerar, e não depois ·
espessura mínima e conexões respeitadas em toda combinação · a peça cabe na
mesa em todos os presets · malha fechada em todos os 10 templates, com todos
os nomes de teste · termo de marca no nome do cliente levanta alerta.

**Você confere:** o seu §16, que é o critério certo — **imprimir os 10**.
Abre no Bambu Studio, fatia sem erro, o texto continua legível depois de
impresso, e a peça aguenta ser manuseada.

**O gargalo é a impressora, não o código.** Dez templates, com as revisões
que sempre aparecem depois da primeira impressão, são semanas de mesa
ocupada. O código vai ficar pronto antes dos templates — e é o seu §6 que
manda: *todo template deve ser testado fisicamente antes de venda*.

## Sprint C3 — Catálogo de templates no painel ✅ FEITO
**Tamanho M · depende do C2**

Seu §12. Sem esta tela, cada template novo depende de mim mexer no código.

**A mudança de fundo:** os seis templates saíram de dentro de `topo.js` e
viraram **linhas de banco**, editadas pela tela `/templates`. O gerador não
carrega mais uma lista escrita em código — ele pergunta ao servidor. Há teste
que reprova se um SKU voltar a aparecer dentro do JavaScript.

**A linha entre painel e vitrine é a ROTA, não a tela.** `/topo/templates` sem
sessão entrega só o publicado; com sessão, entrega tudo, marcado *em teste* —
porque para publicar é preciso imprimir, e para imprimir é preciso gerar. A
vitrine da sprint 8 já nasce obedecendo essa porta.

**Entra:** cadastrar e editar template (SKU, modelo, categoria, campos, fonte,
decoração, arco, limites, licença) · ativar e desativar · **separar em teste
dos publicados**, como pede seu §10 · preço por template · registro de cada
geração.

**O que eu testei:** template em teste não aparece na loja, em nenhuma rota ·
desativar não quebra registro antigo · apagar o template **não apaga as
gerações** dele · renomear o SKU leva as gerações junto · licença em branco
impede publicar, no cadastro e no botão · SKU fora do padrão, repetido, ou com
forma que o gerador não conhece são recusados.

**Dois bugs que os testes acharam antes do uso:**

1. **Apagar um template semeado o trazia de volta.** A semente se reaplicava
   por SKU a cada conexão do banco: você apagava, ele voltava, e não havia
   nada na tela explicando. Agora a semente entra **uma vez na vida do banco**
   — template novo depois do C3 se cadastra pela tela, que é o ponto do sprint.
2. **A tela de erro do formulário quebrava** ao redesenhar com os dados crus
   do POST — mesmo defeito do sprint 1, e mesmo remédio: redesenhar com os
   campos já tipados.

**Sobre "baixar os arquivos" do seu §12:** guardo a **configuração** de cada
geração, e não o STL. O gerador refaz o arquivo idêntico a partir dela, e um
STL por geração encheria o disco da VPS em um mês de festa.

**Você confere:** cadastre um template do zero, deixe em teste, confirme que
ele não aparece na vitrine, publique e confirme que aparece.

## Sprint C4 — Os geradores seguintes ✅ FEITO (o primeiro deles)
**Tamanho variável · depende do C1**

**A escolha, primeiro.** Sua regra é *"não invente nada que não tenha demanda
de clientes comprovada"*. Dos dez do plano original, o **chaveiro** é o único
com demanda dentro do próprio sistema: está nos pedidos de exemplo
("Chaveiro personalizado ×6"), é o exemplo de custo dos testes (9 g, 0,4 h),
aparece na produção, e é o caso que o módulo de licenças já tratava
("Chaveiro do Corinthians"). Os outros nove esperam cliente pedindo.

**O que ele prova.** No C1 eu declarei os parâmetros como dado e **não**
escrevi o renderizador de formulário, dizendo: *"formulário genérico escrito
contra UM formulário acerta por acaso; o C2 traz o segundo"*. Agora são dois,
e com exigências que brigam entre si:

| | tamanho | campos | onde quebra |
| --- | --- | --- | --- |
| Topo de bolo | 12–20 cm | nome + idade | na **conexão** das letras |
| Chaveiro | 3–7 cm | só o nome | na **parede** do furo |

Uma tela serve as duas. O que difere ficou em `pecas.js`; o resto — tela,
rotas, catálogo, vistoria, estimativa, preço, registro de geração — é da
plataforma. **Acrescentar a terceira peça é um módulo de geometria mais uma
entrada no registro.**

**A prova:** as duas peças passam pela mesma matriz de conferência, e todo STL
gerado sai fechado, manifold e em uma peça só.

**Um bug que eu mesmo criei no C3 e que o C4 expôs:** a semente entrava "uma
vez na vida do banco". Isso consertava a ressurreição de template apagado —
mas fechava a porta: os chaveiros nunca chegariam à sua VPS, que é um banco
que já existe. Agora cada entrada diz **de qual sprint veio**, e só as
anteriores são dadas por vistas. Template novo chega; o que você apagou fica
apagado.

**E a armadilha do `[hidden]` de novo:** o chaveiro pede só o nome, e a tela
mostrava "Idade ou número" assim mesmo — `display` de classe ganha da regra do
navegador. Terceira vez neste projeto; agora está no CLAUDE.md e tem teste.

**Você confere:** abra **Criar → Chaveiro de nome**, escreva um nome curto em
5 cm e gere. Depois tente "GUILHERME" em 3 cm: o sistema tem que recusar, e
dizer que 9 letras em 35 mm é apertado — não uma desculpa genérica.

**Os nove restantes:** placa, display, lembrancinha, caixa, organizador, vaso,
cortador, lithophane, mapa. Cada um é hoje um módulo de geometria mais uma
entrada no registro. Me diga qual cliente pediu, e ele entra.

## Quatro decisões já tomadas

- **O cartão nunca passa pelo servidor.** A loja manda o cliente para o
  checkout do meio de pagamento e recebe o aviso de volta. Guardar cartão
  exige certificação que não faz sentido aqui, e vazamento numa VPS de 2 GB
  não se resolve depois.
- **A precificação continua sendo a nossa.** A deles multiplica hora por
  valor e soma margem. A nossa já calcula casca, preenchimento, suporte e
  purga por troca de cor, com piso de R$ 18 + R$ 0,60/g arredondado a R$ 5.
- **Modelo de dados geral agora; código de integração só quando existir.**
  Mesma lógica da decisão anterior, aplicada aos marketplaces. Os campos do
  pedido (canal, número lá fora, comissão, valor líquido) entram no sprint 2,
  porque um pedido antigo sem eles nunca mais terá de onde tirá-los. Já o
  código que fala com a Shopee fica para o sprint 9 — escrever hoje um
  encaixe genérico para uma API que ainda não li é adivinhar, e adivinhação
  em código custa mais caro do que quatro colunas.
- **Quem fez fica gravado desde já; quem pode fazer o quê fica para depois.**
  O Samir administra sozinho hoje, e haverá colaboradores em atendimento e
  outros departamentos mais adiante. As duas metades disso têm custos muito
  diferentes: *quem fez* é irreversível — sem o campo desde a primeira linha,
  o histórico nunca saberá quem cadastrou o pedido ou moveu a peça, e não há
  como preencher depois. *Quem pode fazer o quê* é barato a qualquer momento:
  papéis e permissões entram sem tocar no que já existe. Então todo registro
  grava autor e data agora, a autenticação continua a mesma (uma senha, no
  serviço), e a tela de equipe só entra quando existir a segunda pessoa.

## Respostas que fecharam o plano

| Pergunta | Resposta | Onde entra |
| --- | --- | --- |
| Quem opera | Samir hoje; colaboradores em atendimento e outros departamentos depois | Autor em todo registro: sprints 2 e 3 |
| Pagamento | Mercado Pago | Sprint 8 |
| Preço na vitrine | Catálogo com preço; personalizado sob consulta | Sprints 6 e 8 |
| Entrega | Entrega via Melhor Envio, e retirada | Sprints 1 e 8 |
| Marketplace | Preparar para Shopee e Mercado Livre | Campos no sprint 2; integração no 9 |
| Geradores | Plataforma de personalização, começando por topo de bolo | Trilha de Criação, C1 a C4 |
