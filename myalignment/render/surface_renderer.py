from __future__ import annotations

from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene

if TYPE_CHECKING:
    from myalignment.surface.tin_surface import TinSurface


class TinSurfaceRenderer:
    TRIANGLE_LAYER = "C-TIN-TRI"
    BOUNDARY_LAYER = "C-TIN-BND"

    @classmethod
    def render(
        cls, surface: TinSurface, scene: Scene | None = None,
        show_triangles: bool = True, show_boundary: bool = True,
        *, triangle_layer: Layer | None = None, boundary_layer: Layer | None = None,
    ) -> Scene:
        scene = Scene() if scene is None else scene
        if show_triangles:
            layer = triangle_layer or Layer(cls.TRIANGLE_LAYER, color=8)
            style = Style(color=layer.color, layer=layer.name)
            scene = scene.add_layer(layer).add_all(
                Primitive.polyline(
                    (Point2d(p.x, p.y) for p in triangle.vertices(surface.points)),
                    closed=True, style=style,
                )
                for triangle in surface.triangles
            )
        if show_boundary and surface.boundaries:
            layer = boundary_layer or Layer(cls.BOUNDARY_LAYER, color=1, lineweight=0.5)
            style = Style(color=layer.color, lineweight=layer.lineweight, layer=layer.name)
            scene = scene.add_layer(layer).add_all(
                Primitive.polyline(
                    (Point2d(p.x, p.y) for p in boundary.vertices),
                    closed=True, style=style,
                )
                for boundary in surface.boundaries
            )
        return scene
