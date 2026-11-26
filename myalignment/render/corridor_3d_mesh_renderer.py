from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import math
from typing import TYPE_CHECKING

from myalignment.assembly.codes import LinkCode
from myalignment.corridor.corridor_3d_renderer import Corridor3DRenderer, _indexed_mesh, _sections
from myalignment.corridor.corridor_mesh import CorridorMesh
from myalignment.corridor.mesh_mode import MeshMode
from myalignment.export.dxf_3d_writer import Dxf3DWriter
from myalignment.export.json_3d_exporter import Json3DExporter
from myalignment.render.primitives_3d import Style3D
from myalignment.render.scene_3d import Scene3D
from myalignment.render.tin_surface_3d_renderer import TinSurface3DRenderer
from myalignment.surface.boundary import Boundary
from myalignment.surface.boundary_set import BoundarySet
from myalignment.surface.tin_point import TinPoint
from myalignment.surface.tin_surface import TinSurface

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.corridor.corridor import Corridor
    from myalignment.profile.profile import Profile


_MESH_LAYER = "C-CORRIDOR-MESH"
_STYLE_NAMES = {
    MeshMode.QUAD_STRIP: (f"{_MESH_LAYER}-QUAD", "Quad Strip"),
    MeshMode.TRIANGULATED: (f"{_MESH_LAYER}-TIN", "Triangulated TIN"),
}


def _link_meshes(sections):
    mesh = CorridorMesh.from_sections(sections)
    groups = defaultdict(list)
    for code, face in zip(mesh.face_codes, mesh.triangles):
        groups[code].append(face)
    for code, faces in groups.items():
        if code is None:
            name, suffix = "Unclassified", "UNCLASSIFIED"
        else:
            name = str(code.value)
            suffix = code.name if isinstance(code, LinkCode) else f"{type(code).__name__}-{code.name}"
        color = {LinkCode.SUBBASE: 6, LinkCode.CURB: 2}.get(code, Corridor3DRenderer.LINK_COLORS.get(name, 7))
        style = Style3D(color=color, layer=f"{_MESH_LAYER}-{suffix}", lineweight=0.2)
        yield name, _indexed_mesh(mesh.vertices, faces, style)


def _tin_surface(sections, alignment):
    if len(sections) < 2:
        return None
    left_edge, right_edge = [], []
    upper = {}
    for section in sections:
        if not section.points:
            continue
        center = alignment.point_at(section.station)
        angle = alignment.tangent_at(section.station)
        nx, ny = math.sin(angle), -math.cos(angle)

        def offset(point):
            return (point.x - center.x) * nx + (point.y - center.y) * ny

        left = min(section.points, key=offset)
        right = max(section.points, key=offset)
        left_edge.append((left.x, left.y))
        right_edge.append((right.x, right.y))
        for point in section.points:
            key = point.x, point.y
            if key not in upper or point.z > upper[key].z:
                upper[key] = TinPoint(point.x, point.y, point.z)

    if len(upper) < 3 or len(left_edge) < 2 or left_edge == right_edge:
        return None
    perimeter = tuple(dict.fromkeys((*left_edge, *reversed(right_edge))))
    if len(perimeter) < 3:
        return None
    boundary = Boundary.from_coords(perimeter, name="Corridor TIN")
    return TinSurface.from_points(list(upper.values()), boundaries=BoundarySet((boundary,)))


class Corridor3DMeshRenderer:
    """코리더의 링크별 메시, 사각 스트립 또는 영역별 TIN을 만든다."""

    @staticmethod
    def render_mesh(
        corridor: Corridor, alignment: Alignment, mode: MeshMode = MeshMode.LINK_BASED,
        sample_frequency: float | None = None, z_offset: float = 0.0, *,
        profile: Profile | None = None, baseline_name: str | None = None,
    ) -> Scene3D:
        """기하 측점 간격과 기준 종단을 적용하고 영역 간 공백을 보존한다."""
        if not isinstance(mode, MeshMode):
            raise ValueError("mode must be a MeshMode")

        primitives = []
        labels = {}
        for sections in _sections(corridor, alignment, sample_frequency, z_offset, profile, baseline_name=baseline_name):
            if mode is MeshMode.LINK_BASED:
                for label, primitive in _link_meshes(sections):
                    labels[primitive.style.layer] = label
                    primitives.append(primitive)
                continue

            layer, label = _STYLE_NAMES[mode]
            style = Style3D(color=7, layer=layer)
            if mode is MeshMode.QUAD_STRIP:
                mesh = CorridorMesh.from_sections(sections)
                if mesh.triangles:
                    primitives.append(_indexed_mesh(mesh.vertices, mesh.triangles, style))
                    labels[layer] = label
            else:
                surface = _tin_surface(sections, alignment)
                if surface is not None and surface.triangles:
                    rendered = TinSurface3DRenderer.render(surface, show_wireframe=False, show_mesh=True, mesh_style=style)
                    primitives.extend(rendered.primitives)
                    labels[layer] = label
        return Scene3D(tuple(primitives), {"mesh_mode": mode.value, "mesh_layers": labels})


class Corridor3DMeshPreview:
    """코리더 메시를 범례가 있는 HTML 및 3D DXF로 저장한다."""

    @staticmethod
    def preview(
        corridor: Corridor, alignment: Alignment, html_path: str | Path | None,
        dxf_path: str | Path | None = None, mode: MeshMode = MeshMode.LINK_BASED,
        sample_frequency: float | None = None, *, z_offset: float = 0.0,
        profile: Profile | None = None, baseline_name: str | None = None,
        three_module_base: str | None = None,
    ) -> Scene3D:
        """선택한 파일을 출력하고 메시 장면을 반환한다."""
        scene = Corridor3DMeshRenderer.render_mesh(
            corridor, alignment, mode, sample_frequency, z_offset, profile=profile, baseline_name=baseline_name,
        )
        if dxf_path is not None:
            Dxf3DWriter(scene).write(dxf_path)
        if html_path is not None:
            options = {} if three_module_base is None else {"three_module_base": three_module_base}
            Json3DExporter.export_mesh_with_legend(
                scene, html_path, f"Corridor 3D Mesh ({mode.value}) — {corridor.name}", **options,
            )
        return scene
