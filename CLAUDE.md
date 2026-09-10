# CLAUDE.md — Gerador de Logo 3D / Morumbi 3D

Contexto do projeto para o Claude Code. Leia antes de mexer em qualquer arquivo.

---

## O que é

Ferramenta que converte imagem raster (JPG/PNG) de um logo em arquivos STL prontos
para impressão 3D. Faz parte da divisão **Morumbi 3D**, braço de impressão 3D da
Morumbi Festas (locação de decoração para eventos, Campo Grande/MS).

É irmão do gerador de letreiros (`gerador-letreiros.html`), que parte de fonte
vetorial. Aqui a entrada é raster, o que acrescenta duas etapas que o outro não
tem: recorte do fundo e vetorização.

**Usuário:** Samir, dono do negócio. Não é desenvolvedor. Trabalha em português,
no Windows, e roda comandos que a gente entrega prontos. Escreva mensagens de
erro e comentários em português, sem jargão desnecessário.

---

## Arquitetura

```
morumbi3d_web/
├── gerar_logo_3d.py       # motor: imagem -> STL. Funciona sozinho pelo terminal.
├── app.py                 # servidor Flask. IMPORTA o motor, não reimplementa.
├── wsgi.py                # entrada do gunicorn
├── gunicorn.conf.py       # workers, timeout, reciclagem de memória
├── static/index.html      # interface completa: HTML + CSS + JS num arquivo só
├── requirements.txt
├── morumbi3d.service      # unit do systemd
├── nginx-morumbi3d.conf   # NÃO USADO em produção (ver Implantação)
├── COMO_RODAR.txt         # guia local, para o Samir
└── IMPLANTAR.txt          # guia de VPS, para o Samir
```

**Regra de ouro:** `app.py` chama as funções de `gerar_logo_3d.py`. Nunca duplique
lógica de geometria no servidor. Melhorou o motor pelo terminal, a interface
herda de graça.

### Pipeline

```
imagem
  -> carregar_imagem()        reduz se > 1400px, AMPLIA se < 1100px
  -> mascara_do_objeto()      alpha > cor dos cantos > Otsu
     ou mascara_por_cor()     distância em LAB a partir de --cor-alvo
  -> limpar_mascara()         abertura, fechamento, descarte de fragmento
  -> preencher_mascara()      só para logo vazado (contorno -> sólido)
  -> mascara_para_poligonos() cv2.findContours RETR_CCOMP -> shapely, com furos
  -> auditar_geometria()      traço fino e peça solta, ANTES de imprimir
  -> extrudar()               shapely -> trimesh, via earcut
  -> criar_placa()            base que segura as partes soltas
  -> STL + preview PNG + relatório TXT
```

---

## Armadilhas já pagas com sangue

Estas foram descobertas em produção, com logo real. Não desfaça nenhuma sem
entender por quê.

### `process(validate=True)` do trimesh abre a malha

Ele apaga triângulos degenerados que o earcut cria em cantos simplificados, e
cada triângulo apagado deixa um furo. Resultado: STL não estanque, que alguns
fatiadores recusam. **Use `merge_vertices()` + `fix_normals()`.**

### Juntar vértices depois de concatenar também abre a malha

Corpos que só se encostam viram aresta com 4 faces. **Costure cada corpo
separadamente, antes do `concatenate`.** Depois de juntar, não toque mais.

### Furo encostando na casca

Miolo de R, B ou A que a simplificação colou na borda forma um estrangulamento
que o earcut não fecha. `extrudar()` detecta e conserta com
`buffer(0.01).buffer(-0.01)`. Micro-abertura, imperceptível na peça.

### Limite de ruído tem que ser relativo ao DESENHO, não à imagem

Logo pequeno dentro de tela grande faz o filtro classificar letra de verdade
como sujeira. Foi o que destruiu o "FESTAS" do logo da Morumbi. Hoje
`limpar_mascara()` mede contra `(mask > 0).sum()`.

### Imagem pequena precisa ser AMPLIADA antes de processar

