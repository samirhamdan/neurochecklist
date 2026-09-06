# Plano de construção — do gerador de peça ao controle da oficina

Oito sprints numerados **por dependência**, não por preferência: cada um só
pode existir depois do anterior. Cada um entrega algo usável no mesmo dia,
e traz o que eu testo e o que você confere.

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

## Sprint 1 — Cadastros e custo da peça
**Tamanho M · sem dependência**

Sem produto não existe pedido; sem filamento o produto não tem custo.

**Entra:** filamento (marca, tipo, cor, estoque g, mínimo); insumo (unidade,
estoque, mínimo, valor); produto (peso, tempo, filamento padrão, insumos,
fotos, arquivos STL/3MF). **Soltar o STL preenche peso e tempo** pelo
analisador de malha.

**Eu testo:** peso lido do STL bate com o do analisador, peça a peça ·
produto sem filamento não salva com custo zero fingido · estoque abaixo do
mínimo aparece no painel.

**Você confere:** cadastre o letreiro ANA de 22 cm soltando o STL que o
gerador já produz; peso e custo têm que aparecer sozinhos e bater com a
balança depois de imprimir.

## Sprint 2 — Clientes e pedidos
**Tamanho M · depende do 1**

O buraco de hoje. Sem tela de cadastrar pedido, o painel repete a mesma
mensagem para sempre.

**Entra:** cliente (nome, WhatsApp, canal, observações); pedido (cliente,
itens, quantidade, valor, prazo); canal por pedido, herdado do cliente e
editável; orçamento é o pedido antes de aprovar. **Todo registro grava quem
o criou e quando** — hoje é sempre você, mas o campo já nasce.

**Eu testo:** pedido novo entra na fila agrupado pela cor certa · prazo
vencido marca atrasado e o grupo sobe na fila · aprovar orçamento não
duplica o pedido.

**Você confere:** cadastre um pedido real vindo do Instagram; o painel tem
que sair do vazio e mostrar a peça na cor certa.

## Sprint 3 — Produção numa tela só
**Tamanho G · depende do 2**

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

## Sprint 8 — Loja online
**Tamanho G · depende do 2, 5 e 6**

O único item que traz cliente novo em vez de organizar o que já existe. Por
isso é o último: precisa que todo o resto funcione, senão a venda cai num
sistema que não sabe o que fazer com ela.

```
Vitrine → Pedido ou orçamento → Pagamento → Aguardando produção → Conta a receber
```

**Entra:** vitrine pública (produto, foto, preço, prazo) · personalização
usando os geradores que já existem · pagamento por checkout hospedado, com
PIX · pagou, entra em aguardando produção e gera a conta a receber.

**Eu testo:** **aviso de pagamento repetido não cria dois pedidos** — o meio
de pagamento reenvia o aviso quando não tem resposta, e essa é a falha
clássica · pedido só entra na produção depois do pagamento confirmado ·
preço da vitrine é o mesmo que o sistema calcula.

**Você confere:** compre de você mesmo, PIX de R$ 1 num produto de teste; o
pedido aparece em aguardando produção e a conta em contas a receber, cada um
uma vez só.

---

## Três decisões já tomadas

- **O cartão nunca passa pelo servidor.** A loja manda o cliente para o
  checkout do meio de pagamento e recebe o aviso de volta. Guardar cartão
  exige certificação que não faz sentido aqui, e vazamento numa VPS de 2 GB
  não se resolve depois.
- **A precificação continua sendo a nossa.** A deles multiplica hora por
  valor e soma margem. A nossa já calcula casca, preenchimento, suporte e
  purga por troca de cor, com piso de R$ 18 + R$ 0,60/g arredondado a R$ 5.
- **Quem fez fica gravado desde já; quem pode fazer o quê fica para depois.**
  O Samir administra sozinho hoje, e haverá colaboradores em atendimento e
  outros departamentos mais adiante. As duas metades disso têm custos muito
  diferentes: *quem fez* é irreversível — sem o campo desde a primeira linha,
  o histórico nunca saberá quem cadastrou o pedido ou moveu a peça, e não há
  como preencher depois. *Quem pode fazer o quê* é barato a qualquer momento:
  papéis e permissões entram sem tocar no que já existe. Então todo registro
  grava autor e data agora, a autenticação continua a mesma (uma senha, no
  serviço), e a tela de equipe só entra quando existir a segunda pessoa.

## Perguntas em aberto

1. **Qual meio de pagamento na loja?** Mercado Pago é o caminho mais curto
   no Brasil (PIX, cartão, boleto, checkout hospedado).
2. **A loja mostra preço para todo mundo?** Catálogo tem preço; peça sob
   medida pode ser preço na hora, se o gerador calcular, ou orçamento.
3. **Entrega ou retirada?** Com entrega, o pedido precisa de endereço e
   frete — muda o sprint 8.
