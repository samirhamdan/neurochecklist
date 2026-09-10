# -*- coding: utf-8 -*-
"""O orcamento em PDF -- o papel que o cliente recebe.

Duas metades, separadas de proposito, como o resto da casa:

    linhas()     o CONTEUDO: itens, subtotal, desconto, total, validade.
                 Nao sabe o que e um PDF, e por isso da para testar a conta
                 sem abrir arquivo nenhum.
    desenhar()   o PAPEL: marca, cores, tabela, rodape. Nao faz conta.

O total sai de `dados.total_do_pedido`, a MESMA funcao que o painel e a tela
de pedidos usam. Um PDF que soma por conta propria e a maneira classica de o
papel dizer um numero e o sistema outro -- e o papel e o que fica com o
cliente.

Fonte: Helvetica, que ja vem no PDF. Ela cobre o portugues inteiro (ã, ç, õ,
é) pela codificacao WinAnsi, entao nao ha fonte para embutir, e o arquivo sai
com uns 4 KB -- abre rapido no telefone, que e onde ele vai ser aberto.
"""
from __future__ import annotations

import io
import os

from . import dados, formato

A4 = (595.28, 841.89)          # pontos, o que o PDF usa
MARGEM = 42.0
GRAFITE = (0.082, 0.098, 0.114)      # #15191D
SUAVE = (0.42, 0.46, 0.50)
LINHA = (0.85, 0.87, 0.89)
ICONE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "icone-180.png")