Logo de 500px tem texto secundário com traço de 2 a 3 pixels; a limpeza
morfológica come esse traço antes de virar geometria. `carregar_imagem()` amplia
para 1100px com LANCZOS. Parece contraintuitivo ampliar raster, mas preserva o
detalhe fino.

### Abertura morfológica: iterações de raio 1, nunca núcleo grande

Núcleo 5x5 de uma vez devora traço de 2px. Vários passes de 3x3 limpam o mesmo
ruído sem destruir.

### `--fechar-vaos` e texto pequeno são inimigos

Fechar vão de faceta e fechar contraforma de "e", "b", "S", "A" são a mesma
operação na mesma escala. Não dá para resolver os dois com um botão só. Padrão
é 2. Se o logo tiver texto pequeno, não suba.

### Placa fragmentada

Logo com elementos distantes gera várias placas separadas. No logo da Morumbi,
4 mm dava 3 pedaços; 6 mm era o mínimo para unir; usamos 7 mm. Sempre confira
`len(como_lista(placa))`.

### Preenchimento de contorno usa paridade 4k / 4k+3

Em arte de contorno cada traço gera 2 níveis de aninhamento. Sólido nos níveis
múltiplos de 4, vazado nos 4k+3. É isso que mantém o miolo do "O" furado em vez
de virar disco cheio. Modo `tudo` preenche tudo, para logo sem contraforma.

### `scipy` é dependência obrigatória

O `trimesh` usa em `fix_normals` para contar corpos. Não vem junto e o erro
aparece só na hora de extrudar, longe da causa.

### `opencv-python-headless` no servidor

A versão normal puxa bibliotecas gráficas que não existem em VPS.

### O gerador de letreiros são três arquivos, e a divisão tem guarda

Desde o C1, `web/nucleo/`:

    nucleo.js    polígono, sólido, STL, a mesa      qualquer gerador
    oficina.js   os números DESTA casa              purga, densidade, preço
    letreiro.js  o desenho do letreiro              só ele

`gerador-letreiros.html` carrega os três por `<script src>` **relativo** — por
isso a rota é `/letreiros/` **com barra**, e por isso as ferramentas em
`ferramentas/` copiam a pasta `nucleo/` junto quando montam a página
temporária (`pagina_temporaria.js` faz isso num lugar só).

Há teste que reprova `'magia'` dentro do núcleo. Sem ele a divisão dura um
sprint: alguém precisa de um ajuste rápido, põe um `if` do letreiro no núcleo,
e o próximo gerador herda uma regra que não é dele.

### Polígono no sentido horário vira FURO

O Clipper com preenchimento NonZero trata caminho horário como buraco. Unir
uma forma enrolada ao contrário ao resto da peça **subtrai** ela. O canvas
desenha igual nos dois sentidos, então isso é invisível na tela: sai peça em
dois corpos e aresta não-manifold no STL.

Toda forma nova passa por `antiHorario()` em `topo.js`, e há teste que calcula
a área com sinal de cada uma.

### Duas partes que só se encostam não estão ligadas

`analisar().corpos === 1` não basta: duas formas tangentes são um corpo só em
2D e viram aresta não-manifold ao extrudar — o fatiador recusa. `conexaoFragil`
(em `oficina.js`) encolhe 0,05 mm e vê se a peça se parte. Ela **não** detecta
peça já separada; para isso é `corpos`, e os dois são cobrados.

O `empilhar` do `texto.js` aceita um parâmetro `sobrepor` justamente por isso:
sem ele converge no ponto do toque, que é a ligação mais fraca possível.

### Peça nova = um módulo de geometria + uma entrada em `pecas.js`

Desde o C4 há **uma** tela de gerador (`web/gerador.html`) para todas as peças
de template. `web/nucleo/pecas.js` é o registro: nome, rótulo, prefixo de SKU,
campos, tamanhos, textos, e a linha extra que a peça mostra nas medidas.

O módulo de geometria precisa de `Gerador(fontes).gerar(pedido)` devolvendo
`{viavel, paths, camadas, bb, avisos, corpos, esperado, espessura, nome, …}`
ou `{viavel:false, motivo}`. Tudo o mais — vistoria, estimativa, preço, nome
de arquivo, registro de geração — vem da plataforma.

