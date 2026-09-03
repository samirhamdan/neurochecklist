"""Interface de linha de comando.

    morumbi3d fontes
    morumbi3d buscar "churrasqueira" --so-comercial --imagens
    morumbi3d catalogo --linha Adultos --status novo
    morumbi3d analisar arquivo.stl
    morumbi3d analisar --modelo 12 --arquivo ~/Downloads/modelo.stl
    morumbi3d aprovar 12 --motivo "testar em preto"
    morumbi3d relatorio --so-seguros
    morumbi3d exportar --saida projeto30.csv
    morumbi3d letra logo.svg --altura 300 --profundidade 30 --chanfro 1.5
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import __version__
from .config import Config, carregar_config
from .db import Catalogo
from .licensing import motivo_bloqueio
from .mesh import ArquivoInvalido, analisar_arquivo
from .models import (
    STATUS_APROVADO, STATUS_PRODUCAO, STATUS_REPROVADO, STATUS_VALIDOS,
)
from .net import SessaoEducada
from .pricing import orcar
from .report import exportar_csv, gerar_html, montar_itens
from .search import buscar as executar_busca
from .sources import instanciar

_CORES = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _cor(texto: str, codigo: str) -> str:
    return f"\033[{codigo}m{texto}\033[0m" if _CORES else texto


def verde(t: str) -> str:
    return _cor(t, "32")


def vermelho(t: str) -> str:
    return _cor(t, "31")


def amarelo(t: str) -> str:
    return _cor(t, "33")


def cinza(t: str) -> str:
    return _cor(t, "90")


def negrito(t: str) -> str:
    return _cor(t, "1")


def _marca_licenca(comercial: str, risco: str) -> str:
    if risco != "nenhum":
        return vermelho("[MARCA]")
    return {
        "permitido": verde("[vende]"),
        "proibido": vermelho("[nao vende]"),
    }.get(comercial, amarelo("[conferir]"))


# ---------------------------------------------------------------- comandos


def cmd_init(args, cfg: Config) -> int:
    cfg.preparar_diretorios()
    destino = Path(args.saida) if args.saida else Path.cwd() / "morumbi3d.toml"
    if destino.exists() and not args.forcar:
        print(f"{destino} ja existe (use --forcar para sobrescrever)")
        return 1
    destino.write_text(MODELO_TOML, encoding="utf-8")
    print(f"Dados em:        {cfg.raiz}")
    print(f"Banco:           {cfg.banco}")
    print(f"Configuracao em: {destino}")
    print("\nProximos passos:")
    print("  1. edite morumbi3d.toml (custos reais e fontes a ligar)")
    print("  2. export MORUMBI3D_CONTATO='seu-email@exemplo.com'")
    print("  3. export THINGIVERSE_TOKEN='...'  (opcional, libera o Thingiverse)")
    print("  4. morumbi3d fontes")
    return 0


def cmd_fontes(args, cfg: Config) -> int:
    sessao = SessaoEducada(cfg)
    print(negrito(f"{'fonte':<13}{'estado':<8}{'acesso':<28}motivo"))
    for conector in instanciar(cfg, sessao):
        ok, motivo = conector.disponivel()
        # A cor entra depois do alinhamento: codigos ANSI contam como
        # caracteres e desalinhariam a coluna.
        estado = (verde if ok else cinza)(f"{'ligada' if ok else 'off':<8}")
        print(f"{conector.id:<13}{estado}{conector.acesso:<28}{motivo}")
    print()
    print(cinza("Fontes sem API publica ficam desligadas ate voce ligar em"))
    print(cinza("morumbi3d.toml, depois de conferir os termos de uso do site."))
    return 0


def cmd_buscar(args, cfg: Config) -> int:
    with Catalogo(cfg) as catalogo:
        resultado = executar_busca(
            cfg,
            args.termo,
            limite_por_fonte=args.limite,
            fontes=args.fontes,
            traduzir=not args.sem_traduzir,
            so_comercial=args.so_comercial,
            so_gratuitos=args.so_gratuitos,
            com_imagem=args.com_imagem,
            formato=args.formato,
            catalogo=catalogo,
            baixar_imagens=args.imagens,
        )

        print(negrito(f'Busca: "{args.termo}"'))
        print(cinza(f"Variantes: {', '.join(resultado.variantes)}"))
        for fonte, motivo in resultado.fontes_ignoradas:
            print(cinza(f"  - {fonte} ignorada: {motivo}"))
        for erro in resultado.erros:
            print(amarelo(f"  ! {erro}"))
        print()

        for achado in resultado.achados:
            c = achado.candidato
            marca = _marca_licenca(achado.licenca.comercial, achado.risco.nivel)
            novo = verde("NOVO") if achado.novo else cinza("já visto")
            print(f"#{achado.modelo_id or '-'} {marca} {negrito(c.titulo[:70])}")
            print(
                cinza(
                    f"     {c.fonte} · {c.autor or 'autor ?'} · "
                    f"{achado.linha}/{achado.colecao or '-'} · {novo}"
                )
            )
            print(cinza(f"     {c.url}"))
            bloqueio = motivo_bloqueio(achado.licenca, achado.risco)
            if bloqueio:
                print(f"     {amarelo(bloqueio[:110])}")
        print()
        print(resultado.resumo())
        if resultado.descartados_filtro:
            print(cinza(f"{resultado.descartados_filtro} descartados pelos filtros"))
    return 0


def cmd_catalogo(args, cfg: Config) -> int:
    with Catalogo(cfg) as catalogo:
        linhas = catalogo.listar(
            status=args.status,
            linha=args.linha,
            colecao=args.colecao,
            texto=args.texto,
            fonte=args.fonte,
            so_seguros=args.so_seguros,
            limite=args.limite,
            ordem=args.ordem,
        )
        if not linhas:
            print("Nada no catalogo com esses filtros.")
            return 0
        for r in linhas:
            marca = _marca_licenca(r["licenca_comercial"], r["risco_nivel"])
            analise = catalogo.ultima_analise(r["id"])
            nota = f"nota {analise['nota']}/100" if analise else "sem analise"
            print(f"#{r['id']:<5} {marca} {negrito(r['titulo'][:60])}")
            print(
                cinza(
                    f"       {r['status']} · {r['fonte']} · {r['linha']}"
                    f"{'/' + r['colecao'] if r['colecao'] else ''} · {nota}"
                )
            )
        print()
        print(cinza(f"{len(linhas)} modelo(s)"))
    return 0


def cmd_ver(args, cfg: Config) -> int:
    with Catalogo(cfg) as catalogo:
        r = catalogo.obter(args.id)
        if not r:
            print(vermelho(f"modelo #{args.id} nao encontrado"))
            return 1
        print(negrito(f"#{r['id']} {r['titulo']}"))
        print(f"  fonte     : {r['fonte']} ({r['fonte_id']})")
        print(f"  autor     : {r['autor'] or '?'}")
        print(f"  url       : {r['url']}")
        print(f"  linha     : {r['linha']}{'/' + r['colecao'] if r['colecao'] else ''}")
        print(f"  status    : {r['status']}{' — ' + r['motivo'] if r['motivo'] else ''}")
        print(
            f"  licenca   : {r['licenca_nome']} ({r['licenca_codigo']}) — "
            f"uso comercial {r['licenca_comercial']}"
        )
        if r["risco_nivel"] != "nenhum":
            print(vermelho(f"  RISCO     : {r['risco_mensagem']}"))
        if r["duplicado_de"]:
            print(amarelo(f"  duplicado de #{r['duplicado_de']}"))
        analise = catalogo.ultima_analise(r["id"])
        if analise:
            import json

            rel = json.loads(analise["relatorio"])
            orc = json.loads(analise["orcamento"] or "{}")
            print(f"  arquivo   : {analise['arquivo']}")
            print(f"  malha     : {'fechada' if rel['fechada'] else 'ABERTA'}, "
                  f"{rel['partes_soltas']} parte(s), nota {rel['nota']}/100")
            d = rel["dimensoes_mm"]
            print(f"  dimensoes : {d[0]:.1f} x {d[1]:.1f} x {d[2]:.1f} mm "
                  f"({'cabe' if rel['cabe_na_mesa'] else 'NAO CABE'} na mesa)")
            print(f"  suporte   : {rel['suporte']} ({rel['balanco_ratio'] * 100:.0f}% em balanco)")
            print(f"  material  : {rel['material_g']:.0f} g · {rel['tempo_h']:.1f} h")
            if orc:
                print(f"  custo     : R$ {orc['custo_total']:.2f} · "
                      f"preco sugerido R$ {orc['preco_sugerido']:.2f}")
            for p in rel["problemas"]:
                print(vermelho(f"  ! {p}"))
            for a in rel["alertas"]:
                print(amarelo(f"  · {a}"))
        else:
            print(cinza("  (sem analise de malha — rode `morumbi3d analisar`)"))
    return 0


def cmd_analisar(args, cfg: Config) -> int:
    informado = args.arquivo or args.arquivo_opcao
    caminho = Path(informado) if informado else None

    if args.modelo and caminho is None:
        with Catalogo(cfg) as catalogo:
            r = catalogo.obter(args.modelo)
            if not r:
                print(vermelho(f"modelo #{args.modelo} nao encontrado"))
                return 1
            if r["arquivo_local"] and Path(r["arquivo_local"]).is_file():
                caminho = Path(r["arquivo_local"])
            elif r["arquivo_url"]:
                sessao = SessaoEducada(cfg)
                destino = cfg.cache_arquivos / f"{r['fonte']}-{r['id']}{Path(r['arquivo_url']).suffix or '.bin'}"
                print(cinza(f"baixando {r['arquivo_url']} ..."))
                try:
                    caminho = sessao.baixar(r["arquivo_url"], destino)
                except Exception as exc:
                    print(vermelho(f"download falhou: {exc}"))
                    return 1
            else:
                print(
                    amarelo(
                        "Esta fonte nao oferece link direto de download.\n"
                        f"Baixe o arquivo em {r['url']} e rode:\n"
                        f"  morumbi3d analisar --modelo {r['id']} --arquivo CAMINHO.stl"
                    )
                )
                return 1

    if caminho is None:
        print(vermelho("informe um arquivo ou --modelo ID"))
        return 1

    try:
        relatorio = analisar_arquivo(caminho, cfg)
    except ArquivoInvalido as exc:
        print(vermelho(f"nao foi possivel analisar {caminho}: {exc}"))
        return 1

    orcamento = orcar(relatorio, cfg, quantidade=args.quantidade)
    d = relatorio.dimensoes_mm
    print(negrito(f"{caminho}"))
    print(f"  triangulos: {relatorio.triangulos} · vertices {relatorio.vertices_unicos}")
    print(f"  dimensoes : {d[0]:.1f} x {d[1]:.1f} x {d[2]:.1f} mm · volume "
          f"{relatorio.volume_cm3:.1f} cm3")
    print(f"  malha     : {'fechada' if relatorio.fechada else vermelho('ABERTA')} · "
          f"{relatorio.partes_soltas} parte(s)")
    print(f"  mesa      : {'cabe' if relatorio.cabe_na_mesa else vermelho('nao cabe')}")
    print(f"  suporte   : {relatorio.suporte} ({relatorio.balanco_ratio * 100:.0f}% em balanco)")
    print(f"  estimativa: {relatorio.material_g:.0f} g · {relatorio.tempo_h:.1f} h")
    print(f"  {orcamento.resumo()}")
    print(f"  nota      : {relatorio.nota}/100")
    for p in relatorio.problemas:
        print(vermelho(f"  ! {p}"))
    for a in relatorio.alertas:
        print(amarelo(f"  · {a}"))
    if relatorio.conferencia_trimesh:
        print(cinza(f"  trimesh   : {relatorio.conferencia_trimesh}"))

    if args.modelo:
        with Catalogo(cfg) as catalogo:
            catalogo.salvar_analise(args.modelo, relatorio, orcamento, str(caminho))
        print(cinza(f"  analise salva no modelo #{args.modelo}"))
    return 0


def _mudar(args, cfg: Config, status: str) -> int:
    with Catalogo(cfg) as catalogo:
        r = catalogo.obter(args.id)
        if not r:
            print(vermelho(f"modelo #{args.id} nao encontrado"))
            return 1
        if status in (STATUS_APROVADO, STATUS_PRODUCAO):
            bloqueio = ""
            if r["risco_nivel"] != "nenhum":
                bloqueio = r["risco_mensagem"]
            elif r["licenca_comercial"] != "permitido":
                bloqueio = (
                    f"licenca {r['licenca_nome']} — uso comercial "
                    f"{r['licenca_comercial']}"
                )
            if bloqueio and not args.mesmo_assim:
                print(vermelho(f"BLOQUEADO: {bloqueio}"))
                print(
                    "Confira a licenca na pagina do modelo. Se estiver liberado, "
                    "repita com --mesmo-assim e registre o motivo em --motivo."
                )
                return 2
            if bloqueio:
                print(amarelo(f"aviso ignorado por --mesmo-assim: {bloqueio}"))
        catalogo.mudar_status(args.id, status, args.motivo)
        print(f"#{args.id} {r['titulo'][:60]} -> {negrito(status)}")
    return 0


def cmd_aprovar(args, cfg: Config) -> int:
    return _mudar(args, cfg, STATUS_APROVADO)


def cmd_reprovar(args, cfg: Config) -> int:
    return _mudar(args, cfg, STATUS_REPROVADO)


def cmd_producao(args, cfg: Config) -> int:
    return _mudar(args, cfg, STATUS_PRODUCAO)


def cmd_relatorio(args, cfg: Config) -> int:
    with Catalogo(cfg) as catalogo:
        itens = montar_itens(
            catalogo,
            status=args.status,
            linha=args.linha,
            so_seguros=args.so_seguros,
            limite=args.limite,
        )
        caminho = gerar_html(cfg, itens, args.saida, titulo=args.titulo)
    print(f"Relatorio com {len(itens)} modelo(s): {caminho}")
    return 0


def cmd_exportar(args, cfg: Config) -> int:
    with Catalogo(cfg) as catalogo:
        itens = montar_itens(
            catalogo,
            status=args.status,
            linha=args.linha,
            so_seguros=args.so_seguros,
            limite=args.limite,
        )
        caminho = exportar_csv(itens, args.saida)
    print(f"{len(itens)} linha(s) exportada(s) para {caminho}")
    return 0


def _ler_furos(texto: str | None) -> list[tuple[float, float]]:
    """Aceita "x,y;x,y" ou "x,y x,y"."""

    if not texto:
        return []
    pontos = []
    for parte in texto.replace(";", " ").split():
        try:
            x, y = parte.split(",")
            pontos.append((float(x), float(y)))
        except ValueError:
            raise SystemExit(f"furo invalido: {parte!r} (use x,y)")
    return pontos


def cmd_letra(args, cfg: Config) -> int:
    from .letras import GeometriaInvalida, gerar_de_svg

    try:
        resultado = gerar_de_svg(
            args.svg,
            cfg,
            altura=args.altura,
            profundidade=args.profundidade,
            parede=args.parede,
            frente=args.frente,
            chanfro=args.chanfro,
            macica=args.macica,
            furos=_ler_furos(args.furos),
            furos_auto=args.furos_auto,
            diametro_furo=args.furo_diametro,
            espacamento_furo=args.furo_espacamento,
            cortar_para_mesa=not args.sem_cortar,
            tolerancia=args.tolerancia,
            saida=args.saida,
            nome=args.nome,
        )
    except (GeometriaInvalida, FileNotFoundError, ValueError) as exc:
        print(vermelho(f"nao foi possivel gerar: {exc}"))
        return 1

    print(negrito(resultado.resumo()))
    tipo = "macica" if resultado.macica else f"caixa (parede {args.parede} mm)"
    print(cinza(f"  {tipo} · {len(resultado.furos)} furo(s) de fixacao"))
    print()
    for pedaco in resultado.pedacos:
        rel = pedaco.relatorio
        estado = verde("fechada") if rel.fechada else vermelho("ABERTA")
        d = rel.dimensoes_mm
        print(f"  {negrito(pedaco.nome)}  {pedaco.arquivo}")
        print(
            cinza(
                f"     {d[0]:.0f} x {d[1]:.0f} x {d[2]:.0f} mm · {estado} · "
                f"{rel.triangulos} triangulos · "
                f"{'cabe na mesa' if rel.cabe_na_mesa else vermelho('NAO CABE')}"
            )
        )
        print(
            cinza(
                f"     ~{rel.material_g:.0f} g · ~{rel.tempo_h:.1f} h · "
                f"custo R$ {pedaco.orcamento.custo_total:.2f} · "
                f"preco R$ {pedaco.orcamento.preco_sugerido:.2f}"
            )
        )
    print()
    print(
        f"  Total: {resultado.material_g:.0f} g · {resultado.tempo_h:.1f} h · "
        f"custo R$ {resultado.custo:.2f} · "
        f"preco sugerido R$ {resultado.preco_sugerido:.2f}"
    )
    for aviso in resultado.avisos:
        print(amarelo(f"  ! {aviso}"))
    if not resultado.tudo_fechado:
        print(vermelho("  Alguma peca saiu aberta: confira no fatiador."))
        return 1
    return 0


def cmd_stats(args, cfg: Config) -> int:
    with Catalogo(cfg) as catalogo:
        e = catalogo.estatisticas()
    print(negrito("Catalogo Morumbi 3D"))
    print(f"  total            : {e['total']}")
    for status, n in sorted(e["por_status"].items()):
        print(f"    {status:<14}: {n}")
    print(f"  seguros p/ venda : {verde(str(e['seguros_para_venda']))}")
    print(f"  bloqueados       : {vermelho(str(e['bloqueados']))}")
    print(f"  duplicados       : {e['duplicados']}")
    if e["por_linha"]:
        print("  por linha:")
        for linha, n in e["por_linha"].items():
            print(f"    {linha:<20}: {n}")
    if e["por_fonte"]:
        print("  por fonte:")
        for fonte, n in e["por_fonte"].items():
            print(f"    {fonte:<20}: {n}")
    return 0


MODELO_TOML = """# Configuracao do sistema de curadoria — Morumbi 3D
# Ajuste os numeros com os dados reais da operacao antes de usar a
# precificacao para decidir preco de venda.

