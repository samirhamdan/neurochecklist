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
