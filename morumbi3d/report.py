"""Relatorio de curadoria e exportacao.

Gera uma pagina HTML com miniatura, licenca, imprimibilidade e custo lado a
lado — a tela onde se decide rapido o que vale testar (secao 3.6) — e um CSV
no formato do Projeto 30 Produtos.

A pagina e offline: CSS e JS embutidos, imagens copiadas do cache local.
"""

from __future__ import annotations

import csv
import html
import json
import shutil
from datetime import datetime
from pathlib import Path

from .config import Config
from .db import Catalogo

_CSS = """
:root{--tinta:#12212e;--papel:#f7f5f1;--cartao:#fff;--borda:#e3ded6;
--verde:#1f7a4d;--verde-bg:#e7f4ec;--vermelho:#b3261e;--vermelho-bg:#fdecea;
--ambar:#8a5a00;--ambar-bg:#fdf3e0;--suave:#6b7a86}
*{box-sizing:border-box}
body{margin:0;background:var(--papel);color:var(--tinta);
font:15px/1.5 "IBM Plex Sans",-apple-system,Segoe UI,Roboto,sans-serif}
header{padding:28px 32px 12px;border-bottom:1px solid var(--borda);background:var(--cartao)}
h1{margin:0 0 4px;font-size:24px;letter-spacing:-.01em}
.sub{color:var(--suave);font-size:13px}
.barra{display:flex;gap:18px;flex-wrap:wrap;padding:14px 32px;background:var(--cartao);
border-bottom:1px solid var(--borda);position:sticky;top:0;z-index:5}
.barra label{font-size:12px;color:var(--suave);display:flex;gap:6px;align-items:center}
select,input[type=search]{font:inherit;font-size:13px;padding:6px 8px;border:1px solid var(--borda);
border-radius:6px;background:var(--papel)}
.metricas{display:flex;gap:10px;flex-wrap:wrap;padding:16px 32px 0}
.metrica{background:var(--cartao);border:1px solid var(--borda);border-radius:10px;
padding:10px 14px;min-width:120px}
.metrica b{display:block;font-size:22px;line-height:1.1}
.metrica span{font-size:11px;color:var(--suave);text-transform:uppercase;letter-spacing:.06em}
.grade{display:grid;gap:16px;padding:20px 32px 48px;
grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}
.cartao{background:var(--cartao);border:1px solid var(--borda);border-radius:12px;
overflow:hidden;display:flex;flex-direction:column}
.cartao.bloqueado{border-color:#f0c4c0;box-shadow:inset 3px 0 0 var(--vermelho)}
.cartao.duvida{box-shadow:inset 3px 0 0 var(--ambar)}
.cartao.livre{box-shadow:inset 3px 0 0 var(--verde)}
.miniatura{aspect-ratio:4/3;background:#ece7df;display:flex;align-items:center;
justify-content:center;color:var(--suave);font-size:12px;overflow:hidden}
.miniatura.vazia{aspect-ratio:auto;height:30px;font-size:11px;letter-spacing:.04em}
.miniatura img{width:100%;height:100%;object-fit:cover}
.corpo{padding:14px 16px 16px;display:flex;flex-direction:column;gap:10px;flex:1}
.titulo{font-weight:600;line-height:1.3}
.titulo a{color:inherit;text-decoration:none}
.titulo a:hover{text-decoration:underline}
.meta{font-size:12px;color:var(--suave)}
.selos{display:flex;gap:6px;flex-wrap:wrap}
.selo{font-size:11px;padding:3px 8px;border-radius:999px;font-weight:600;
letter-spacing:.02em;white-space:nowrap}
.selo.ok{background:var(--verde-bg);color:var(--verde)}
.selo.nao{background:var(--vermelho-bg);color:var(--vermelho)}
.selo.talvez{background:var(--ambar-bg);color:var(--ambar)}
.selo.neutro{background:#eef1f3;color:#41525e}
.dados{display:grid;grid-template-columns:1fr 1fr;gap:6px 12px;font-size:12px;
border-top:1px solid var(--borda);padding-top:10px;margin-top:auto}
.dados div span{color:var(--suave);display:block;font-size:10px;
text-transform:uppercase;letter-spacing:.05em}
.aviso{background:var(--vermelho-bg);color:var(--vermelho);font-size:12px;
padding:8px 10px;border-radius:8px;line-height:1.4}
.problemas{font-size:12px;color:var(--vermelho);margin:0;padding-left:16px}
.alertas{font-size:12px;color:var(--ambar);margin:0;padding-left:16px}
footer{padding:20px 32px 40px;color:var(--suave);font-size:12px;
border-top:1px solid var(--borda)}
.vazio{padding:60px 32px;text-align:center;color:var(--suave)}
"""

