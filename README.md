# Morumbi 3D — Ferramentas de Catálogo e Produção

Duas ferramentas de linha de comando que dividem a mesma base técnica
(analisador de malha, custo, mesa da impressora):

| Ferramenta | O que faz |
| --- | --- |
| `morumbi3d buscar` e cia. | **Curadoria**: encontra, avalia e organiza modelos 3D prontos de repositórios públicos |
| `morumbi3d letra` | **Produção**: converte SVG em letra caixa pronta para imprimir |
| [`web/gerador-letreiros.html`](web/) | **Produção**: placa de nome com letras conectadas, direto no navegador |
| [`sistema/`](sistema/) | **Gestão**: entrada e painel — fila de produção, pedidos e estoque |
| [`sistema/logo/`](sistema/logo/) | **Produção**: gerador de logo 3D (imagem → STL), agora dentro do sistema |

A primeira implementa a especificação *Sistema de Busca e Curadoria de
Modelos 3D*, na ordem recomendada por ela: banco de dados + analisador de
malha → conectores de fonte → filtro de licença → relatório de curadoria.
As outras duas cobrem o outro lado do catálogo — o produto feito sob medida —
e partem de entradas diferentes: o `letra` de um SVG (arte pronta), o gerador
de letreiros de um nome digitado. O analisador de malha da curadoria confere
a saída dos três.

**Roda só com Python 3.11+ e a biblioteca padrão.** Nenhuma dependência
obrigatória — inclusive o analisador de malha, que lê STL/3MF/OBJ por conta
própria.

---

## Instalação

```bash
cd morumbi3d
pip install -e .            # instala o comando `morumbi3d`
morumbi3d init              # cria ~/.morumbi3d e o morumbi3d.toml
```

Sem instalar nada, também funciona: `python3 -m morumbi3d <comando>`.

Depois do `init`:

```bash
export MORUMBI3D_CONTATO="seu-email@exemplo.com"   # identifica o sistema nas requisições
export THINGIVERSE_TOKEN="..."                     # opcional, libera o Thingiverse
export GITHUB_TOKEN="..."                          # opcional, aumenta o limite do GitHub
morumbi3d fontes                                   # confere o que está ligado
```

## O fluxo de trabalho

```bash
# 1. buscar (traduz PT→EN automaticamente e consulta todas as fontes ligadas)
morumbi3d buscar "churrasqueira" --so-comercial --imagens

# 2. olhar o que entrou no catálogo
morumbi3d catalogo --linha Adultos --status novo
morumbi3d ver 12

# 3. baixar o arquivo do modelo e medir se imprime bem
morumbi3d analisar --modelo 12 --arquivo ~/Downloads/modelo.stl

# 4. decidir
morumbi3d aprovar 12 --motivo "testar em preto fosco"
morumbi3d reprovar 15 --motivo "malha aberta, muito suporte"

# 5. relatório visual e exportação para a planilha
morumbi3d relatorio --so-seguros
morumbi3d exportar --status aprovado --saida projeto30.csv
```

`morumbi3d stats` mostra o funil inteiro (novo → aprovado → produção).

---

## O que cada parte faz

### Busca multi-fonte com tradução (§3.1)

`buscar` expande o termo antes de consultar: `churrasco` vira também
`barbecue`, `bbq`, `grill`, `grilling` — porque os modelos bons estão
catalogados em inglês. O dicionário do nicho está em
[`morumbi3d/translate.py`](morumbi3d/translate.py) e você amplia sem mexer no
código criando `~/.morumbi3d/dicionario.txt`:

```
cuia = mate gourd, yerba mate cup
```

Filtros: `--so-comercial`, `--so-gratuitos`, `--com-imagem`,
`--formato stl|3mf`, `--fontes thingiverse github`.

### Filtro de licença — o filtro que protege o negócio (§3.2)

Duas verificações independentes, porque elas respondem perguntas diferentes:

| Verificação | Pergunta |
| --- | --- |
| **Licença** | o autor deixa vender a peça impressa? |
| **Marca/personagem** | o *design* é propriedade de outra pessoa? |

O segundo é o caso do escudo de time: um STL pode estar em **CC0** e mesmo
assim o escudo não ser seu para vender. Por isso, título, descrição e tags
passam por uma lista de termos sensíveis (times, personagens, franquias,
marcas) e um acerto **bloqueia o modelo mesmo com licença livre**.

Cada licença vira quatro respostas objetivas: pode vender · exige crédito ·
share-alike · pode modificar. **Na dúvida, `desconhecido`** — nunca
"permitido". `aprovar` recusa modelo bloqueado; para liberar é preciso
`--mesmo-assim` e registrar o porquê em `--motivo`, que fica gravado no banco.

