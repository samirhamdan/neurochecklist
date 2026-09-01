"""Analisador de imprimibilidade.

Le STL (binario e ASCII) e 3MF apenas com a biblioteca padrao e responde as
mesmas perguntas que hoje sao feitas na mao antes de imprimir:

* a malha e fechada (watertight)?
* quantas partes soltas (shells) existem?
* cabe na mesa da impressora?
* quanta area fica em balanco (necessidade de suporte)?
* quanto material e tempo, aproximadamente?

Se ``trimesh`` estiver instalado, ele e usado apenas como conferencia extra
(campo ``conferencia_trimesh``); nada aqui depende dele.
"""

from __future__ import annotations

import math
import re
import struct
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field, asdict
from pathlib import Path

from .config import Config

FORMATOS_SUPORTADOS = {".stl", ".3mf", ".obj"}
_TOLERANCIA_SOLDA = 1e-4  # mm; vertices mais proximos que isso sao o mesmo ponto


class ArquivoInvalido(ValueError):
    """Arquivo ilegivel ou em formato nao suportado."""


# ---------------------------------------------------------------- leitores


def _ler_stl_binario(dados: bytes) -> list[tuple[tuple[float, float, float], ...]]:
    (n,) = struct.unpack_from("<I", dados, 80)
    esperado = 84 + n * 50
    if len(dados) < esperado:
        raise ArquivoInvalido(
            f"STL binario truncado: cabecalho anuncia {n} triangulos "
            f"({esperado} bytes), arquivo tem {len(dados)}"
        )
    triangulos = []
    desloc = 84
    desempacotar = struct.Struct("<12fH").unpack_from
    for _ in range(n):
        valores = desempacotar(dados, desloc)
        triangulos.append(
            (
                (valores[3], valores[4], valores[5]),
                (valores[6], valores[7], valores[8]),
                (valores[9], valores[10], valores[11]),
            )
        )
        desloc += 50
    return triangulos


_RE_VERTICE = re.compile(
    r"vertex\s+(-?[\d.eE+-]+)\s+(-?[\d.eE+-]+)\s+(-?[\d.eE+-]+)"
)


def _ler_stl_ascii(texto: str) -> list[tuple[tuple[float, float, float], ...]]:
    pontos = [
        (float(x), float(y), float(z)) for x, y, z in _RE_VERTICE.findall(texto)
    ]
    if len(pontos) % 3 != 0:
        raise ArquivoInvalido(
            f"STL ASCII com {len(pontos)} vertices — nao e multiplo de 3"
        )
    return [tuple(pontos[i : i + 3]) for i in range(0, len(pontos), 3)]


def _parece_binario(dados: bytes) -> bool:
    if len(dados) < 84:
        return False
    (n,) = struct.unpack_from("<I", dados, 80)
    return len(dados) == 84 + n * 50


def _ler_stl(caminho: Path) -> list[tuple[tuple[float, float, float], ...]]:
    dados = caminho.read_bytes()
    if not dados:
        raise ArquivoInvalido("arquivo vazio")
    if _parece_binario(dados):
        return _ler_stl_binario(dados)
    try:
        texto = dados.decode("utf-8", errors="replace")
    except Exception as exc:  # pragma: no cover - decode com replace nao falha
        raise ArquivoInvalido(f"nao foi possivel decodificar: {exc}") from exc
    if "facet" in texto[:2048] or "vertex" in texto[:2048]:
        return _ler_stl_ascii(texto)
    # Cabecalho mente sobre a contagem: tenta binario mesmo assim.
    return _ler_stl_binario(dados)


def _matriz_3mf(texto: str | None) -> tuple[float, ...] | None:
    if not texto:
        return None
    partes = texto.split()
    if len(partes) != 12:
        return None
    try:
        return tuple(float(p) for p in partes)
    except ValueError:
        return None


def _aplicar_matriz(p: tuple[float, float, float], m: tuple[float, ...] | None):
    if m is None:
        return p
    x, y, z = p
    return (
        m[0] * x + m[3] * y + m[6] * z + m[9],
        m[1] * x + m[4] * y + m[7] * z + m[10],
        m[2] * x + m[5] * y + m[8] * z + m[11],
    )