_JS = """
const cartoes = [...document.querySelectorAll('.cartao')];
const filtros = {linha:'', status:'', seguro:'', texto:''};
function aplicar(){
  let visiveis = 0;
  for (const c of cartoes){
    const d = c.dataset;
    const ok = (!filtros.linha || d.linha === filtros.linha)
      && (!filtros.status || d.status === filtros.status)
      && (!filtros.seguro || d.seguro === filtros.seguro)
      && (!filtros.texto || (d.busca||'').includes(filtros.texto));
    c.style.display = ok ? '' : 'none';
    visiveis += ok ? 1 : 0;
  }
  document.getElementById('contador').textContent = visiveis;
}
for (const campo of ['linha','status','seguro']){
  document.getElementById('f-'+campo).addEventListener('change', e => {
    filtros[campo] = e.target.value; aplicar();
  });
}
document.getElementById('f-texto').addEventListener('input', e => {
  filtros.texto = e.target.value.toLowerCase(); aplicar();
});
"""


def montar_itens(
    catalogo: Catalogo, **filtros
) -> list[dict]:
    """Junta modelo + ultima analise + orcamento num dicionario por item."""

    itens = []
    for linha in catalogo.listar(**filtros):
        item = dict(linha)
        item["tags"] = json.loads(item.get("tags") or "[]")
        item["licenca_obs"] = json.loads(item.get("licenca_obs") or "[]")
        item["risco_termos"] = json.loads(item.get("risco_termos") or "[]")
        analise = catalogo.ultima_analise(linha["id"])
        item["analise"] = json.loads(analise["relatorio"]) if analise else None
        item["orcamento"] = json.loads(analise["orcamento"]) if analise else None
        item["seguro"] = (
            item["licenca_comercial"] == "permitido" and item["risco_nivel"] == "nenhum"
        )
        itens.append(item)
    return itens


def _selo_licenca(item: dict) -> str:
    comercial = item["licenca_comercial"]
    classe = {"permitido": "ok", "proibido": "nao"}.get(comercial, "talvez")
    rotulo = {
        "permitido": "pode vender",
        "proibido": "nao pode vender",
    }.get(comercial, "licenca a conferir")
    nome = item.get("licenca_nome") or item.get("licenca_codigo") or "?"
    return (
        f'<span class="selo {classe}">{html.escape(rotulo)}</span>'
        f'<span class="selo neutro">{html.escape(nome)}</span>'
    )