Seus próprios termos sensíveis (clientes, marcas locais) vão em
`~/.morumbi3d/termos_sensiveis.txt`:

```
cliente: Padaria do Ze
franquia: Personagem da novela
```

### Avaliação de imprimibilidade (§3.3)

`analisar` lê o arquivo e responde, sem abrir o fatiador:

- **malha fechada?** — arestas sem par e arestas não-manifold, contadas de verdade;
- **quantas partes soltas** — união de triângulos por aresta compartilhada;
- **cabe na mesa?** — e, se não couber reto, testa girar em torno de Z ângulo a
  ângulo antes de sugerir redução de escala;
- **quanto suporte** — área voltada para baixo além do ângulo do slicer,
  já descontando o que se apoia na mesa;
- **material e tempo** — casca + preenchimento + suporte, na densidade e vazão
  configuradas;
- **nota de 0 a 100**, para ordenar a fila de teste.

Se você tiver `trimesh` instalado (`pip install -e ".[malha]"`), o resultado
traz também uma conferência independente — mas nada depende disso.

### Banco de dados local (§3.4)

SQLite em `~/.morumbi3d/catalogo.sqlite3`. Guarda fonte, link, autor, licença,
análise, orçamento e status de curadoria (`novo` / `aprovado` / `reprovado` /
`producao`).

**Duplicatas entre fontes** são reconhecidas por uma assinatura de
título+autor que ignora pontuação, acento, ordem das palavras e ruído tipo
"STL"/"v2"/"remix": o mesmo porta-tempero achado no Thingiverse e no
Printables vira um item só na listagem.

### Organização por linha de produto (§3.5)

Cada modelo é etiquetado automaticamente por linha e coleção espelhando o Guia
de Produtos Próprios — Infantil, Adultos/Futebol, Adultos/Churrasco,
Social/Casamento, Casa e Decoração, Corporativo. A taxonomia está em
[`morumbi3d/lines.py`](morumbi3d/lines.py).

### Relatório de curadoria (§3.6)

`relatorio` gera um HTML offline (CSS e JS embutidos, imagens copiadas do
cache) com miniatura, licença, imprimibilidade e custo lado a lado, filtros
por linha/status/segurança e busca por texto. A borda do cartão é o semáforo:
verde = pode vender, âmbar = licença a conferir, vermelho = risco de marca.

`exportar` gera o CSV (`;`, UTF-8 com BOM — abre direto no Excel brasileiro)
no formato do Projeto 30 Produtos.

---

## Fontes

Cada repositório é um módulo em [`morumbi3d/sources/`](morumbi3d/sources/).
Uma fonte que cai vira uma linha de erro na busca — **nunca derruba as
outras**.

| Fonte | Acesso | Estado inicial |
| --- | --- | --- |
| Thingiverse | API oficial (exige `THINGIVERSE_TOKEN`) | ligada |
| GitHub | API oficial pública | ligada |
| Printables | endpoint interno, não documentado | **desligada** |
| MakerWorld (Bambu) | endpoint interno, não documentado | **desligada** |
| Thangs | API parcial | **desligada** |
| Cults3D | sem busca pública em JSON | **desligada** |

As quatro últimas ficam desligadas de propósito: são endpoints que o site usa
para o próprio front-end, não uma API que alguém prometeu manter. Ligar é uma
decisão sua, em `morumbi3d.toml`, depois de ler os termos de uso do site — e
elas podem parar de funcionar quando o site mudar. Quando isso acontece, o
conector devolve um erro dizendo o que quebrou, em vez de resultado errado.

## Conduta com as fontes (§6)

Tudo o que sai para a internet passa por
[`morumbi3d/net.py`](morumbi3d/net.py), que aplica sempre:

- **User-Agent** identificando o sistema e o seu contato;
- **robots.txt** conferido antes de cada URL e respeitado (`AcessoNegado` se
  não permitir);
- **intervalo mínimo** entre requisições ao mesmo host, respeitando
  `Crawl-delay`;
- **cache em disco** — cada URL e cada arquivo baixados uma única vez;
- **recuo exponencial** em 429/5xx, respeitando `Retry-After`, e limite de
  tamanho de download.

Não há nada aqui para contornar bloqueio, captcha ou limite de taxa. Se a
fonte disser não, o conector devolve o motivo e a busca segue nas outras.

---

## Um serviço só: `wsgi.py`

O gerador de logo (`morumbi3d_web`) morava num serviço próprio. Agora mora em
[`sistema/logo/`](sistema/logo/) e sobe junto com o painel, num processo só:

```bash
pip install -r requirements.txt
MORUMBI_USUARIO=samir MORUMBI_SENHA=troque \
  gunicorn -c gunicorn.conf.py wsgi:app
```

