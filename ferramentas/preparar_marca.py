#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera os arquivos de marca que o sistema serve, a partir do original.

    python3 ferramentas/preparar_marca.py

Entrada:  marca/morumbi3d-original.png   (1254x1254, RGBA)
Saida:    sistema/static/marca-simbolo.webp   o M, para o topo e a entrada
          sistema/static/icone-32.png         favicon
          sistema/static/icone-180.png        icone de tela de celular

Duas coisas que este arquivo existe para nao serem redescobertas:

1. O original tem um halo de alfa 1..8 cobrindo a imagem INTEIRA. Ele nao
   aparece na tela, mas engana o getbbox() do Pillow, que corta em alfa>0:
   o recorte do M saia com 1135 de largura em vez de 693, deformando a
   proporcao de 1,16 para 1,84. Zerar o que nao se ve resolve.

2. So o M vai para a tela. Na trava inteira, "MORUMBI" e as palavras "QUE"
   e "FORMA" do lema sao grafite escuro -- elas somem no fundo escuro da
   tela de entrada, porque o logotipo foi desenhado para papel branco. O
   nome e o lema entram como texto, que da para ler nos dois fundos.
"""
import os
import sys

try:
    import numpy as np
    from PIL import Image
except ImportError:
    sys.exit("Precisa de Pillow e numpy:  pip install pillow numpy")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGINAL = os.path.join(RAIZ, "marca", "morumbi3d-original.png")
DESTINO = os.path.join(RAIZ, "sistema", "static")

# Onde o M acaba e a assinatura comeca. Sao faixas totalmente vazias no
# original; se a marca for redesenhada, conferir com:
#   alfa.max(axis=1) <= 8
FIM_DO_SIMBOLO = 685


def sem_halo(img):
    a = np.array(img.convert("RGBA"))
    a[:, :, 3] = np.where(a[:, :, 3] <= 8, 0, a[:, :, 3])
    return Image.fromarray(a)


def apara(img):
    caixa = img.getbbox()
    return img.crop(caixa) if caixa else img


def main():
    if not os.path.exists(ORIGINAL):
        sys.exit(f"nao achei {ORIGINAL}")
    limpa = sem_halo(Image.open(ORIGINAL))
    simbolo = apara(limpa.crop((0, 0, limpa.width, FIM_DO_SIMBOLO)))

    prop = simbolo.width / simbolo.height
    if not 1.05 < prop < 1.30:
        sys.exit(f"o M saiu com proporcao {prop:.2f}, esperava ~1,16. "
                 "O halo voltou, ou a marca mudou de desenho.")

    alto = 256
    largo = round(simbolo.width * alto / simbolo.height)
    simbolo.resize((largo, alto), Image.LANCZOS).save(
        os.path.join(DESTINO, "marca-simbolo.webp"), quality=90, method=6)

    # Favicon e quadrado; a sobra fica transparente, e nao branca -- a aba
    # do navegador pode ser clara ou escura.
    lado = max(simbolo.size)
    folga = round(lado * 0.06)
    tela = Image.new("RGBA", (lado + folga * 2, lado + folga * 2), (0, 0, 0, 0))
    tela.paste(simbolo, ((tela.width - simbolo.width) // 2,
                         (tela.height - simbolo.height) // 2), simbolo)
    for px, nome in ((180, "icone-180.png"), (32, "icone-32.png")):
        tela.resize((px, px), Image.LANCZOS).save(
            os.path.join(DESTINO, nome), optimize=True)

    for nome in ("marca-simbolo.webp", "icone-32.png", "icone-180.png"):
        caminho = os.path.join(DESTINO, nome)
        print(f"  {nome:22s} {os.path.getsize(caminho) // 1024:3d} KB")


if __name__ == "__main__":
    main()