def _cartao(item: dict, pasta_assets: Path) -> str:
    analise = item.get("analise") or {}
    orcamento = item.get("orcamento") or {}
    if item["risco_nivel"] != "nenhum":
        classe = "bloqueado"
    elif item["licenca_comercial"] == "permitido":
        classe = "livre"
    else:
        classe = "duvida"

    thumb = ""
    origem = item.get("thumb_local") or ""
    if origem and Path(origem).is_file():
        destino = pasta_assets / Path(origem).name
        try:
            if not destino.exists():
                shutil.copy2(origem, destino)
            thumb = f'<img src="assets/{html.escape(destino.name)}" alt="" loading="lazy">'
        except OSError:
            thumb = ""
    if not thumb and item.get("thumb_url"):
        thumb = f'<img src="{html.escape(item["thumb_url"])}" alt="" loading="lazy">'
    classe_thumb = "miniatura"
    if not thumb:
        # Sem imagem, a faixa vira um risco fino: o cartao nao desperdica
        # meia tela com um retangulo vazio.
        thumb, classe_thumb = "sem imagem de referencia", "miniatura vazia"

    dimensoes = analise.get("dimensoes_mm")
    dim_txt = (
        f"{dimensoes[0]:.0f}×{dimensoes[1]:.0f}×{dimensoes[2]:.0f} mm"
        if dimensoes
        else "—"
    )
    linhas_dados = [
        ("Dimensoes", dim_txt),
        ("Cabe na mesa", "sim" if analise.get("cabe_na_mesa", True) else "NAO" if analise else "—"),
        ("Malha", ("fechada" if analise.get("fechada") else "aberta") if analise else "—"),
        ("Suporte", analise.get("suporte", "—") if analise else "—"),
        ("Material", f"{analise.get('material_g', 0):.0f} g" if analise else "—"),
        ("Tempo", f"{analise.get('tempo_h', 0):.1f} h" if analise else "—"),
        ("Custo", f"R$ {orcamento.get('custo_total', 0):.2f}" if orcamento else "—"),
        ("Preco sugerido", f"R$ {orcamento.get('preco_sugerido', 0):.2f}" if orcamento else "—"),
    ]
    dados_html = "".join(
        f"<div><span>{html.escape(rotulo)}</span>{html.escape(str(valor))}</div>"
        for rotulo, valor in linhas_dados
    )

    aviso = ""
    if item["risco_mensagem"]:
        aviso = f'<div class="aviso">⚠ {html.escape(item["risco_mensagem"])}</div>'
    elif item["licenca_obs"]:
        aviso = (
            '<div class="meta">'
            + html.escape("; ".join(item["licenca_obs"]))
            + "</div>"
        )

    problemas = "".join(
        f"<li>{html.escape(p)}</li>" for p in (analise.get("problemas") or [])
    )
    alertas = "".join(
        f"<li>{html.escape(a)}</li>" for a in (analise.get("alertas") or [])
    )
    listas = ""
    if problemas:
        listas += f'<ul class="problemas">{problemas}</ul>'
    if alertas:
        listas += f'<ul class="alertas">{alertas}</ul>'

    nota = analise.get("nota")
    selo_nota = (
        f'<span class="selo {"ok" if nota >= 75 else "talvez" if nota >= 50 else "nao"}">'
        f"imprimibilidade {nota}/100</span>"
        if nota is not None
        else '<span class="selo neutro">sem analise</span>'
    )
    busca = " ".join(
        [item["titulo"], item.get("autor", ""), " ".join(item.get("tags", []))]
    ).lower()

    return f"""
    <article class="cartao {classe}" data-linha="{html.escape(item['linha'])}"
      data-status="{html.escape(item['status'])}"
      data-seguro="{'sim' if item['seguro'] else 'nao'}"
      data-busca="{html.escape(busca)}">
      <div class="{classe_thumb}">{thumb}</div>
      <div class="corpo">
        <div class="titulo"><a href="{html.escape(item['url'])}" target="_blank"
          rel="noopener noreferrer">#{item['id']} {html.escape(item['titulo'])}</a></div>
        <div class="meta">{html.escape(item['fonte'])}
          {'· ' + html.escape(item['autor']) if item.get('autor') else ''}
          · {html.escape(item['linha'])}{' / ' + html.escape(item['colecao']) if item.get('colecao') else ''}
          · <b>{html.escape(item['status'])}</b></div>
        <div class="selos">{_selo_licenca(item)}{selo_nota}</div>
        {aviso}
        {listas}
        <div class="dados">{dados_html}</div>
      </div>
    </article>"""


def gerar_html(
    cfg: Config,
    itens: list[dict],
    caminho: Path | str | None = None,
    titulo: str = "Curadoria de modelos 3D",
) -> Path:
    """Escreve o relatorio HTML e devolve o caminho."""

    cfg.preparar_diretorios()
    caminho = Path(caminho) if caminho else (
        cfg.relatorios / f"curadoria-{datetime.now():%Y%m%d-%H%M}.html"
    )
    caminho.parent.mkdir(parents=True, exist_ok=True)
    assets = caminho.parent / "assets"
    assets.mkdir(exist_ok=True)

    seguros = sum(1 for i in itens if i["seguro"])
    bloqueados = sum(1 for i in itens if i["risco_nivel"] != "nenhum")
    analisados = sum(1 for i in itens if i.get("analise"))
    linhas = sorted({i["linha"] for i in itens})
    status = sorted({i["status"] for i in itens})

    opcoes_linha = "".join(f'<option value="{html.escape(l)}">{html.escape(l)}</option>' for l in linhas)
    opcoes_status = "".join(f'<option value="{html.escape(s)}">{html.escape(s)}</option>' for s in status)
    cartoes = "".join(_cartao(i, assets) for i in itens)
    if not cartoes:
        cartoes = '<p class="vazio">Nenhum modelo no filtro atual.</p>'

    documento = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(titulo)} — Morumbi 3D</title>