| Endereço | O quê |
| --- | --- |
| `/` | painel — fila, pedidos, estoque |
| `/entrar` | tela de entrada (a única sem cadeado, junto com `/saude`) |
| `/letreiros` | gerador de placa de nome (roda no navegador) |
| `/logo/` | gerador de logo 3D (roda no servidor) |

A razão é a máquina: o VPS tem 2 GB, e cada processo gunicorn carrega numpy,
scipy, opencv e trimesh por conta própria — 300 a 400 MB cada um. Dois
serviços separados **não cabiam** com folga; um cabe.

Três detalhes que essa junção obrigou:

1. **Um cadeado, não dois.** O gerador de logo tinha Basic auth própria
   (popup do navegador). Manter as duas pediria a senha duas vezes na mesma
   sessão. Então `wsgi.py` desliga a Basic dele (`SENHA = ""`) e põe a guarda
   de sessão do sistema na frente de `/logo` inteiro — **inclusive as rotas
   de API**, que é o que de fato importa: sem a guarda, desligar a Basic
   deixaria `/logo/api/gerar` aberto na internet. Há teste para cada uma
   dessas rotas.
2. **O front do logo virou relativo.** Ele chamava `fetch('/api/gerar')`, que
   sob `/logo/` bateria na raiz e daria 404. Uma linha resolve, e ela deriva
   o prefixo em vez de fixá-lo:
   `const BASE = location.pathname.replace(/\/+$/, "")...`
3. **Falta de dependência não derruba o painel.** Se `opencv` ou `trimesh`
   não estiverem instalados, `/logo` responde 503 dizendo qual import falhou
   — o resto do sistema continua no ar. Antes, o mesmo erro impediria o
   processo inteiro de subir.

O que **não** mudou: `sistema/logo/app.py` continua chamando as funções de
`gerar_logo_3d.py`, sem geometria duplicada no servidor. É a regra de ouro do
`CLAUDE.md` e ela vale igual depois da junção.

### Duplicação que sobrou

`morumbi3d/letras/geom2d.py` reimplementa em Python puro o que `shapely`
(deslocamento de polígono, booleanas) e `mapbox_earcut` (triangulação) fazem —
e agora que os dois estão no mesmo `requirements.txt`, essa duplicação não tem
mais desculpa de "rodar sem instalar nada". Trocar `geom2d.py` por shapely é o
próximo passo óbvio, e é também o conserto de verdade do cortador (ver
limitações abaixo). Não fiz junto porque é reescrita de geometria, e geometria
aqui só muda com o verificador de malha confirmando peça a peça.

O corte já usa a stack de vocês: `letras/malha.py` prefere o cortador próprio
(mais rápido, e medindo sai na frente) e chama o `trimesh` só nos planos onde
ele falhou — a 1 200 mm isso salva 25 cortes. A ponte respeita as armadilhas
já documentadas: nunca `process(validate=True)`, `merge_vertices()` +
`fix_normals()`, e `disponivel()` testa `scipy`, `networkx` e `rtree` de
saída, em vez de deixar o erro aparecer longe da causa.

## Testes

```bash
cd morumbi3d
python3 -m unittest discover -s tests -t .
```

194 testes, **sem rede**. Os da curadoria e do gerador de letra caixa rodam
sem dependência nenhuma; os do sistema pedem Flask, e os dois que abrem o
gerador de logo se pulam sozinhos quando `opencv`/`trimesh` não estão
instalados — quem só quer o painel não precisa de 180 MB de biblioteca.
Curadoria: malha (STL binário/ASCII,
3MF, OBJ, arquivo truncado, balanço, mesa), licenças, marcas, tradução,
linhas, custo, banco, deduplicação, tolerância a falha por fonte, parsing de
cada conector, relatório, CSV e CLI. Letra caixa: aninhamento de contra-formas,
erosão, triangulação com conservação de área, leitura de SVG, e — o que mais
importa — **toda combinação de geometria é verificada como malha fechada**,
incluindo os cortes, onde a soma dos volumes tem que bater com a peça inteira.
Os testes da ponte do `trimesh` se pulam sozinhos quando ele não está
instalado. Junção: as quatro rotas de `/logo` recusam quem não entrou, a
interface usa prefixo relativo, e falta de dependência devolve 503 em `/logo`
sem derrubar o painel. Implantação: o `gunicorn.conf.py` carrega e obedece o
`MORUMBI_BIND` do systemd, e todo caminho que os scripts mandam usar existe —
foi assim que apareceram duas referências que a junção deixou para trás.

## Ainda não implementado na curadoria (segunda fase, §4)

Busca por imagem/forma (o gancho está em
[`sources/thangs.py`](morumbi3d/sources/thangs.py)), alertas de novidades,
pré-visualização 3D renderizada, integração direta com o Bambu Studio.