def _ler_3mf(caminho: Path) -> list[tuple[tuple[float, float, float], ...]]:
    with zipfile.ZipFile(caminho) as zf:
        nomes = [n for n in zf.namelist() if n.lower().endswith(".model")]
        if not nomes:
            raise ArquivoInvalido("3MF sem arquivo .model interno")
        preferido = next((n for n in nomes if n.lower() == "3d/3dmodel.model"), nomes[0])
        raiz = ET.fromstring(zf.read(preferido))

    ns = {"c": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}

    def _tag(elemento: ET.Element) -> str:
        return elemento.tag.split("}")[-1]

    objetos: dict[str, list] = {}
    for obj in raiz.iter():
        if _tag(obj) != "object":
            continue
        malha = next((f for f in obj if _tag(f) == "mesh"), None)
        if malha is None:
            continue
        vertices_el = next((f for f in malha if _tag(f) == "vertices"), None)
        triangulos_el = next((f for f in malha if _tag(f) == "triangles"), None)
        if vertices_el is None or triangulos_el is None:
            continue
        vs = [
            (float(v.get("x", 0)), float(v.get("y", 0)), float(v.get("z", 0)))
            for v in vertices_el
            if _tag(v) == "vertex"
        ]
        ts = []
        for t in triangulos_el:
            if _tag(t) != "triangle":
                continue
            try:
                i1, i2, i3 = int(t.get("v1")), int(t.get("v2")), int(t.get("v3"))
                ts.append((vs[i1], vs[i2], vs[i3]))
            except (TypeError, ValueError, IndexError):
                continue
        objetos[obj.get("id", "")] = ts

    build = next((f for f in raiz if _tag(f) == "build"), None)
    triangulos: list = []
    if build is not None:
        for item in build:
            if _tag(item) != "item":
                continue
            ts = objetos.get(item.get("objectid", ""), [])
            m = _matriz_3mf(item.get("transform"))
            for tri in ts:
                triangulos.append(tuple(_aplicar_matriz(p, m) for p in tri))
    if not triangulos:  # sem <build> util: usa todos os objetos
        for ts in objetos.values():
            triangulos.extend(ts)
    if not triangulos:
        raise ArquivoInvalido("3MF sem geometria legivel")
    return triangulos


_RE_OBJ_V = re.compile(r"^v\s+(-?[\d.eE+-]+)\s+(-?[\d.eE+-]+)\s+(-?[\d.eE+-]+)", re.M)


def _ler_obj(caminho: Path) -> list[tuple[tuple[float, float, float], ...]]:
    texto = caminho.read_text(encoding="utf-8", errors="replace")
    vertices = [
        (float(x), float(y), float(z)) for x, y, z in _RE_OBJ_V.findall(texto)
    ]
    triangulos = []
    for linha in texto.splitlines():
        if not linha.startswith("f "):
            continue
        indices = []
        for campo in linha.split()[1:]:
            try:
                i = int(campo.split("/")[0])
            except ValueError:
                continue
            indices.append(i - 1 if i > 0 else len(vertices) + i)
        for k in range(1, len(indices) - 1):  # leque de triangulos
            try:
                triangulos.append(
                    (vertices[indices[0]], vertices[indices[k]], vertices[indices[k + 1]])
                )
            except IndexError:
                continue
    if not triangulos:
        raise ArquivoInvalido("OBJ sem faces legiveis")
    return triangulos


def carregar_triangulos(caminho: Path) -> list[tuple[tuple[float, float, float], ...]]:
    """Le um arquivo de malha e devolve a lista de triangulos."""

    caminho = Path(caminho)
    if not caminho.is_file():
        raise ArquivoInvalido(f"arquivo nao encontrado: {caminho}")
    sufixo = caminho.suffix.lower()
    if sufixo == ".stl":
        return _ler_stl(caminho)
    if sufixo == ".3mf":
        return _ler_3mf(caminho)
    if sufixo == ".obj":
        return _ler_obj(caminho)
    raise ArquivoInvalido(
        f"formato {sufixo or '(sem extensao)'} nao suportado; use STL, 3MF ou OBJ"
    )


# ---------------------------------------------------------------- analise


