# Morumbi 3D — Busca e Curadoria de Modelos 3D Prontos

Sistema de linha de comando para **encontrar, avaliar e organizar modelos 3D
prontos** (STL/3MF) de repositórios públicos, alimentando o catálogo da
Morumbi 3D com modelos de terceiros bem selecionados.

Implementa a especificação funcional *Sistema de Busca e Curadoria de Modelos
3D*, na ordem recomendada por ela: banco de dados + analisador de malha →
conectores de fonte → filtro de licença → relatório de curadoria.

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

## Testes

```bash
cd morumbi3d
python3 -m unittest discover -s tests -t .
```

112 testes, sem rede e sem dependências: malha (STL binário/ASCII, 3MF, OBJ,
arquivo truncado, balanço, mesa), licenças, marcas, tradução, linhas, custo,
banco, deduplicação, tolerância a falha por fonte, parsing de cada conector,
relatório, CSV e CLI.

## Ainda não implementado (segunda fase, §4)

Busca por imagem/forma (o gancho está em
[`sources/thangs.py`](morumbi3d/sources/thangs.py)), alertas de novidades,
pré-visualização 3D renderizada, integração direta com o Bambu Studio.

## Limites que valem dizer em voz alta

- **Material e tempo são estimativa**, não fatiamento: servem para descartar
  cedo o que é inviável. O número final é o do Bambu Studio. Calibre
  `vazao_cm3_por_hora` com uma peça real.
- **O filtro de licença é triagem, não parecer jurídico.** Ele reduz o volume
  a conferir e obriga a decisão a ficar registrada; a conferência na página do
  modelo continua sendo sua.
- **Os custos padrão são chute razoável.** Troque pelos seus em
  `morumbi3d.toml` antes de usar o preço sugerido.
