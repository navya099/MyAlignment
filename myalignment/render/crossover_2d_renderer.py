from __future__ import annotations

from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.render._rail_plan import add_plan_primitives, cross_marker
from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Scene

if TYPE_CHECKING:
    from myalignment.turnout.crossover_geometry import CrossoverGeometry


class Crossover2DRenderer:
    """본선과 연결 레일, 턴아웃 및 교차 마커를 평면도에 추가한다."""

    MAIN1_LAYER = "C-CROSSOVER-MAIN1"
    MAIN2_LAYER = "C-CROSSOVER-MAIN2"
    CONNECT_LAYER = "C-CROSSOVER-CONNECT"
    DIAMOND_LAYER = "C-CROSSOVER-DIAMOND"
    MARKER_LAYER = "C-CROSSOVER-MARKER"
    LABEL_LAYER = "C-CROSSOVER-LABEL"

    @classmethod
    def render_2d(
        cls,
        scene: Scene,
        geometry: CrossoverGeometry,
        crossover_name: str = "",
        show_labels: bool = True,
        show_markers: bool = True,
        show_diamond: bool = True,
    ) -> Scene:
        """CrossoverGeometryCalculator로 계산한 평면도를 기존 Scene에 추가한다."""
        if not geometry.is_valid:
            raise ValueError(geometry.error_message)
        if not geometry.connecting_rails:
            raise ValueError("use CrossoverGeometryCalculator.calculate to generate the plan rails")

        primitives = []
        for layer, color, rails in (
            (cls.MAIN1_LAYER, 7, (geometry.main1_left_rail, geometry.main1_right_rail)),
            (cls.MAIN2_LAYER, 5, (geometry.main2_left_rail, geometry.main2_right_rail)),
            (cls.CONNECT_LAYER, 3, tuple(rail for pair in geometry.connecting_rails for rail in pair)),
        ):
            style = Style(color=color, layer=layer, lineweight=0.5)
            primitives.extend(Primitive.polyline(rail, style=style) for rail in rails if len(rail) >= 2)

        marker_style = Style(color=6, layer=cls.MARKER_LAYER, lineweight=0.5)
        text_style = Style(color=2, layer=cls.LABEL_LAYER)
        for name, point, station in geometry.turnout_markers:
            if show_markers:
                primitives.extend(cross_marker(point, marker_style))
            if show_labels:
                text = name if station is None else f"{name} (STA {station:.2f})"
                primitives.append(Primitive.text(
                    Point2d(point.x + 4, point.y + 4), text, 1.5, style=text_style,
                ))

        center = geometry.diamond_center
        if show_diamond and center is not None:
            diamond_style = Style(color=1, layer=cls.DIAMOND_LAYER, lineweight=0.6)
            primitives.extend(cross_marker(center, diamond_style, radius=3))
            if show_labels:
                primitives.append(Primitive.text(
                    Point2d(center.x + 5, center.y + 5), "DIAMOND", 1.5, style=diamond_style,
                ))

        if show_labels and crossover_name:
            connector = geometry.connections[0]
            start, end = connector.start_point, connector.end_point
            x, y = (start.x + end.x) / 2, (start.y + end.y) / 2
            lengths = " / ".join(f"{connection.length:.1f} m" for connection in geometry.connections)
            rows = [*crossover_name.splitlines(), f"L={lengths}"]
            primitives.extend(
                Primitive.text(Point2d(x, y - 12 - index * 2.5), row, 2, style=text_style)
                for index, row in enumerate(rows) if row
            )

        return add_plan_primitives(scene, primitives)