@dataclass
class RelatorioMalha:
    """Resultado da analise de um arquivo de malha."""

    arquivo: str = ""
    formato: str = ""
    triangulos: int = 0
    vertices_unicos: int = 0
    fechada: bool = False
    arestas_abertas: int = 0
    arestas_nao_manifold: int = 0
    faces_degeneradas: int = 0
    partes_soltas: int = 1
    dimensoes_mm: tuple[float, float, float] = (0.0, 0.0, 0.0)
    volume_cm3: float = 0.0
    area_cm2: float = 0.0
    cabe_na_mesa: bool = True
    cabe_girando: bool = False
    """Nao cabe direto, mas cabe girando 45 graus na diagonal da mesa."""

    escala_sugerida: float = 1.0
    """Fator <1 necessario para caber na mesa (1.0 = ja cabe)."""

    balanco_ratio: float = 0.0
    suporte: str = "nenhum"
    volume_suporte_cm3: float = 0.0
    material_g: float = 0.0
    tempo_h: float = 0.0
    problemas: list[str] = field(default_factory=list)
    alertas: list[str] = field(default_factory=list)
    nota: int = 0
    """0-100. Quanto maior, mais tranquilo e imprimir."""

    conferencia_trimesh: dict | None = None

    def resumo(self) -> str:
        x, y, z = self.dimensoes_mm
        estado = "fechada" if self.fechada else f"ABERTA ({self.arestas_abertas} arestas)"
        return (
            f"{x:.0f}x{y:.0f}x{z:.0f} mm | {estado} | {self.partes_soltas} parte(s) | "
            f"suporte: {self.suporte} | ~{self.material_g:.0f} g | ~{self.tempo_h:.1f} h"
        )

    def como_dict(self) -> dict:
        dados = asdict(self)
        dados["dimensoes_mm"] = list(self.dimensoes_mm)
        return dados


class _UnionFind:
    def __init__(self, n: int) -> None:
        self.pai = list(range(n))

    def find(self, a: int) -> int:
        raiz = a
        while self.pai[raiz] != raiz:
            raiz = self.pai[raiz]
        while self.pai[a] != raiz:  # compressao de caminho
            self.pai[a], a = raiz, self.pai[a]
        return raiz

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.pai[rb] = ra


def _chave(p: tuple[float, float, float]) -> tuple[int, int, int]:
    inv = 1.0 / _TOLERANCIA_SOLDA
    return (round(p[0] * inv), round(p[1] * inv), round(p[2] * inv))


def analisar_arquivo(caminho: Path | str, cfg: Config | None = None) -> RelatorioMalha:
    """Analisa um arquivo de malha e devolve o relatorio de imprimibilidade."""

    from .config import carregar_config

    cfg = cfg or carregar_config()
    caminho = Path(caminho)
    triangulos = carregar_triangulos(caminho)
    rel = analisar_triangulos(triangulos, cfg)
    rel.arquivo = str(caminho)
    rel.formato = caminho.suffix.lower().lstrip(".")
    rel.conferencia_trimesh = _conferir_com_trimesh(caminho)
    return rel