Há teste que reprova texto de uma peça só dentro da tela (`haste`, `argola`,
`topo de bolo`): é o começo da segunda cópia.

### A semente de templates diz de qual sprint veio

`templates-iniciais.json` tem um campo `desde` (`"C2"`, `"C4"`). Num banco que
já existe, só as entradas de sprints anteriores são dadas por vistas — é assim
que template novo chega à VPS sem ressuscitar o que o Samir apagou. Já errei
nos dois sentidos: por SKU (ressuscitava) e por "já rodou" (nunca chegava).

### Templates de topo de bolo moram no BANCO, não no código

Desde o C3 são linhas da tabela `templates`, editadas em `/templates`.
`web/nucleo/templates-iniciais.json` é só a **semente**, e ela entra **uma vez
na vida do banco** (marcada em `parametros.semente_templates`) — por SKU,
apagar um template o trazia de volta na conexão seguinte.

`/topo/templates` é a porta: **sem sessão entrega só o publicado**. É a regra
do §10 do documento, e é onde a vitrine da sprint 8 vai se plugar.

### Formulário que volta com erro precisa dos campos TIPADOS

`render_template(..., atual=request.form)` quebra: no form cru tudo é texto e
campo não preenchido nem existe, então `|round` cai em Undefined. Use
`campos_<coisa>(request.form)`, que é para isso que essas funções existem.
Aconteceu no filamento (sprint 1) e de novo no template (C3).

### Geradores: as três pastas partilhadas

`web/libs/` (opentype, ClipperLib, earcut), `web/fontes/` (as cinco em base64)
e `web/nucleo/` são carregadas por **caminho relativo** pelas duas páginas de
gerador. Por isso as rotas terminam em barra (`/letreiros/`, `/topo/`) e as
ferramentas copiam as três pastas para a página temporária.

Arquivo `.js` e não `.ttf` nas fontes: as ferramentas abrem a página como
`file://`, e ali o navegador bloqueia `fetch` mas deixa `<script src>` passar.

### Mexeu no topo de bolo? Rode a matriz

    node ferramentas/conferir_topos.js /tmp/topos          # 192 peças, ~6 min
    node ferramentas/conferir_topos.js /tmp/topos --rapido # os extremos, ~65 s

Depois passe os STL pelo `analisar_arquivo` do pacote. É o §16 do documento do
Samir traduzido: "o modelo fatia sem erros". A suíte roda a versão curta.

### Mexeu em geometria? Confira a impressão digital

    node ferramentas/impressao_digital.js --conferir docs/impressao-digital.txt

Vinte casos, um sha256 por peça. É o único jeito honesto de refatorar
geometria: um teste que só olha "malha fechada" passa feliz com a peça virada
do avesso. Roda junto da suíte quando há Chromium (~75 s).

Mudou um hash e a peça **devia** mudar? Regenere e explique no commit qual
peça mudou e por quê:

    node ferramentas/impressao_digital.js > docs/impressao-digital.txt

### O menu é dado, em `app.py`

`MENU` é uma tupla de grupos; `_grupo_de(endpoint)` diz qual abre. A lateral se
desenha a partir disso, e há teste que **abre cada rota do menu**. Numa lista de
links escritos a mão, um item apontando para o lugar errado só aparece quando
alguém clica.

Os grupos são `<details>/<summary>`: abrem pelo teclado sozinhos, sem
JavaScript. O único script da casca é o da gaveta.

### Item de grid e de flex nasce com `min-width:auto`

Que significa "no mínimo a largura do conteúdo" — e é por isso que um cartão de
594 px cabia numa coluna de 372 px e empurrava a página inteira para fora da
tela. Foi o último transbordo que sobrou depois da lateral, e só aparece em
tela estreita. `.duas-colunas > *{min-width:0}`.

### `focus()` em elemento escondido não faz nada, e não dá erro

A gaveta focava `querySelector("a, summary")` — que no telefone é o link da
marca, `display:none`. O foco simplesmente ficava fora da gaveta recém-aberta.
Pior: o teste do Escape passava, porque "voltar o foco para o botão" era um
no-op. Filtre por `getClientRects().length > 0`.