[impressora]
nome = "Bambu Lab A1 / A2L"
mesa_x_mm = 256.0
mesa_y_mm = 256.0
altura_max_mm = 256.0
altura_camada_mm = 0.24
preenchimento = 0.08
vazao_cm3_por_hora = 12.0

[custo]
preco_filamento_kg = 120.0
custo_hora_maquina = 3.50
taxa_falha = 0.10
custo_fixo_por_peca = 1.50
multiplicador_margem = 3.0

[rede]
# Identifique-se: e o minimo de educacao com os servidores das fontes.
contato = ""
intervalo_min_s = 3.0
respeitar_robots = true

[fontes]
# Fontes sem API publica documentada: ligue SO depois de conferir os
# termos de uso do site.
thingiverse = true
github = true
printables = false
makerworld = false
thangs = false
cults3d = false
"""


def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="morumbi3d",
        description="Busca e curadoria de modelos 3D prontos — Morumbi 3D",
    )
    p.add_argument("--version", action="version", version=f"morumbi3d {__version__}")
    p.add_argument("--config", help="caminho do morumbi3d.toml")
    sub = p.add_subparsers(dest="comando", required=True)

    s = sub.add_parser("init", help="cria a configuracao e as pastas de dados")
    s.add_argument("--saida", help="onde escrever o morumbi3d.toml")
    s.add_argument("--forcar", action="store_true")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("fontes", help="lista as fontes e o estado de cada uma")
    s.set_defaults(func=cmd_fontes)

    s = sub.add_parser("buscar", help="busca em todas as fontes ligadas")
    s.add_argument("termo")
    s.add_argument("--limite", type=int, default=20, help="resultados por fonte")
    s.add_argument("--fontes", nargs="+", help="restringe a estas fontes")
    s.add_argument("--sem-traduzir", action="store_true", help="nao expande PT->EN")
    s.add_argument("--so-comercial", action="store_true", help="so o que pode vender")
    s.add_argument("--so-gratuitos", action="store_true")
    s.add_argument("--com-imagem", action="store_true", help="so com imagem de referencia")
    s.add_argument("--formato", choices=["stl", "3mf"], help="formato disponivel")
    s.add_argument("--imagens", action="store_true", help="baixa as miniaturas")
    s.set_defaults(func=cmd_buscar)

    s = sub.add_parser("catalogo", help="consulta o banco local")
    s.add_argument("--status", choices=list(STATUS_VALIDOS))
    s.add_argument("--linha")
    s.add_argument("--colecao")
    s.add_argument("--fonte")
    s.add_argument("--texto", help="busca por titulo/descricao/tag")
    s.add_argument("--so-seguros", action="store_true")
    s.add_argument("--limite", type=int, default=30)
    s.add_argument("--ordem", choices=["recentes", "titulo", "populares"], default="recentes")
    s.set_defaults(func=cmd_catalogo)

    s = sub.add_parser("ver", help="detalha um modelo")
    s.add_argument("id", type=int)
    s.set_defaults(func=cmd_ver)

    s = sub.add_parser("analisar", help="analisa a imprimibilidade de um arquivo")
    s.add_argument("arquivo", nargs="?", help="STL, 3MF ou OBJ")
    s.add_argument(
        "--arquivo",
        dest="arquivo_opcao",
        help="mesmo que o argumento posicional (util junto de --modelo)",
    )
    s.add_argument("--modelo", type=int, help="id no catalogo (salva a analise)")
    s.add_argument("--quantidade", type=int, default=1)
    s.set_defaults(func=cmd_analisar)

    for nome, funcao, ajuda in (
        ("aprovar", cmd_aprovar, "marca como aprovado"),
        ("reprovar", cmd_reprovar, "marca como reprovado"),
        ("producao", cmd_producao, "marca como ja em producao"),
    ):
        s = sub.add_parser(nome, help=ajuda)
        s.add_argument("id", type=int)
        s.add_argument("--motivo", default="")
        s.add_argument(
            "--mesmo-assim",
            action="store_true",
            help="prossegue mesmo com licenca/marca bloqueando",
        )
        s.set_defaults(func=funcao)

    s = sub.add_parser("relatorio", help="gera o relatorio HTML de curadoria")
    s.add_argument("--saida")
    s.add_argument("--status", choices=list(STATUS_VALIDOS))
    s.add_argument("--linha")
    s.add_argument("--so-seguros", action="store_true")
    s.add_argument("--limite", type=int, default=200)
    s.add_argument("--titulo", default="Curadoria de modelos 3D")
    s.set_defaults(func=cmd_relatorio)

    s = sub.add_parser("exportar", help="exporta CSV no formato do Projeto 30 Produtos")
    s.add_argument("--saida", default="projeto30-candidatos.csv")
    s.add_argument("--status", choices=list(STATUS_VALIDOS))
    s.add_argument("--linha")
    s.add_argument("--so-seguros", action="store_true")
    s.add_argument("--limite", type=int, default=500)
    s.set_defaults(func=cmd_exportar)

    s = sub.add_parser(
        "letra",
        help="gera letra caixa em STL a partir de um SVG",
        description=(
            "Converte um SVG (texto ja em curvas) em letra caixa pronta para "
            "imprimir: face na frente, paredes e fundo aberto. Corta sozinha "
            "quando a peca nao cabe na mesa."
        ),
    )
    s.add_argument("svg", help="arquivo SVG com o texto em curvas")
    s.add_argument("--altura", type=float, default=150.0, help="altura da letra em mm")
    s.add_argument("--profundidade", type=float, default=25.0, help="profundidade em mm")
    s.add_argument("--parede", type=float, default=2.4, help="espessura da parede em mm")
    s.add_argument("--frente", type=float, default=2.0, help="espessura da face em mm")
    s.add_argument("--chanfro", type=float, default=0.0, help="filete lateral em mm")
    s.add_argument("--macica", action="store_true", help="sem cavidade interna")
    s.add_argument("--furos", help='furos de fixacao: "x,y;x,y" em mm')
    s.add_argument("--furos-auto", action="store_true", help="distribui furos sozinho")
    s.add_argument("--furo-diametro", type=float, default=4.0)
    s.add_argument("--furo-espacamento", type=float, default=60.0)
    s.add_argument("--sem-cortar", action="store_true", help="nao corta para caber na mesa")
    s.add_argument("--tolerancia", type=float, default=0.1, help="achatamento das curvas em mm")
    s.add_argument("--saida", help="pasta de destino dos STL")
    s.add_argument("--nome", help="nome base dos arquivos")
    s.set_defaults(func=cmd_letra)

    s = sub.add_parser("stats", help="resumo do funil de curadoria")
    s.set_defaults(func=cmd_stats)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = construir_parser()
    args = parser.parse_args(argv)
    cfg = carregar_config(args.config)
    for aviso in getattr(cfg, "avisos", []):
        print(amarelo(f"config: {aviso}"), file=sys.stderr)
    try:
        return int(args.func(args, cfg) or 0)
    except KeyboardInterrupt:
        print("\ninterrompido")
        return 130


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