def analisar_triangulos(triangulos: list, cfg: Config) -> RelatorioMalha:
    rel = RelatorioMalha(triangulos=len(triangulos))
    if not triangulos:
        rel.problemas.append("malha vazia (nenhum triangulo)")
        return rel

    imp = cfg.impressora
    indice: dict[tuple[int, int, int], int] = {}
    contagem_arestas: dict[tuple[int, int], int] = {}
    dono_aresta: dict[tuple[int, int], int] = {}
    uf = _UnionFind(len(triangulos))

    min_x = min_y = min_z = math.inf
    max_x = max_y = max_z = -math.inf
    volume6 = 0.0
    area_total = 0.0
    area_balanco = 0.0
    degeneradas = 0

    limite_seno = math.sin(math.radians(imp.angulo_suporte_graus))
    # (area, z medio, z maximo) de cada face voltada para baixo; as que
    # encostam na mesa sao descartadas depois, quando min_z ja e conhecido.
    faces_baixas: list[tuple[float, float, float]] = []

    for idx, tri in enumerate(triangulos):
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = tri
        for x, y, z in tri:
            min_x, max_x = min(min_x, x), max(max_x, x)
            min_y, max_y = min(min_y, y), max(max_y, y)
            min_z, max_z = min(min_z, z), max(max_z, z)

        u = (bx - ax, by - ay, bz - az)
        v = (cx - ax, cy - ay, cz - az)
        nx = u[1] * v[2] - u[2] * v[1]
        ny = u[2] * v[0] - u[0] * v[2]
        nz = u[0] * v[1] - u[1] * v[0]
        norma = math.sqrt(nx * nx + ny * ny + nz * nz)
        area = norma / 2.0
        if area <= 1e-9:
            degeneradas += 1
        else:
            area_total += area
            if (-nz / norma) > limite_seno:
                faces_baixas.append((area, (az + bz + cz) / 3.0, max(az, bz, cz)))

        volume6 += ax * (by * cz - bz * cy) - ay * (bx * cz - bz * cx) + az * (
            bx * cy - by * cx
        )

        ids = []
        for p in tri:
            k = _chave(p)
            i = indice.get(k)
            if i is None:
                i = len(indice)
                indice[k] = i
            ids.append(i)
        for i, j in ((ids[0], ids[1]), (ids[1], ids[2]), (ids[2], ids[0])):
            if i == j:
                continue
            aresta = (i, j) if i < j else (j, i)
            contagem_arestas[aresta] = contagem_arestas.get(aresta, 0) + 1
            vizinho = dono_aresta.get(aresta)
            if vizinho is None:
                dono_aresta[aresta] = idx
            else:
                uf.union(vizinho, idx)

    rel.faces_degeneradas = degeneradas
    rel.vertices_unicos = len(indice)
    rel.arestas_abertas = sum(1 for c in contagem_arestas.values() if c == 1)
    rel.arestas_nao_manifold = sum(1 for c in contagem_arestas.values() if c > 2)
    rel.fechada = rel.arestas_abertas == 0 and rel.arestas_nao_manifold == 0
    rel.partes_soltas = len({uf.find(i) for i in range(len(triangulos))})

    # Faces voltadas para baixo que encostam na mesa apoiam-se nela: nao
    # sao balanco. A primeira camada tem a espessura de uma camada de folga.
    piso = min_z + max(imp.altura_camada_mm, 0.1)
    faces_balanco = [(a, z) for a, z, z_max in faces_baixas if z_max > piso]
    area_balanco = sum(a for a, _ in faces_balanco)

    dim = (max_x - min_x, max_y - min_y, max_z - min_z)
    rel.dimensoes_mm = (round(dim[0], 2), round(dim[1], 2), round(dim[2], 2))
    rel.volume_cm3 = round(abs(volume6) / 6.0 / 1000.0, 3)
    rel.area_cm2 = round(area_total / 100.0, 2)
    rel.balanco_ratio = round(area_balanco / area_total, 4) if area_total else 0.0

    # --- mesa ----------------------------------------------------------
    mx, my, mz = cfg.mesa_util
    rel.cabe_na_mesa = dim[0] <= mx and dim[1] <= my and dim[2] <= mz
    if not rel.cabe_na_mesa:
        rel.cabe_girando = dim[2] <= mz and _cabe_girado(dim[0], dim[1], mx, my)
        fatores = [
            mx / dim[0] if dim[0] else 1.0,
            my / dim[1] if dim[1] else 1.0,
            mz / dim[2] if dim[2] else 1.0,
        ]
        rel.escala_sugerida = round(min(1.0, min(fatores)), 3)

    # --- suporte -------------------------------------------------------
    rel.suporte = _classificar_suporte(rel.balanco_ratio)
    altura_media = (
        sum(area * max(z - min_z, 0.0) for area, z in faces_balanco) / area_balanco
        if area_balanco
        else 0.0
    )
    rel.volume_suporte_cm3 = round(
        area_balanco * altura_media * cfg.custo.densidade_suporte / 1000.0, 3
    )

    # --- material e tempo ----------------------------------------------
    material_cm3 = estimar_material_cm3(rel, cfg)
    rel.material_g = round(material_cm3 * cfg.custo.densidade_g_cm3, 1)
    rel.tempo_h = round(
        material_cm3 / max(imp.vazao_cm3_por_hora, 0.1) + imp.overhead_horas, 2
    )

    _diagnosticar(rel, cfg)
    rel.nota = _pontuar(rel)
    return rel


def estimar_material_cm3(rel: RelatorioMalha, cfg: Config) -> float:
    """Casca solida + preenchimento no miolo + suporte."""

    imp = cfg.impressora
    volume = rel.volume_cm3
    if volume <= 0:
        return 0.0
    casca = min(volume, rel.area_cm2 * (imp.espessura_parede_mm / 10.0))
    miolo = max(0.0, volume - casca) * imp.preenchimento
    return casca + miolo + rel.volume_suporte_cm3


