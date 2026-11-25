from __future__ import annotations

import re
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.assembly.codes import LinkCode
from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene
from myalignment.render.surface_renderer import TinSurfaceRenderer

if TYPE_CHECKING:
    from myalignment.corridor.link_surface_manager import LinkSurfaceManager


class LinkSurfaceRenderer:
    """링크별 삼각망과 경계를 코드 레이어에 배치한다."""

    LINK_COLORS = {
        LinkCode.TOP: 7,
        LinkCode.PAVEMENT: 1,
        LinkCode.PAVEMENT_TOP: 1,
        LinkCode.PAVEMENT_BOTTOM: 6,
        LinkCode.SUBBASE: 6,
        LinkCode.SHOULDER: 3,
        LinkCode.SLOPE: 5,
        LinkCode.DATUM: 8,
        LinkCode.CURB: 2,
    }

    @classmethod
    def render(
        cls,
        scene: Scene,
        manager: LinkSurfaceManager,
        show_triangles: bool = True,
        show_boundary: bool = True,
        *,
        show_labels: bool = True,
    ) -> Scene:
        """선택한 표면 표시를 기존 Scene에 추가한다."""
        for result in manager:
            surface = result.surface
            code = result.link_code
            color = cls.LINK_COLORS.get(code, 7) if result.color is None else result.color
            token = re.sub(r"[^\w-]+", "-", code.value if code is not None else surface.name).strip("-")
            name = f"C-CORRIDOR-SURFACE-{token.upper() or 'CUSTOM'}"
            layer = Layer(name, color=color)
            scene = TinSurfaceRenderer.render(
                surface, scene, show_triangles, show_boundary, triangle_layer=layer,
                boundary_layer=Layer(name, color=color, lineweight=0.6),
            )
            if show_labels and surface.triangles:
                vertices = surface.triangles[0].vertices(surface.points)
                x, y = (sum(getattr(vertex, axis) for vertex in vertices) / 3 for axis in ("x", "y"))
                style = Style(color=color, layer=name)
                rows = [*surface.name.splitlines(), f"{surface.area_2d:.1f} m²"]
                scene = scene.add_layer(layer).add_all(
                    Primitive.text(Point2d(x, y - index * 2.4), row, 2.0, style=style)
                    for index, row in enumerate(rows) if row
                )
        return scene