def _cor(hexa: str) -> tuple[float, float, float]:
    """'#0040F0' -> (0.0, 0.25, 0.94). Cor invalida cai no azul da marca."""
    hexa = (hexa or "").strip().lstrip("#")
    if len(hexa) != 6:
        hexa = "0040F0"
    try:
        return tuple(int(hexa[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return (0.0, 0.25, 0.94)


def linhas(pedido: dict, empresa: dict) -> dict:
    """O conteudo do orcamento, ja somado. Sem uma linha de PDF.

    `subtotal` e a soma dos itens; `total` e o que o cliente paga. Os dois
    aparecem no papel quando ha desconto, e so o total quando nao ha: uma
    linha de "desconto R$ 0,00" e ruido que faz o cliente procurar o que ela
    quer dizer.
    """
    itens = []
    for i in pedido.get("itens") or []:
        qtd = i.get("quantidade") or 1
        unit = i.get("valor_unit") or 0
        itens.append({
            "descricao": i.get("descricao") or "",
            "cor": i.get("cor") or "",
            "quantidade": qtd,
            "valor_unit": unit,
            "total": round(qtd * unit, 2),
        })
    subtotal = round(sum(i["total"] for i in itens), 2)
    desconto = round(pedido.get("desconto") or 0, 2)
    return {
        "numero": pedido.get("id"),
        "cliente": pedido.get("cliente") or "",
        "itens": itens,
        "subtotal": subtotal,
        "desconto": desconto,
        # A MESMA funcao do painel e da tela de pedidos.
        "total": dados.total_do_pedido(pedido),
        "prazo": pedido.get("prazo"),
        "vale_ate": pedido.get("token_expira"),
        "aceito_em": pedido.get("aceito_em"),
        "aceito_por": pedido.get("aceito_por"),
        "observacao": pedido.get("observacao") or "",
        "condicoes": (empresa or {}).get("condicoes") or "",
    }


def _cabecalho(c, emp, cor, y: float) -> float:
    """A marca e quem assina. Devolve onde o conteudo pode comecar."""
    c.setFillColorRGB(*cor)
    c.rect(0, A4[1] - 8, A4[0], 8, stroke=0, fill=1)     # a faixa da cor

    if os.path.exists(ICONE):
        try:
            from reportlab.lib.utils import ImageReader
            c.drawImage(ImageReader(ICONE), MARGEM, y - 34, width=34, height=34,
                        mask="auto")
        except Exception:
            pass          # sem icone o documento continua valendo

    # A marca escrita, como no cabecalho do sistema: "3" laranja, "D" azul.
    x = MARGEM + 44
    c.setFont("Helvetica-Bold", 17)
    c.setFillColorRGB(*GRAFITE)
    nome = emp.get("nome") or "Morumbi 3D"
    c.drawString(x, y - 14, nome)

    c.setFont("Helvetica", 8.5)
    c.setFillColorRGB(*SUAVE)
    contato = " · ".join(p for p in (emp.get("documento"), emp.get("telefone"),
                                     emp.get("email"), emp.get("site")) if p)
    if contato:
        c.drawString(x, y - 27, contato[:110])
    if emp.get("endereco"):
        c.drawString(x, y - 37, emp["endereco"][:110])
    return y - 52


def _tabela(c, dados_, cor, y: float) -> float:
    largura = A4[0] - MARGEM * 2
    col_qtd, col_unit, col_total = MARGEM + largura - 200, MARGEM + largura - 120, MARGEM + largura

    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColorRGB(*SUAVE)
    c.drawString(MARGEM, y, "ITEM")
    c.drawRightString(col_qtd, y, "QTD")
    c.drawRightString(col_unit, y, "UNITÁRIO")
    c.drawRightString(col_total, y, "TOTAL")
    y -= 6
    c.setStrokeColorRGB(*cor)
    c.setLineWidth(1)
    c.line(MARGEM, y, MARGEM + largura, y)
    y -= 16

    for item in dados_["itens"]:
        c.setFont("Helvetica", 10)
        c.setFillColorRGB(*GRAFITE)
        c.drawString(MARGEM, y, item["descricao"][:56])
        if item["cor"]:
            c.setFont("Helvetica", 8.5)
            c.setFillColorRGB(*SUAVE)
            c.drawString(MARGEM + 6, y - 11, item["cor"])
        c.setFont("Helvetica", 10)
        c.setFillColorRGB(*GRAFITE)
        c.drawRightString(col_qtd, y, formato.numero(item["quantidade"], 0))
        c.drawRightString(col_unit, y, formato.dinheiro(item["valor_unit"]))
        c.drawRightString(col_total, y, formato.dinheiro(item["total"]))
        y -= 26 if item["cor"] else 20
        c.setStrokeColorRGB(*LINHA)
        c.setLineWidth(0.5)
        c.line(MARGEM, y + 8, MARGEM + largura, y + 8)
    return y


def _totais(c, dados_, cor, y: float) -> float:
    largura = A4[0] - MARGEM * 2
    direita = MARGEM + largura
    rotulo = direita - 120

    # Subtotal e desconto so aparecem quando HA desconto: "desconto R$ 0,00"
    # e ruido que faz o cliente procurar o que a linha quer dizer.
    if dados_["desconto"]:
        for nome, texto in (("Subtotal", formato.dinheiro(dados_["subtotal"])),
                            ("Desconto", "- " + formato.dinheiro(dados_["desconto"]))):
            c.setFont("Helvetica", 10)
            c.setFillColorRGB(*SUAVE)
            c.drawRightString(rotulo, y, nome)
            c.setFillColorRGB(*GRAFITE)
            c.drawRightString(direita, y, texto)
            y -= 16
        y -= 2

    c.setFont("Helvetica-Bold", 11)
    c.setFillColorRGB(*SUAVE)
    c.drawRightString(rotulo, y, "TOTAL")
    c.setFont("Helvetica-Bold", 16)
    c.setFillColorRGB(*cor)
    c.drawRightString(direita, y - 3, formato.dinheiro(dados_["total"]))
    return y - 24


def _texto_quebrado(c, texto: str, x: float, y: float, largura: float,
                    tamanho: float = 9) -> float:
    """Quebra por largura MEDIDA, e nao por contagem de letras.

    "iii" e "MMM" tem trinta letras iguais e larguras muito diferentes; contar
    letra estoura a margem em nome com muitas maiusculas.
    """
    c.setFont("Helvetica", tamanho)
    linha = ""
    for palavra in texto.split():
        tentativa = f"{linha} {palavra}".strip()
        if c.stringWidth(tentativa, "Helvetica", tamanho) > largura and linha:
            c.drawString(x, y, linha)
            y -= tamanho + 3
            linha = palavra
        else:
            linha = tentativa
    if linha:
        c.drawString(x, y, linha)
        y -= tamanho + 3
    return y


def desenhar(pedido: dict, empresa: dict, link: str = "") -> bytes:
    """O PDF, em bytes. Nao grava arquivo: quem grava e quem chamou."""
    from reportlab.pdfgen import canvas

    d = linhas(pedido, empresa)
    cor = _cor(empresa.get("cor"))
    buffer = io.BytesIO()
    # Sem compressao: o arquivo de uma pagina fica em uns 6 KB de qualquer
    # jeito, e assim o teste consegue procurar o total DENTRO do PDF, que e o
    # unico jeito de provar que o numero chegou no papel.
    c = canvas.Canvas(buffer, pagesize=A4, pageCompression=0)
    c.setTitle(f"Orçamento {d['numero']} — {empresa.get('nome') or 'Morumbi 3D'}")
    c.setAuthor(empresa.get("nome") or "Morumbi 3D")

    largura = A4[0] - MARGEM * 2
    y = _cabecalho(c, empresa, cor, A4[1] - MARGEM)

    # -------- numero e datas
    c.setFont("Helvetica-Bold", 22)
    c.setFillColorRGB(*GRAFITE)
    c.drawString(MARGEM, y - 18, "Orçamento")
    c.setFont("Helvetica-Bold", 22)
    c.setFillColorRGB(*cor)
    c.drawRightString(MARGEM + largura, y - 18, f"nº {d['numero']}")
    y -= 44

    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColorRGB(*SUAVE)
    c.drawString(MARGEM, y, "PARA")
    if d["prazo"]:
        c.drawRightString(MARGEM + largura, y, "ENTREGA")
    y -= 15
    c.setFont("Helvetica-Bold", 13)
    c.setFillColorRGB(*GRAFITE)
    c.drawString(MARGEM, y, d["cliente"][:52])
    if d["prazo"]:
        c.drawRightString(MARGEM + largura, y, formato.data(d["prazo"]))
    y -= 30

    y = _tabela(c, d, cor, y)
    y = _totais(c, d, cor, y - 12)

    # -------- rodape: o que vale, ate quando, e como aceitar
    y -= 10
    if d["observacao"]:
        c.setFillColorRGB(*SUAVE)
        y = _texto_quebrado(c, d["observacao"], MARGEM, y, largura)
        y -= 6
    if d["condicoes"]:
        c.setFillColorRGB(*SUAVE)
        y = _texto_quebrado(c, d["condicoes"], MARGEM, y, largura)
        y -= 6

    if d["aceito_em"]:
        c.setFillColorRGB(*cor)
        c.setFont("Helvetica-Bold", 10)
        quem = f" por {d['aceito_por']}" if d["aceito_por"] else ""
        c.drawString(MARGEM, y, f"Aceito em {formato.datahora(d['aceito_em'])}{quem}.")
        y -= 18
    elif d["vale_ate"]:
        c.setFillColorRGB(*GRAFITE)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(MARGEM, y, f"Este orçamento vale até {formato.data(d['vale_ate'])}.")
        y -= 18

    if link and not d["aceito_em"]:
        c.setFillColorRGB(*SUAVE)
        c.setFont("Helvetica", 9)
        c.drawString(MARGEM, y, "Para aceitar, abra:")
        c.setFillColorRGB(*cor)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(MARGEM + 92, y, link)
        # Clicavel no telefone, que e onde ele vai ser aberto.
        c.linkURL(link, (MARGEM + 92, y - 3, MARGEM + 92 + c.stringWidth(
            link, "Helvetica-Bold", 9), y + 10), relative=0)

    c.setFont("Helvetica", 7.5)
    c.setFillColorRGB(*SUAVE)
    c.drawString(MARGEM, MARGEM - 14,
                 f"{empresa.get('nome') or 'Morumbi 3D'} · gerado em "
                 f"{formato.data(formato.hoje())}")
    c.showPage()
    c.save()
    return buffer.getvalue()


def nome_do_arquivo(pedido: dict) -> str:
    """`Orcamento-12-Ana-Paula.pdf` -- o cliente acha no telefone depois."""
    cliente = formato.sem_acento_simples(pedido.get("cliente") or "")
    cliente = "-".join(cliente.split())[:28].strip("-")
    return f"Orcamento-{pedido.get('id')}{'-' + cliente if cliente else ''}.pdf"