def _cabe_girado(largura: float, profundidade: float, mx: float, my: float) -> bool:
    """A peca cabe na mesa se for girada em torno de Z?

    Girando de ``ang``, a caixa envolvente passa a medir
    ``L*cos + W*sin`` por ``L*sin + W*cos``. Varre os angulos de grau em grau
    e responde se algum deles cabe.
    """

    if largura <= 0 or profundidade <= 0:
        return False
    for graus in range(1, 90):
        rad = math.radians(graus)
        cos, sen = abs(math.cos(rad)), abs(math.sin(rad))
        if (
            largura * cos + profundidade * sen <= mx
            and largura * sen + profundidade * cos <= my
        ):
            return True
    return False


def _classificar_suporte(ratio: float) -> str:
    if ratio < 0.02:
        return "nenhum"
    if ratio < 0.10:
        return "pouco"
    if ratio < 0.25:
        return "moderado"
    return "muito"


def _diagnosticar(rel: RelatorioMalha, cfg: Config) -> None:
    if not rel.fechada:
        if rel.arestas_abertas:
            rel.problemas.append(
                f"malha aberta: {rel.arestas_abertas} arestas sem par "
                "(o fatiador pode gerar peca com furo)"
            )
        if rel.arestas_nao_manifold:
            rel.problemas.append(
                f"{rel.arestas_nao_manifold} arestas nao-manifold "
                "(geometria se auto-intersecta)"
            )
    if rel.faces_degeneradas:
        rel.alertas.append(f"{rel.faces_degeneradas} faces degeneradas (area zero)")
    if rel.partes_soltas > 1:
        rel.alertas.append(
            f"{rel.partes_soltas} partes soltas — confira se e um kit ou "
            "geometria quebrada"
        )
    if not rel.cabe_na_mesa:
        mx, my, mz = cfg.mesa_util
        detalhe = (
            "cabe girando na diagonal"
            if rel.cabe_girando
            else f"precisa reduzir para {rel.escala_sugerida * 100:.0f}% ou cortar"
        )
        rel.problemas.append(
            f"nao cabe na mesa util ({mx:.0f}x{my:.0f}x{mz:.0f} mm) — {detalhe}"
        )
    if rel.suporte in ("moderado", "muito"):
        rel.alertas.append(
            f"{rel.balanco_ratio * 100:.0f}% da area em balanco — suporte {rel.suporte}, "
            "mais desperdicio e acabamento"
        )
    menor = min(rel.dimensoes_mm)
    if 0 < menor < 3:
        rel.alertas.append(
            f"dimensao minima de {menor:.1f} mm — peca fragil ou detalhe muito fino"
        )
    if rel.volume_cm3 <= 0:
        rel.problemas.append("volume calculado zero — malha provavelmente invalida")


def _pontuar(rel: RelatorioMalha) -> int:
    nota = 100
    if not rel.fechada:
        nota -= 35 if rel.arestas_abertas > 50 else 20
    if rel.arestas_nao_manifold:
        nota -= 10
    if not rel.cabe_na_mesa:
        nota -= 20 if rel.cabe_girando else 40
    nota -= {"nenhum": 0, "pouco": 5, "moderado": 15, "muito": 25}[rel.suporte]
    if rel.partes_soltas > 4:
        nota -= 10
    if rel.faces_degeneradas > rel.triangulos * 0.01:
        nota -= 5
    if rel.volume_cm3 <= 0:
        nota -= 40
    return max(0, min(100, nota))


def _conferir_com_trimesh(caminho: Path) -> dict | None:
    """Conferencia opcional: so roda se ``trimesh`` estiver instalado."""

    try:
        import trimesh  # type: ignore
    except Exception:
        return None
    try:
        malha = trimesh.load(str(caminho), force="mesh")
        return {
            "fechada": bool(malha.is_watertight),
            "volume_cm3": round(float(abs(malha.volume)) / 1000.0, 3),
            "partes_soltas": int(malha.body_count),
        }
    except Exception as exc:  # pragma: no cover - depende de lib externa
        return {"erro": str(exc)}
