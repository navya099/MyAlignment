from __future__ import annotations

from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene

if TYPE_CHECKING:
    from myalignment.corridor.feature_line_manager import CorridorFeatureLineManager


class FeatureLine2DRenderer:
    """코리더 선의 평면 도형과 이름 레이블을 추가한다."""

    @staticmethod
    def render(scene: Scene, manager: CorridorFeatureLineManager) -> Scene:
        """구간별 2D 도형을 기존 장면에 추가한다."""
        primitives = []
        for line in manager:
            if not line.points:
                continue
            spec = line.spec
            style = Style(color=spec.color, layer=spec.layer, lineweight=spec.lineweight) if spec else Style(
                color=7, layer="C-CORRIDOR-FL", lineweight=0.3,
            )
            scene = scene.add_layer(Layer(style.layer, color=style.color))
            for run in line.segments:
                vertices = tuple(Point2d(p.point.x, p.point.y) for p in run)
                if len(vertices) >= 2:
                    primitives.append(Primitive.polyline(vertices, style=style))
                else:
                    primitives.append(Primitive.circle(vertices[0], 0.5, style))
                start = vertices[0]
                if line.name:
                    primitives.append(Primitive.text(
                        Point2d(start.x + 2, start.y + 2), line.name, 1.5, style=style,
                    ))
        return scene.add_all(primitives) if primitives else scene
