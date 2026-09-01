"""Utilitarios compartilhados pelos testes (geradores de malha, config temporaria)."""

from __future__ import annotations

import struct
import tempfile
from pathlib import Path

from morumbi3d.config import Config


def config_temporaria() -> Config:
    cfg = Config()
    cfg.raiz = Path(tempfile.mkdtemp(prefix="morumbi3d-teste-"))
    cfg.preparar_diretorios()
    return cfg


def cubo(lado: float = 20.0, origem=(0.0, 0.0, 0.0)) -> list:
    """Cubo fechado, com normais para fora."""

    ox, oy, oz = origem
    l = lado
    v = [
        (ox, oy, oz), (ox + l, oy, oz), (ox + l, oy + l, oz), (ox, oy + l, oz),
        (ox, oy, oz + l), (ox + l, oy, oz + l), (ox + l, oy + l, oz + l), (ox, oy + l, oz + l),
    ]
    faces = [
        (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
        (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
    ]
    return [(v[a], v[b], v[c]) for a, b, c in faces]


def escrever_stl_binario(caminho: Path, triangulos: list) -> Path:
    with Path(caminho).open("wb") as fh:
        fh.write(b"\0" * 80)
        fh.write(struct.pack("<I", len(triangulos)))
        for tri in triangulos:
            fh.write(struct.pack("<3f", 0.0, 0.0, 0.0))
            for ponto in tri:
                fh.write(struct.pack("<3f", *ponto))
            fh.write(struct.pack("<H", 0))
    return Path(caminho)


def escrever_stl_ascii(caminho: Path, triangulos: list) -> Path:
    linhas = ["solid teste"]
    for tri in triangulos:
        linhas.append("  facet normal 0 0 0")
        linhas.append("    outer loop")
        for x, y, z in tri:
            linhas.append(f"      vertex {x} {y} {z}")
        linhas.append("    endloop")
        linhas.append("  endfacet")
    linhas.append("endsolid teste")
    Path(caminho).write_text("\n".join(linhas), encoding="utf-8")
    return Path(caminho)


def escrever_3mf(caminho: Path, triangulos: list) -> Path:
    import zipfile

    vertices: list[tuple[float, float, float]] = []
    indices: dict[tuple[float, float, float], int] = {}
    faces = []
    for tri in triangulos:
        ids = []
        for ponto in tri:
            if ponto not in indices:
                indices[ponto] = len(vertices)
                vertices.append(ponto)
            ids.append(indices[ponto])
        faces.append(tuple(ids))

    vs = "".join(f'<vertex x="{x}" y="{y}" z="{z}"/>' for x, y, z in vertices)
    ts = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in faces)
    modelo = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<model unit="millimeter" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
        f'<resources><object id="1" type="model"><mesh>'
        f"<vertices>{vs}</vertices><triangles>{ts}</triangles>"
        "</mesh></object></resources>"
        '<build><item objectid="1"/></build></model>'
    )
    with zipfile.ZipFile(caminho, "w") as zf:
        zf.writestr("3D/3dmodel.model", modelo)
    return Path(caminho)