---

# Gerador de letra caixa (`morumbi3d letra`)

Converte um **SVG com o texto já em curvas** em letra caixa pronta para
imprimir: face na frente, paredes seguindo o contorno e fundo aberto.

```bash
morumbi3d letra logo.svg --altura 300 --profundidade 30 \
  --parede 2.4 --frente 2.5 --chanfro 1.5 --furos-auto
```

Saída: um STL por peça em `~/.morumbi3d/letras/<nome>/`, mais o relatório de
cada uma — dimensões, malha fechada, se cabe na mesa, gramas, horas, custo e
preço sugerido.

## O que ele faz

**Lê o SVG de verdade.** Caminhos com todos os comandos (incluindo curvas de
Bézier e arco elíptico), `rect`, `circle`, `ellipse`, `polygon`, `polyline`, e
`transform` acumulado pela árvore. Contra-formas — a barriga do "B", o miolo
do "O" — são reconhecidas pela regra par/ímpar, inclusive ilha dentro de furo.
Traço (`stroke`) é ignorado: o que vira material é o preenchimento.

**Monta a caixa.** A cavidade é o contorno erodido pela espessura de parede.
Quando o traço da letra é fino demais para duas paredes, a peça sai maciça e
o aviso diz por quê — em vez de gerar uma casca impossível.

**Filete lateral** (`--chanfro`): a face da frente encolhe e é costurada ao
corpo como uma tira de quadriláteros, tirando o "degrau" da aresta.

**Furos de fixação** (`--furos "x,y;x,y"` ou `--furos-auto`): atravessam só a
face da frente na letra caixa, e a peça inteira na maciça. Furo que cai fora
da área útil é recusado com aviso — nos automáticos, silenciosamente.

**Corta o que não cabe.** Letreiro de 1 m não entra numa mesa de 25 cm: a peça
é cortada por planos verticais nos dois eixos e cada corte é **tampado**, para
cada pedaço sair fechado e colável.

## Por que ele confere o próprio trabalho

Nada é gravado sem antes passar pelo mesmo analisador de malha da curadoria:
*esta malha é fechada? quantas partes soltas? cabe na mesa?* Isso já pagou:

- a costura dos furos ao contorno inseria um vértice na tampa que a parede não
  tinha — 152 arestas sem par numa peça que "parecia certa". Daí veio o
  `costurar_juntas_t`, que divide a aresta em leque;
- o corte no eixo de simetria de uma peça simétrica saía não-manifold. Hoje o
  plano anda alguns milímetros — dentro da folga que a mesa ainda permite — até
  sair peça sã, e diz que andou.

O que o verificador não conseguir consertar, ele **denuncia**: a peça é
nomeada no aviso e o comando sai com erro, em vez de entregar STL quebrado.

## Limitações conhecidas do gerador

- **O cortador não escala.** Medido no mesmo SVG de três letras, variando só
  a altura:

  | Altura | Peças | Malha aberta |
  | --- | --- | --- |
  | até 800 mm | até 29 | **0%** |
  | 1 200 mm | 47 | 4% (2 peças) |
  | 2 000 mm | 111 | **68% (76 peças)** |

  Para letra caixa de tamanho normal — e 800 mm já é um letreiro grande — ele
  está sólido. Para vários metros ele **não serve** hoje. O comando avisa
  quando passa de 12 peças e nomeia cada peça aberta, então a falha nunca é
  silenciosa. O conserto de verdade continua sendo cortar os contornos em 2D
  **antes** de extrudar (com `shapely`, que o morumbi3d_web já usa), e não a
  malha depois: aí cada pedaço nasce fechado pelo mesmo caminho que já é
  confiável. Enquanto isso: gere uma letra por vez ou use `--sem-cortar` e
  corte no fatiador.
- **O chanfro é reto** (chanfro/bisel), não um filete arredondado.
- **Sem encaixe entre pedaços**: as peças cortadas têm face plana de cola, sem
  pino ou rabo de andorinha.
- **A fonte precisa estar em curvas.** Texto vivo no SVG não vira material — o
  comando avisa e ensina o conserto.

## Limites que valem dizer em voz alta

- **Material e tempo são estimativa**, não fatiamento: servem para descartar
  cedo o que é inviável. O número final é o do Bambu Studio. Calibre
  `vazao_cm3_por_hora` com uma peça real.
- **O filtro de licença é triagem, não parecer jurídico.** Ele reduz o volume
  a conferir e obriga a decisão a ficar registrada; a conferência na página do
  modelo continua sendo sua.
- **Os custos padrão são chute razoável.** Troque pelos seus em
  `morumbi3d.toml` antes de usar o preço sugerido.
