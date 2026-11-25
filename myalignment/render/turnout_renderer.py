from __future__ import annotations

import math
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene

if TYPE_CHECKING:
    from myalignment.turnout.geometry import TurnoutGeometry


class TurnoutRenderer:
    """턴아웃 레일과 공칭 PS·PF·PC를 2D 평면도에 추가한다."""

    MAIN_RAIL_LAYER = "C-TURNOUT-MAIN-RAIL"
    BRANCH_RAIL_LAYER = "C-TURNOUT-BRANCH-RAIL"
    MARKER_LAYER = "C-TURNOUT-MARKER"
    LABEL_LAYER = "C-TURNOUT-LABEL"

    @classmethod
    def render_2d(
        cls,
        scene: Scene,
        geometry: TurnoutGeometry,
        turnout_name: str = "",
        show_labels: bool = True,
        show_markers: bool = True,
    ) -> Scene:
        """레일을 폴리라인으로 배치하고 마커와 레이블을 선택적으로 추가한다."""
        if not geometry.is_valid:
            raise ValueError(geometry.error_message)

        primitives = []
        for layer, color, rails in (
            (cls.MAIN_RAIL_LAYER, 7, (geometry.main_left_rail, geometry.main_right_rail)),
            (cls.BRANCH_RAIL_LAYER, 3, (geometry.branch_left_rail, geometry.branch_right_rail)),
        ):
            style = Style(color=color, layer=layer, lineweight=0.5)
            primitives.extend(Primitive.polyline(rail, style=style) for rail in rails if len(rail) >= 2)

        marker_style = Style(color=1, layer=cls.MARKER_LAYER, lineweight=0.5)
        label_style = Style(color=2, layer=cls.LABEL_LAYER)
        for name, point, station in geometry.markers:
            x, y = point.x, point.y
            if show_markers:
                primitives.extend((
                    Primitive.line(Point2d(x - 2, y - 2), Point2d(x + 2, y + 2), marker_style),
                    Primitive.line(Point2d(x - 2, y + 2), Point2d(x + 2, y - 2), marker_style),
                    Primitive.circle(point, 2, marker_style),
                ))
            if show_labels:
                primitives.append(Primitive.text(
                    Point2d(x + 3, y + 3), f"{name} (STA {station:.2f})", 1.5, style=label_style,
                ))

        if show_labels and turnout_name and geometry.ps_point is not None:
            x, y = geometry.ps_point.x, geometry.ps_point.y
            frog = f"1/{1 / math.tan(geometry.branch_angle):g}" if geometry.branch_angle > 0 else ""
            info = f"L={geometry.lead_length:.1f}m, R={geometry.radius:.1f}m"
            rows = [*turnout_name.splitlines(), frog, info]
            primitives.extend(
                Primitive.text(Point2d(x, y + 10 + 2.5 * index), row, 2, style=label_style)
                for index, row in enumerate(reversed(rows)) if row
            )

        for layer, color in {p.style.layer: p.style.color for p in primitives}.items():
            scene = scene.add_layer(Layer(layer, color=color))
        return scene.add_all(primitives) if primitives else scene
