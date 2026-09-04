# Gerador de letreiros — Morumbi 3D

`gerador-letreiros.html` é o gerador de placas de nome com letras conectadas.
Um arquivo só, sem servidor e sem internet: abre no navegador e funciona.
Traz embutidos o opentype.js (contorno das letras), o ClipperLib (booleanas e
deslocamento de polígono), o earcut (triangulação) e cinco fontes.

## O que ele faz

Digita-se um nome; ele monta a peça e entrega os STL.

- **Letras conectadas**: `encaixeMinimo` faz busca binária pela menor invasão
  que funde duas letras num corpo só — é isso que deixa a peça imprimível
  inteira, sem partes soltas.
- **Duas linhas**: nome composto empilha, procurando o maior afastamento que
  ainda mantém contato.
- **Moldura**: dilata o conjunto até unir tudo, sem fechar as contra-formas.
- **Duas cores**: corpo e capa saem como peças separadas, para troca de cor.
- **Luminária (60 mm)**: peça escavada, com canal para fita de LED.
- Prévia ao vivo, posição na mesa de 256 mm e preço sugerido.

## Luminária: como a peça é montada

Escolher 60 mm troca o bloco maciço por uma caixa oca:

| | |
| --- | --- |
| Frente | 1,6 mm — fina o bastante para o PLA branco difundir a luz |
| Parede | 2,4 mm (6 perímetros de 0,4) |
| Fundo | **aberto**, é por onde entra a fita |
| Rasgo do cabo | 7 mm de largura, 6 mm de altura, no meio da base |

**Sai sempre em peça única.** Separar a frente em outra cor não fecha: numa
letra com contra-forma ("O", "A", "e"), escavar deixa a parede de dentro como
um anel solto — quem segura essa parede é a frente. O gerador detecta isso e
avisa.

**Imprima com a frente virada para a mesa.** Assim o vão fica para cima e não
precisa de suporte.

Quando o traço da letra não comporta parede dos dois lados, a peça sai maciça
e o aviso diz o motivo. Quando o canal fica mais estreito que a fita, ele
também avisa — serve para LED em fio, não para fita.

## Conferir a saída

O gerador roda no navegador, mas dá para conferir a geometria sem abrir o
fatiador: `ferramentas/gerar_letreiro.js` abre a página num Chromium sem tela,
pede uma peça e grava o STL; o analisador de malha do pacote responde se ela
está fechada.

```bash
node ferramentas/gerar_letreiro.js --nome "MORUMBI" --espessura 60 --saida /tmp/stl
./ferramentas/conferir_letreiros.sh          # matriz de regressão completa
```

A regressão cobre 6 produtos em 3 espessuras e **exige malha fechada em todas
as peças** — foi ela que pegou o rasgo do cabo abrindo a malha.

## Junta em T

`costurarJuntasT()` conserta vértice pousado no meio da aresta de outra face.
Acontece quando uma camada tem um recorte que a de cima não tem — o rasgo do
cabo é o caso clássico: a geometria está certa, mas a aresta fica sem par e o
fatiador vê a malha como aberta. A costura divide a aresta em leque; dividir
um ponto por vez não resolve quando há vários na mesma aresta.
