from __future__ import annotations

from cadgeom import Point2d

from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene
from myalignment.section.section_view_data import SectionViewData, section_point_slopes
from myalignment.section.section_view_style import SectionViewStyle, section_projection


class SectionViewGradeBreakRenderer:
    """횡단면에서 0.5%p를 초과하는 구배 변화에 틱과 레이블을 그린다."""

    LAYER = "C-SECTION-GRADEBREAK"

    @classmethod
    def render(
        cls, scene: Scene, data: SectionViewData, view_style: SectionViewStyle,
        min_elev: float | None = None, max_elev: float | None = None,
    ) -> Scene:
        if not data.points or not data.links:
            return scene
        *_, plot = section_projection(data, view_style, min_elev, max_elev)
        return cls._render_projected(scene, data, plot)

    @classmethod
    def _render_projected(cls, scene, data, plot):
        slopes = section_point_slopes(data)
        primitives = []
        style = Style(color=1, layer=cls.LAYER, lineweight=.5)
        for point in data.points:
            incoming, outgoing = slopes.get(point, ((), ()))
            if len(incoming) != 1 or len(outgoing) != 1:
                continue
            change = next(iter(outgoing)) - next(iter(incoming))
            if abs(change) <= .5:
                continue
            anchor = plot(point.offset, point.elevation)
            primitives.extend((
                Primitive.line(Point2d(anchor.x, anchor.y - 2), Point2d(anchor.x, anchor.y + 2), style),
                Primitive.text(Point2d(anchor.x - 5, anchor.y + 3), f"Δ{change:+.1f}%", 1.2, style=style),
            ))
        return scene.add_layer(Layer(cls.LAYER, color=1)).add_all(primitives) if primitives else scene