<style>{_CSS}</style>
</head>
<body>
<header>
  <h1>{html.escape(titulo)}</h1>
  <div class="sub">Morumbi 3D · gerado em {datetime.now():%d/%m/%Y %H:%M} ·
  <span id="contador">{len(itens)}</span> de {len(itens)} modelos visiveis</div>
</header>
<div class="metricas">
  <div class="metrica"><b>{len(itens)}</b><span>candidatos</span></div>
  <div class="metrica"><b>{seguros}</b><span>seguros p/ venda</span></div>
  <div class="metrica"><b>{bloqueados}</b><span>risco de marca</span></div>
  <div class="metrica"><b>{analisados}</b><span>com analise de malha</span></div>
</div>
<div class="barra">
  <label>Linha <select id="f-linha"><option value="">todas</option>{opcoes_linha}</select></label>
  <label>Status <select id="f-status"><option value="">todos</option>{opcoes_status}</select></label>
  <label>Venda <select id="f-seguro"><option value="">tudo</option>
    <option value="sim">so seguros</option><option value="nao">so bloqueados</option></select></label>
  <label>Busca <input id="f-texto" type="search" placeholder="titulo, autor, tag"></label>
</div>
<div class="grade">{cartoes}</div>
<footer>
  Licenca e propriedade intelectual conferidas automaticamente: use como
  triagem, nao como parecer juridico. Nenhum modelo com risco de marca ou
  licenca desconhecida deve ir para venda sem checagem manual.
</footer>
<script>{_JS}</script>
</body>
</html>
"""
    caminho.write_text(documento, encoding="utf-8")
    return caminho


COLUNAS_CSV = [
    "id", "titulo", "linha", "colecao", "status", "fonte", "autor", "url",
    "licenca", "uso_comercial", "risco_marca", "risco_termos",
    "dimensoes_mm", "cabe_na_mesa", "malha_fechada", "partes_soltas",
    "suporte", "nota_imprimibilidade", "material_g", "tempo_h",
    "custo_total", "preco_sugerido", "motivo",
]


def exportar_csv(itens: list[dict], caminho: Path | str) -> Path:
    """CSV no formato do Projeto 30 Produtos."""

    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", newline="", encoding="utf-8-sig") as fh:
        escritor = csv.DictWriter(fh, fieldnames=COLUNAS_CSV, delimiter=";")
        escritor.writeheader()
        for item in itens:
            analise = item.get("analise") or {}
            orcamento = item.get("orcamento") or {}
            dim = analise.get("dimensoes_mm")
            escritor.writerow(
                {
                    "id": item["id"],
                    "titulo": item["titulo"],
                    "linha": item["linha"],
                    "colecao": item["colecao"],
                    "status": item["status"],
                    "fonte": item["fonte"],
                    "autor": item["autor"],
                    "url": item["url"],
                    "licenca": item["licenca_nome"] or item["licenca_codigo"],
                    "uso_comercial": item["licenca_comercial"],
                    "risco_marca": item["risco_nivel"],
                    "risco_termos": ", ".join(t[0] for t in item.get("risco_termos", [])),
                    "dimensoes_mm": (
                        f"{dim[0]:.1f}x{dim[1]:.1f}x{dim[2]:.1f}" if dim else ""
                    ),
                    "cabe_na_mesa": (
                        ("sim" if analise["cabe_na_mesa"] else "nao")
                        if "cabe_na_mesa" in analise
                        else ""
                    ),
                    "malha_fechada": (
                        ("sim" if analise["fechada"] else "nao")
                        if "fechada" in analise
                        else ""
                    ),
                    "partes_soltas": analise.get("partes_soltas", ""),
                    "suporte": analise.get("suporte", ""),
                    "nota_imprimibilidade": analise.get("nota", ""),
                    "material_g": analise.get("material_g", ""),
                    "tempo_h": analise.get("tempo_h", ""),
                    "custo_total": orcamento.get("custo_total", ""),
                    "preco_sugerido": orcamento.get("preco_sugerido", ""),
                    "motivo": item.get("motivo", ""),
                }
            )
    return caminho
