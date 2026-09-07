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

## Sprint 4 — Compras: o custo vira real
**Tamanho P · depende do 1**

Pequeno e vale muito. Enquanto o preço do filamento for digitado uma vez e
esquecido, o custo é ficção.

**Entra:** compra (fornecedor, item, quantidade, valor pago, data) · entrada
no estoque e no último valor de compra · custo do produto passa a usar o
preço pago de verdade.

**Eu testo:** compra nova muda o custo de todo produto que usa aquele
filamento · compra não some do histórico quando o preço muda · estoque
somado das compras bate com o saldo do painel.

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

## Sprint C1 — Soltar o núcleo
**Tamanho M · sem dependência · pode andar em paralelo com a trilha de gestão**

**Entra:** o núcleo vira módulo de verdade, fora do HTML do letreiro ·
formulário de parâmetros declarado por gerador · validação de malha
obrigatória antes de qualquer download · prévia 3D · estimativa de gramas,
horas e preço · nome de arquivo padronizado · configuração salva, para
reimprimir sem procurar arquivo antigo.

**Eu testo:** **os três geradores de hoje continuam produzindo o mesmo STL,
byte a byte, depois da extração** — é assim que se prova que uma extração não
quebrou nada · malha reprovada não gera download, nunca · a mesma
configuração gera o mesmo arquivo duas vezes.

**Você confere:** gere um letreiro que você já gerou antes e compare o
arquivo com o antigo. Tem que ser idêntico.

## Sprint C2 — Gerador de topo de bolo
**Tamanho G · depende do C1 · o gargalo não é código**

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

## Sprint C3 — Catálogo de templates no painel
**Tamanho M · depende do C2**

Seu §12. Sem esta tela, cada template novo depende de mim mexer no código.

**Entra:** cadastrar e editar template (SKU, modelo, categoria, campos,
tamanhos, fontes, cores, licença) · ativar e desativar · **separar em teste
dos publicados**, como pede seu §10 · preço por template · acompanhar
gerações e baixar os arquivos.

**Eu testo:** template em teste não aparece na loja, em nenhuma rota ·
desativar template não quebra pedido antigo que o usou · licença em branco
impede publicar.

**Você confere:** cadastre um template do zero, deixe em teste, confirme que
ele não aparece na vitrine, publique e confirme que aparece.

## Sprint C4 — Os geradores seguintes
**Tamanho variável · depende do C1**

Chaveiro, placa, display, lembrancinha, caixa, organizador, vaso, cortador,
lithophane, mapa. Cada um é **um módulo de geometria mais templates** — a
plataforma não muda.

A ordem não decido eu: sai pela demanda que você vê no balcão e pelo que a
Morumbi Festas puxa junto. O seu §20 já aponta o caminho — a família coerente
de produtos para a mesma ocasião.

**Regra que vale para todos:** nenhum gerador vai à loja sem passar pelo seu
§6 e §16. Malha validada pela plataforma e template impresso e aprovado por
você.

---

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
