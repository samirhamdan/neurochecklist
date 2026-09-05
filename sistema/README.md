# Sistema de gestão — entrada e painel

Primeira entrega do sistema descrito na especificação: a tela de entrada e o
painel. As duas leem dados de verdade; enquanto não houver pedido cadastrado,
o painel diz isso em vez de fingir movimento.

Tudo junto — painel, letreiros e gerador de logo — **a partir da raiz do
repositório**, que é onde moram o `wsgi.py` e o `gunicorn.conf.py`:

```bash
pip install -r requirements.txt

MORUMBI_DADOS=./dados MORUMBI_USUARIO=samir MORUMBI_SENHA=troque MORUMBI_HTTPS=0 \
  gunicorn -c gunicorn.conf.py wsgi:app
# abre em http://127.0.0.1:5000
```

Só o painel, sem o gerador de logo (não precisa de opencv nem trimesh):

```bash
pip install -e ".[sistema]"
MORUMBI_DADOS=./dados MORUMBI_USUARIO=samir MORUMBI_SENHA=troque \
  python3 -m sistema.app
```

Para conhecer o painel com movimento antes de ter dados reais:

```bash
MORUMBI_DADOS=./dados python3 ferramentas/semear_exemplo.py
MORUMBI_DADOS=./dados python3 ferramentas/semear_exemplo.py --limpar
```

Os nomes são inventados. Não semeie no banco de produção: eles poluiriam o
histórico de que o laço de custo depende.

## As duas telas

Seguem o que o `CLAUDE.md` do gerador de logo já define — **palco escuro para
julgar, bancada clara para ler número**, rubilith `#E23A45`, Barlow + IBM Plex
Mono. A entrada é o palco; o painel, onde se lê número, é a bancada.

O painel mostra a **fila agrupada por cor**, e isso não é decoração: cada
troca de cor custa 6 g de purga, número que o gerador de letreiros já calcula.
Os grupos saem na ordem da peça mais urgente que cada um contém — assim a cor
com o prazo mais apertado abre a fila, e todas as peças dela saem de uma vez.
Ordenar por prazo antes de agrupar separaria a mesma cor em pedidos diferentes
e faria a impressora trocar de filamento à toa.

## O gerador de logo mora aqui dentro

[`sistema/logo/`](logo/) é o `morumbi3d_web` de vocês, movido para dentro do
repositório. Ele não sobe mais sozinho: quem monta tudo é o `wsgi.py` da raiz,
que serve o painel em `/` e o gerador em `/logo/`.

Isso é economia de RAM, não organização: cada processo gunicorn carrega numpy,
scipy, opencv e trimesh por conta própria — 300 a 400 MB. Em 2 GB, dois
serviços separados ficam apertados; um só cabe com folga.

**O cadeado do gerador foi desligado de propósito.** `wsgi.py` faz
`modulo_logo.SENHA = ""` para não pedir senha duas vezes na mesma sessão, e no
lugar dela põe a guarda de sessão do sistema na frente de `/logo` inteiro.
Repare no risco: se essa guarda falhar, o gerador fica **aberto na internet**,
porque a proteção original dele foi retirada. Por isso o teste não confere só
a página — confere `/logo/api/enviar`, `/logo/api/gerar` e `/logo/api/baixar`
uma a uma, que são as rotas que aceitam upload e devolvem arquivo.

Se `opencv` ou `trimesh` faltarem, `/logo` devolve 503 nomeando o import que
falhou e o painel continua funcionando. Antes, esse mesmo erro impediria o
processo inteiro de subir.

**Os dois apps agora dividem o `MORUMBI_DADOS`**, e isso pedia um ajuste: o
gerador de logo apaga sozinho o que passa da validade, para o disco do VPS
não encher, e apagava *qualquer* pasta velha. Era seguro quando ele era dono
da pasta; não é mais, com o banco de pedidos e a chave de sessão morando lá.
A faxina passou a olhar só pasta com nome de sessão (12 dígitos hexadecimais)
— o banco e a chave são arquivos e já escapavam, mas depender disso é frágil
demais para uma rotina que apaga em silêncio.

## Autenticação

Usa as mesmas variáveis que o gerador de logo já usa — `MORUMBI_USUARIO` e
`MORUMBI_SENHA` — e mantém a comparação em tempo constante com
`hmac.compare_digest`. O que muda é a forma: em vez do popup do navegador
(Basic auth), um formulário com sessão, porque uma tela de login precisa poder
dizer o que aconteceu quando dá errado.

Cuidados que valem explicação:

- **Sem senha, o sistema só sobe preso ao próprio computador.** O gerador de
  logo prometia isso num comentário mas não verificava: sem `MORUMBI_SENHA`
  ele liberava tudo, inclusive publicado na internet. Aqui a promessa é
  checada na subida, e o painel avisa quando está rodando aberto.
- **A chave que assina o cookie fica em disco** (`chave_sessao`, modo 600).
  Em memória ela mudaria a cada restart, derrubando todo mundo — e cada worker
  do gunicorn geraria a sua, então a sessão valeria num processo e não no
  outro.
- **Cinco tentativas erradas por endereço** travam por 15 minutos, contadas no
  banco. Entrar certo zera o contador.
- **A mensagem de erro é sempre a mesma**, exista o usuário ou não: dizer
  "usuário não existe" entregaria quais nomes existem.
- **O destino do redirecionamento só pode ser caminho interno.** `//site.fora`
  é o jeito clássico de usar uma tela de login para levar embora quem entrou.
- `/saude` responde sem senha, de propósito: é o que o `implantar/atualizar.sh`
  consulta para saber se o serviço voltou depois do deploy.

## Variáveis

| Variável | Para quê |
| --- | --- |
| `MORUMBI_USUARIO` / `MORUMBI_SENHA` | entrada. Sem senha, só local |
| `MORUMBI_DADOS` | pasta do banco e da chave de sessão |
| `MORUMBI_BIND` | endereço de escuta; decide se rodar sem senha é permitido |
| `MORUMBI_HTTPS` | `1` (padrão) marca o cookie como Secure. Use `0` só em teste local por HTTP |
| `MORUMBI_WORKERS` | processos do gunicorn. Padrão `1`; só suba em máquina de 4 GB ou mais |

Atrás do Caddy o app recebe HTTP puro, então `request.is_secure` é falso lá
dentro — por isso o cookie Secure é decidido por variável, e o IP do visitante
sai do `X-Forwarded-For` para o bloqueio por tentativas funcionar.
