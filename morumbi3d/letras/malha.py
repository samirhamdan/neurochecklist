"""Ponte opcional para o trimesh.

O cortador proprio (``cortar.py``) existe para o pacote rodar sem instalar
nada. Mas quando o ``trimesh`` esta disponivel — e no morumbi3d_web ele ja e
dependencia — cortar com ele e melhor: e codigo de producao testado por muita
gente, e resolve os casos degenerados que o cortador caseiro erra (peca
simetrica cortada no eixo de simetria, nesga fina no meio de contra-forma).

Segue as armadilhas ja documentadas no CLAUDE.md do gerador de logo:

* **nunca** ``process(validate=True)``: ele apaga triangulo degenerado e cada
  um deixa um furo. Use ``merge_vertices()`` + ``fix_normals()``;
* costure cada corpo ANTES de concatenar; depois de juntar, nao mexa mais;
* ``scipy`` e obrigatorio de verdade — o ``trimesh`` so reclama na hora de
  contar corpos, longe da causa. ``disponivel()`` testa isso de saida.
"""

from __future__ import annotations

from typing import Any

Triangulo = tuple[tuple[float, float, float], ...]

_estado: dict[str, Any] = {}


def disponivel() -> tuple[bool, str]:
    """(pode_usar, motivo). Testa o caminho todo, nao so o import."""

    if "ok" in _estado:
        return _estado["ok"], _estado["motivo"]

    try:
        import numpy  # noqa: F401
        import trimesh
    except Exception as exc:
        _estado.update(ok=False, motivo=f"trimesh/numpy nao instalados ({exc})")
        return _estado["ok"], _estado["motivo"]

    try:
        # Exercita fix_normals e slice_plane num cubo: e ai que faltam o
        # scipy, o networkx e o rtree, cada um com erro longe da causa.
        cubo = trimesh.creation.box(extents=(10.0, 10.0, 10.0))
        cubo.fix_normals()
        pedaco = cubo.slice_plane([0, 0, 0], [0, 0, 1], cap=True)
        if pedaco is None or not pedaco.is_watertight:
            raise RuntimeError("slice_plane nao devolveu peca fechada")
    except Exception as exc:
        _estado.update(
            ok=False,
            motivo=f"trimesh instalado mas incompleto ({exc}); falta scipy/networkx/rtree?",
        )
        return _estado["ok"], _estado["motivo"]

    _estado.update(ok=True, motivo=f"trimesh {trimesh.__version__}")
    return _estado["ok"], _estado["motivo"]


def para_trimesh(triangulos: list[Triangulo]):
    """Lista de triangulos -> Trimesh costurado."""

    import numpy as np
    import trimesh

    vertices = np.array([p for tri in triangulos for p in tri], dtype=np.float64)
    faces = np.arange(len(vertices), dtype=np.int64).reshape(-1, 3)
    # process=False de proposito: a limpeza automatica do trimesh e a mesma
    # que abre a malha (ver o cabecalho do modulo).
    malha = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    malha.merge_vertices()
    malha.fix_normals()
    return malha


def para_triangulos(malha) -> list[Triangulo]:
    return [tuple(map(tuple, malha.vertices[face])) for face in malha.faces]


def cortar_um_plano(
    triangulos: list[Triangulo], eixo: int, corte: float
) -> list[list[Triangulo]] | None:
    """Corta por UM plano. Devolve os pedacos, ou ``None`` se nao deu.

    Um plano que cai fora do material devolve um pedaco so — nao e erro: numa
    linha de texto ha folga entre uma letra e outra, e a grade de corte cai
    nessas folgas o tempo todo.
    """

    ok, _ = disponivel()
    if not ok:
        return None
    try:
        malha = para_trimesh(triangulos)
        normal = [0.0, 0.0, 0.0]
        normal[eixo] = 1.0
        origem = [0.0, 0.0, 0.0]
        origem[eixo] = corte

        abaixo = malha.slice_plane(origem, [-n for n in normal], cap=True)
        acima = malha.slice_plane(origem, normal, cap=True)
        partes = [
            p for p in (abaixo, acima) if p is not None and len(p.faces) > 0
        ]
        if not partes:
            return None
        if not all(p.is_watertight for p in partes):
            return None
        return [para_triangulos(p) for p in partes]
    except Exception:
        return None
