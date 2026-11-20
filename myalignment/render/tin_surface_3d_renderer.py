from __future__ import annotations

from typing import TYPE_CHECKING

from myalignment.render.primitives_3d import Point3D, Primitive3D, Style3D
from myalignment.render.scene_3d import Scene3D

if TYPE_CHECKING:
    from myalignment.surface.tin_surface import TinSurface


class TinSurface3DRenderer:
    @classmethod
    def render(
        cls, surface: TinSurface, color: int = 7, show_wireframe: bool = True, show_mesh: bool = False,
    ) -> Scene3D:
        vertices = tuple(Point3D(p.x, p.y, p.z) for p in surface.points)
        faces = tuple((tri.a, tri.b, tri.c) for tri in surface.triangles)
        primitives = []
        if show_wireframe:
            edges = dict.fromkeys(
                (min(a, b), max(a, b))
                for face in faces for a, b in zip(face, (*face[1:], face[0]))
            )
            style = Style3D(color=8, lineweight=0.15, layer="C-TIN-WIREFRAME")
            primitives.extend(Primitive3D.line(vertices[a], vertices[b], style) for a, b in edges)
        if show_mesh and faces:
            primitives.append(Primitive3D.mesh(vertices, faces, Style3D(color=color, layer="C-TIN-MESH")))
        return Scene3D(tuple(primitives))
