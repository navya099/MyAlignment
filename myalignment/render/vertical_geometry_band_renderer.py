from __future__ import annotations

from itertools import groupby
import math
from typing import TYPE_CHECKING

from myalignment.profile.band_style import VerticalGeometryBandStyle
from myalignment.profile.vertical_geometry_extractor import VerticalGeometryExtractor
from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene
from myalignment.render.viewport import Viewport, ViewportType

if TYPE_CHECKING:
    from myalignment.profile.profile import Profile


class VerticalGeometryBandRenderer:
    """종단 기하점의 측점에 틱과 회전 레이블을 배치한다."""

    @classmethod
    def render(
        cls, scene: Scene, profile: Profile, band_y_base: float,
        style: VerticalGeometryBandStyle, vertical_exaggeration: float = 10.0,
    ) -> Scene:
        """band_y_base는 수직 과장을 적용하기 전 밴드 상단 표고다."""
        if not profile.is_valid:
            return scene
        viewport = Viewport(ViewportType.PROFILE, vertical_exaggeration)
        top, bottom = band_y_base, band_y_base - style.band_height
        frame = Style(color=8, layer=style.layer, lineweight=0.2)
        primitives = [
            Primitive.line(viewport.project(profile.start_station, y), viewport.project(profile.end_station, y), frame)
            for y in (top, bottom)
        ]
        points = (
            point for point in VerticalGeometryExtractor.extract(profile)
            if point.label_text in style.visible_types
        )
        text_y = (top + bottom) / 2 + style.text_offset_y
        height = style.text_height * vertical_exaggeration
        for station, group in groupby(points, key=lambda point: point.station):
            marks = tuple(group)
            tick_style = Style(color=style.color_for_type(marks[0].point_type), layer=style.layer, lineweight=0.3)
            for start, end in ((top, top + style.tick_length), (bottom, bottom - style.tick_length), (top, bottom)):
                primitives.append(Primitive.line(
                    viewport.project(station, start), viewport.project(station, end), tick_style,
                ))
            for index, point in enumerate(marks):
                text_style = Style(color=style.color_for_type(point.point_type), layer=style.layer)
                primitives.append(Primitive.text(
                    viewport.project(station + index * height, text_y),
                    point.label_text, height, math.pi / 2, text_style,
                ))
        return scene.add_layer(Layer(style.layer, color=style.pvi_color)).add_all(primitives)