### `gramas_est` e `horas_est` são o total da LINHA

Quem multiplica é `app.py` ao montar o item do pedido ("peso e tempo são por
peça no catálogo; a fila precisa do total"). Por isso a baixa de **filamento**
não multiplica de novo — e a de **insumo** multiplica, porque o que é por
unidade lá é a quantidade do vínculo produto-insumo.

Li o `_baixar`, achei que a assimetria fosse defeito, "consertei" e vi
`test_quantidade_multiplica_peso_e_tempo` ficar vermelho. O defeito era meu.
Antes de mexer nessa conta, leia o teste.

Cuidado ao semear banco de exemplo chamando `salvar_pedido` direto: ele grava
o que você mandar. Semeie `gramas = por_unidade * quantidade`, senão a tela de
teste mostra número que a tela de verdade não mostraria.

### `web/gerador.html` é arquivo ESTÁTICO

`send_from_directory` o entrega cru — Jinja não passa por ali. Um `{# … #}`
sai **impresso na tela**, e eu já paguei esse: um comentário meu apareceu
como texto no meio da prévia. Use `<!-- -->`.

### Tela vazia ensina; espera fala

Toda tela do menu tem que dizer alguma coisa com o banco zerado, e
`tests/test_vazios.py` varre todas elas — não basta não quebrar. O recado
precisa de uma **saída**, não só do fato: "Nenhum pedido." é um fato.

As colunas do quadro têm `dados.CONVITES`, ao lado de `ETAPAS`: etapa nova sem
convite fica vermelha no teste, em vez de nascer muda.

No gerador, a prévia leva ~1,9 s até haver o que ver na primeira carga. O
`#estado` ganha a classe `cobrindo` e ocupa a área da prévia enquanto **não há
desenho**; assim que há peça, volta a ser a linha de 14 px. Cobrir a peça a
cada tecla piscaria pior do que deixar o desenho anterior no lugar pelos
273 ms do redesenho — há teste para os dois lados.

### O erro sabe de qual campo ele é

`dados.ErroDeCampo(campo, mensagem)` — herda de `ValueError`, então quem já
tratava continua tratando. `app.py` traduz com `_erro(excecao)`, que devolve
`{erro, campo_erro}`; o topo vira um atalho (`_erro.html`) e a mensagem mora
embaixo do campo, em `<b class="recado-campo">`.

Cada `<label class="campo">` tem `id="campo-<name>"`. Há teste que varre o
`dados.py` atrás de todo `ErroDeCampo("X"` e cobra que exista um
`id="campo-X"` em alguma tela — renomear de um lado só deixaria o atalho do
topo levando a lugar nenhum, em silêncio.

Nem todo erro é de um campo. Quando não é, o topo mostra a mensagem como
antes; a compra sem item aponta o **título da tabela**, que é o que precisa
ganhar linha.

### `position:sticky` só gruda dentro do próprio pai

A barra de Salvar em produto e pedido morava num cartão da coluna lateral:
sticky ali não tem para onde grudar. Ela virou filha do `<form>` — e isso
também é mais certo, porque Salvar é do formulário inteiro.

Sticky faz a coisa **condicional** de graça: num cadastro curto a barra fica
em fluxo no fim, sem custar nada; num comprido gruda no pé da tela. Barra
`fixed` custaria 60 px de tela em toda tela, e taparia o último campo no fim
do formulário — há teste para os dois lados.

### Proteção de formulário mora na casca, não na tela

`base.html` carrega um script que vale para todo `form[data-avisar]`: aviso
antes de sair com alteração não salva, e `blur()` no campo numérico ao rolar
a página. Escrito por formulário, o próximo cadastro nasceria sem nenhum dos
dois — há teste que reprova uma segunda cópia de `beforeunload` nas telas.

Salvar e Cancelar **não** perguntam: um é a gravação, o outro é a desistência.
Sem essa parte, o aviso aparecia justamente no botão de desistir.

Comparar o formulário inteiro (`new URLSearchParams(new FormData(form))`) e
não uma lista de campos guardada no começo: as linhas de item que o
JavaScript da tela cria depois não estariam na lista.

### Rodinha do mouse em `<input type=number>` muda o valor

Comportamento padrão do navegador: com o campo focado, rolar a página troca
83,7 g por 82,7 g e ninguém vê. O peso e o tempo saem do arquivo 3D
justamente para não serem chute — e um chute entrava assim, sem toque em
tecla nenhuma.

### `type="number"` já abre teclado numérico

O plano de interface dizia que os campos de número abriam o alfabético. A
medida desmentiu: dos 63 campos, **um** abria o teclado de letras — o
WhatsApp do cliente, que é o mais digitado no telefone. O `inputmode` ainda
vale (`numeric` para `step=1`, `decimal` para o resto), porque o iPhone entrega
`type=number` sem a vírgula em várias versões.

Medir antes de consertar vale para plano meu também.

### A linha e o cartão são o MESMO DOM

Desde o U3, abaixo de 640 px cada `<tr>` vira um cartão por CSS. Não existe
uma marcação para tela larga e outra para telefone — o que a linha mostra, o
cartão mostra, e há teste de navegador que compara o `innerText` das linhas em
1280 px e em 420 px. Esconder uma coluna no telefone com `display:none` é o
atalho óbvio para "não cabe", e é o que esse teste reprova.

Cada `<td>` carrega `data-rotulo` com o nome da sua coluna, e quatro classes
dizem o papel: `.chave` (título), `.estado` (etiqueta), `.decide` (o número
que decide), `.acao` (o botão no pé). O papel manda na ORDEM do cartão, e não
a posição da coluna — em Templates o título é a segunda coluna.

`tests/test_cartoes.py` compara `data-rotulo` com o `<th>` da mesma coluna em
toda tabela de toda tela. Sem isso o rótulo vira a segunda cópia do cabeçalho
e envelhece sozinho.

### Ordenar e buscar: uma lista de ordens, duas interfaces

`sistema/listas.py` tem `ORDENS_*` e `BUSCA_*` por tela. O cabeçalho clicável
(tela larga) e a caixa de seleção (telefone, onde não há cabeçalho) saem das
mesmas tuplas, e há teste que compara as duas.

Ordena em **Python**, sobre a lista já lida — montar `ORDER BY` com texto da
URL abre injeção. A lista de permitidos é a mesma proteção sem o risco. Cuidado
com o teste fraco: chave *inventada* não ordena por acidente (é nula em toda
linha). O que a lista protege é o campo que **existe** e não devia sair na URL.

O vazio vai para o fim **nos dois sentidos**. "Sem prazo" não é o prazo mais
urgente nem o menos: no meio da lista ele esconde os que têm.

### Regra de CSS que perde por ordem de fonte

O conserto do alvo de 44 px da barra de busca ficou **antes** do bloco
`.peneira` no arquivo, com a mesma especificidade — e perdeu. Media query não
soma especificidade. Quando duas regras empatam, quem vem depois ganha.

### Alvo de toque: link em prosa não tem conserto

44 px é o que um dedo acerta, e vale só no telefone — no computador o ponteiro
é preciso e a densidade é vantagem. Mas um link no meio de uma frase tem a
altura da linha, e esticá-lo destrói o parágrafo. A saída não é abrir exceção
no teste: é **não pôr o controle dentro da frase**. Numa tela vazia, a ação
vira botão; num aviso, o aviso inteiro vira o link.

### Um número que a tela também mostra sai da MESMA função

Desde o U2, `dados.somar_valor`, `dados.horas_na_mesa`,
`dados.parado_em_filamento` e `custo.retorno_por_hora` são chamadas pelo
painel **e** pela tela para onde o número aponta. Não é preciosismo: um total
somado aqui por uma consulta e lá por outra passa a discordar no dia em que
uma das duas ganhar um filtro — e quem olha não tem como saber qual vale.

Os testes de `tests/test_painel.py` seguem o link e comparam os dois lados.
Por isso os valores têm `id` no HTML: `v-a-receber`, `v-na-mesa`, `v-parado`,
`v-entregue`, `total-pedidos`, `parado-total`, `horas-na-mesa`.

### Dinheiro e data têm filtro; `<input>` continua em formato de máquina

`|dinheiro`, `|numero(n)`, `|data`, `|datahora` (em `sistema/formato.py`).
`<input type="number">` **só** aceita ponto decimal — quem lê ali é o
navegador, não o Samir — então `value="{{ '%.2f'|format(x) }}"` está certo e
o teste que varre os templates ignora atributos `value`.

`agora()` grava em UTC e `|datahora` converte para o relógio daqui. O
`criado_em[:16].replace('T',' ')` que existia antes não errava o formato:
errava o **fuso**, em silêncio, e só depois das 20h — quando a data também
troca de dia.

### `width:1px` numa `<table>` é só um mínimo

A tabela do gráfico para leitor de tela ficou com 265 px de caixa invisível
solta por cima da tela: `<table>` cresce até caber o conteúdo, e ignora um
`width` menor. A classe de esconder vai num `<div>` em volta. Quem achou foi
o teste de navegador medindo `getBoundingClientRect`.

### Regra escrita para dois itens quebra no terceiro

`a.atalho:nth-of-type(2){border-left-color:laranja}` foi escrita quando havia
dois atalhos no painel — letreiro azul, logo laranja, as duas metades do M.
Com nove cartões, o segundo ficou laranja por acaso. Cor por **posição** é
uma bomba-relógio; cor por **categoria** não é.

### Nome de classe curto é barato até colidir

Chamei a barra do celular de `.barra`. `.barra` já era das barras de estoque do
painel: elas sumiram da tela, sem um erro sequer no console. Antes de criar uma
classe, `grep` nos templates.

### `display` de classe ganha do `[hidden]` do navegador

`el.hidden = true` põe o atributo, e o atributo só esconde porque a folha do
navegador diz `[hidden]{display:none}` — regra fraca, que qualquer
`.minha-classe{display:flex}` derruba. A tela fica com o atributo certo e
**nada some**.

`sistema.css` carrega `[hidden]{display:none !important}` por causa disto.
Custou um filtro que marcava tudo como oculto e mostrava os oito cartões, e a
descoberta de que o botão Quadro/Lista da produção estava assim havia um
sprint inteiro.

### Conferir a tela pelo DOM é conferir a coisa errada

O bug acima passou por uma conferência minha no navegador: eu perguntei por
`.modelo:not([hidden])` — o ATRIBUTO — e recebi a resposta certa enquanto a
tela mostrava tudo. **Pergunte se o elemento tem caixa** (`offsetParent !==
null`), que é o que a pessoa vê. É a regra de `tests/test_navegador.py`.

### `networkidle` no teste de navegador mede a internet

As telas puxam fonte do Google. Numa máquina sem saída, `wait_for_load_state
("networkidle")` espera até estourar o tempo e o teste parece travado. Os
testes de navegador bloqueiam tudo que não é `127.0.0.1` e esperam por
seletor, nunca por rede parada.

---

## Estado do servidor

Estado em **disco**, nunca em memória. Com vários workers do gunicorn, cache em
memória faz o upload cair num processo e a prévia noutro, que responde "imagem
expirou" sem motivo aparente. Também vaza memória, o que num VPS pequeno derruba
o serviço.

Cada sessão é uma pasta em `MORUMBI_DADOS` com a imagem e `ficha.json`.
`caminho_sessao()` valida o id (12 caracteres hexadecimais) para barrar travessia
de diretório. `faxina()` apaga uploads com mais de `MORUMBI_VALIDADE_H` horas.

---

## Implantação em produção

VPS RackNerd, Ubuntu 24.04, IP `23.95.96.132`, 2 GB de RAM com pouco livre.
Domínio `morumbi3d.duckdns.org`.

**A máquina já tinha uma infraestrutura Docker rodando** (`lite_default`):
Caddy, n8n, Evolution API, Postgres, Redis e um atualizador de DuckDNS. O Caddy
é dono das portas 80 e 443.

Por isso o `nginx-morumbi3d.conf` **não é usado**. O nginx foi instalado e
depois desativado. Quem faz proxy é o Caddy, pelo bloco acrescentado em
`/opt/sdr-agent/infra/lite/Caddyfile`:

```
morumbi3d.duckdns.org {
        reverse_proxy 172.18.0.1:5000
}
```

O app escuta em `172.18.0.1:5000`, o gateway da rede Docker — **não em
127.0.0.1**, que de dentro do container seria o próprio container. Continua
inacessível pela internet, porque é IP privado.

O Caddy emite e renova o certificado sozinho. Não use certbot.

O **ufw não protege as portas publicadas pelo Docker**, que escreve as próprias
regras de iptables e passa por cima. Não crie falsa sensação de segurança com ele.

```
Instalação:  /opt/morumbi3d          (venv em ./venv)
Dados:       /var/lib/morumbi3d
Serviço:     systemctl {status,restart} morumbi3d
Logs:        journalctl -u morumbi3d -f
Workers:     1  (a RAM não comporta 2)
MemoryMax:   800M
```

Atualizar código: copiar para `/opt/morumbi3d`, `chown -R morumbi:morumbi`,
`systemctl restart morumbi3d`.

---

## Comandos

```bash
# Local
python3 app.py                       # http://localhost:5000
py app.py                            # Windows, onde "python" não está no PATH

# Motor direto, útil para depurar
python3 gerar_logo_3d.py logo.png --largura 150 --borda 7

# Logo vazado, fundo escuro
python3 gerar_logo_3d.py logo.png --cor-alvo "#FFE81F" --preencher contorno

# Produção
gunicorn -c gunicorn.conf.py wsgi:app
```

Variáveis: `MORUMBI_USUARIO`, `MORUMBI_SENHA`, `MORUMBI_DADOS`,
`MORUMBI_VALIDADE_H`, `MORUMBI_WORKERS`, `MORUMBI_BIND`, `MORUMBI_PORTA`.
Sem `MORUMBI_SENHA` a autenticação fica desligada — só para uso local.

---

## Valores calibrados

Logo Morumbi Festas, 500x500px, a 150 mm de largura:

```
--borda 7  --fechar-vaos 2  --suavizar 1
-> 150.0 x 108.7 x 5.0 mm, 21 corpos, placa em peça única, tudo estanque
```

Os 21 corpos são o símbolo M facetado mais as 13 letras. A placa segura tudo.

---

## Convenções

- Código, comentários, mensagens de erro e interface **em português**.
- Comentário explica **por quê**, não o quê. Especialmente nas armadilhas acima.
- Toda mudança em geometria precisa ser validada com logo real, não sintético.
  Os testes sintéticos não pegaram nenhum dos quatro defeitos que o logo da
  Morumbi revelou.
- Sempre confira `is_watertight` depois de mexer em `extrudar()`.
- Interface: palco escuro para julgar máscara, bancada clara para ler número.
  Máscara em rubilith `#E23A45`, referência à película de mascaramento de
  fotolito. Barlow + IBM Plex Mono. Prévia atualiza em ~0,3s, o que substitui o
  ciclo rodar-conferir-ajustar.

---

## Propriedade intelectual

**Não** adicione ao catálogo comercial logo de terceiro com marca registrada
ativa. Star Wars e YouTube foram usados como teste técnico e não podem ser
vendidos nem ficar hospedados no VPS — pedido de remoção chega ao provedor.

Para o catálogo: tema genérico em vez de marca ("festa gamer" em vez do logo de
um jogo), e logo de cliente com autorização.

---

## Pendências

- **M multicolorido**: o símbolo tem ~12 cores. Não sai fiel em FDM. Decisão em
  aberto entre peça única pintada à mão ou separar em 3-5 cores aceitando
  aproximação.
- **Visualizador 3D** na interface. Hoje a conferência é pelo preview 2D e pelo
  fatiador. `three.js` com STLLoader resolveria.
- **`--fechar-vaos` seletivo por tamanho de elemento**, para tratar faceta grande
  e contraforma pequena de formas diferentes.
- **Luminária (60 mm)**: geometria do canal de LED ainda não modelada. Vem do
  gerador de letreiros, vale para logos também.
- Limite de upload de 25 MB precisa bater em três lugares se mudar:
  `MAX_CONTENT_LENGTH` no `app.py`, o proxy e o cliente.
