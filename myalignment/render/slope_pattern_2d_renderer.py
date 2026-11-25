from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene

if TYPE_CHECKING:
    from myalignment.corridor.slope_pattern import SlopePattern


def _draw_patterns(scene, patterns, project, text_height):
    primitives = []
    for pattern in patterns:
        style = pattern.style
        appearance = Style(color=style.color, layer=style.layer, lineweight=style.lineweight)
        items = []
        for element in pattern.elements:
            points = []
            for vertex in element.points:
                point = project(pattern, vertex)
                if not points or points[-1].distance_to(point) > 1e-8:
                    points.append(point)
            if len(points) == 1 and element.element_type == "marker":
                items.append(Primitive.circle(points[0], style.pattern_size / 4, appearance))
            elif len(points) == 2:
                items.append(Primitive.line(*points, style=appearance))
            elif len(points) > 2:
                items.append(Primitive.polyline(points, style=appearance))
        label = pattern.label
        if label:
            a, b = (project(pattern, p) for p in (pattern.start_point, pattern.end_point))
            pos = Point2d((a.x + b.x) / 2, (a.y + b.y) / 2 + text_height)
            items.append(Primitive.text(pos, label, text_height, style=appearance))
        if items:
            scene = scene.add_layer(Layer(style.layer, color=style.color, lineweight=style.lineweight))
            primitives.extend(items)
    return scene.add_all(primitives) if primitives else scene


class SlopePattern2DRenderer:
    """월드 XY 평면에 사면 표시선, 말뚝 기호와 레이블을 추가한다."""

    @staticmethod
    def render(scene: Scene, collection: Iterable[SlopePattern]) -> Scene:
        """기존 평면 장면을 확장한다."""
        return _draw_patterns(scene, collection, lambda _, p: Point2d(p.x, p.y), 1.2)
