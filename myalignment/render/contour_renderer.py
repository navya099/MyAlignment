from __future__ import annotations

from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene
from myalignment.surface.contour_style import ContourStyle
from myalignment.surface.contour_type import ContourType

if TYPE_CHECKING:
    from myalignment.surface.contour_line import ContourSet


class ContourRenderer:
    """평면 장면에 등고선과 주 등고선 표고 레이블을 추가한다."""

    @staticmethod
    def render(scene: Scene, contours: ContourSet, style: ContourStyle | None = None) -> Scene:
        style = style or ContourStyle.standard()
        text = Style(color=style.label_color, layer=style.label_layer)
        layers = {}
        primitives = []
        for contour in contours:
            if contour.point_count < 2 or not style.is_visible(contour.contour_type):
                continue
            layer, color, weight = style.appearance(contour.contour_type, contour.elevation)
            layers.setdefault(layer, Layer(layer, color=color, lineweight=weight))
            primitives.append(Primitive.polyline(
                contour.points, closed=contour.closed, style=Style(color=color, lineweight=weight, layer=layer),
            ))
            if style.show_labels and contour.contour_type is ContourType.MAJOR:
                length, spacing = contour.length, style.label_interval_distance
                count = max(1, int(length / spacing))
                start = (length - (count - 1) * spacing) / 2
                distances = (start + i * spacing for i in range(count))
                for point in contour._points_at_distances(distances):
                    layers.setdefault(style.label_layer, Layer(style.label_layer, color=style.label_color))
                    anchor = Point2d(point.x, point.y + style.label_height * 0.5)
                    primitives.append(Primitive.text(anchor, f"{contour.elevation:.2f}", style.label_height, style=text))
        for layer in layers.values():
            scene = scene.add_layer(layer)
        return scene.add_all(primitives) if primitives else scene
