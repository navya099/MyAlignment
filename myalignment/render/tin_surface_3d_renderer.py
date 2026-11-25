from __future__ import annotations

import math
from typing import TYPE_CHECKING

from myalignment.render.primitives_3d import Point3D, Primitive3D, Style3D
from myalignment.render.scene_3d import Scene3D

if TYPE_CHECKING:
    from myalignment.surface.tin_surface import TinSurface


class TinSurface3DRenderer:
    @classmethod
    def render(
        cls, surface: TinSurface, color: int = 7, show_wireframe: bool = True, show_mesh: bool = False,
        *, mesh_style: Style3D | None = None, wire_style: Style3D | None = None,
        z_scale: float = 1.0, z_offset: float = 0.0,
    ) -> Scene3D:
        """TIN을 스타일과 표고 변환을 적용해 3D 장면으로 만든다."""
        if not math.isfinite(z_scale) or z_scale <= 0 or not math.isfinite(z_offset):
            raise ValueError("z_scale must be positive and both Z settings must be finite")
        vertices = tuple(Point3D(p.x, p.y, p.z * z_scale + z_offset) for p in surface.points)
        faces = tuple((tri.a, tri.b, tri.c) for tri in surface.triangles)
        primitives = []
        if show_wireframe:
            edges = dict.fromkeys(
                (min(a, b), max(a, b))
                for face in faces for a, b in zip(face, (*face[1:], face[0]))
            )
            style = wire_style or Style3D(color=8, lineweight=0.15, layer="C-TIN-WIREFRAME")
            primitives.extend(Primitive3D.line(vertices[a], vertices[b], style) for a, b in edges)
        if show_mesh and faces:
            style = mesh_style or Style3D(color=color, layer="C-TIN-MESH")
            primitives.append(Primitive3D.mesh(vertices, faces, style))
        return Scene3D(tuple(primitives))
