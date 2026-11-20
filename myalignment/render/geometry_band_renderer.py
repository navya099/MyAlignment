from __future__ import annotations

import math
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.profile.band_style import GeometryBandStyle
from myalignment.profile.geometry_extractor import GeometryPointExtractor
from myalignment.profile.geometry_point_type import GeometryPointType
from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene
from myalignment.render.viewport import Viewport, ViewportType

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment


_POINT_COLORS = {
    GeometryPointType.TS: 5,
    GeometryPointType.ST: 5,
    GeometryPointType.SC: 6,
    GeometryPointType.CS: 6,
    GeometryPointType.BC: 4,
    GeometryPointType.EC: 4,
}


class HorizontalGeometryBandRenderer:
    """수평 선형의 전이점을 틱, 연결선과 레이블로 표시한다."""

    @classmethod
    def render(
        cls,
        scene: Scene,
        alignment: Alignment,
        band_y_base: float,
        style: GeometryBandStyle,
        vertical_exaggeration: float = 10.0,
        *,
        station_range: tuple[float, float] | None = None,
    ) -> Scene:
        """band_y_base는 수직 과장을 적용하기 전 밴드 상단 표고다."""
        viewport = Viewport(ViewportType.PROFILE, vertical_exaggeration)
        start, end = station_range or (alignment.start_station, alignment.end_station)
        if not alignment.is_valid or start >= end:
            return scene

        top, bottom = band_y_base, band_y_base - style.band_height
        frame_style = Style(color=style.tick_color, layer=style.layer, lineweight=0.2)
        tick_style = Style(color=style.tick_color, layer=style.layer, lineweight=style.tick_lineweight)
        text_style = Style(color=style.text_color, layer=style.layer)
        primitives = [
            Primitive.line(viewport.project(start, y), viewport.project(end, y), frame_style)
            for y in (top, bottom)
        ]

        points = GeometryPointExtractor.extract(alignment)
        for point in points:
            x = point.station
            if point.point_type.value not in style.visible_types or not start <= x <= end:
                continue
            point_style = Style(
                color=_POINT_COLORS.get(point.point_type, style.tick_color),
                layer=style.layer, lineweight=0.3,
            )
            primitives.extend((
                Primitive.line(viewport.project(x, top), viewport.project(x, top + style.tick_length), tick_style),
                Primitive.line(viewport.project(x, bottom), viewport.project(x, bottom - style.tick_length), tick_style),
                Primitive.line(viewport.project(x, top), viewport.project(x, bottom), point_style),
            ))
            text_at = viewport.project(x, (top + bottom) / 2 + style.text_offset_y)
            height = style.text_height * vertical_exaggeration
            symbol, _, radius = point.label.partition("\\P")
            primitives.append(Primitive.text(text_at, symbol, height, math.pi / 2, style=text_style))
            if radius:
                radius_at = Point2d(text_at.x + height, text_at.y)
                primitives.append(Primitive.text(radius_at, radius, height, math.pi / 2, style=text_style))

        if not points:
            # 전이점이 없는 선형도 기존 요소 길이 표기를 유지한다.
            for entity in alignment.entities:
                low, high = max(start, entity.start_station), min(end, entity.end_station)
                if low < high:
                    primitives.append(Primitive.text(
                        viewport.project((low + high) / 2, (top + bottom) / 2),
                        f"{entity.entity_type.name} {entity.length:.2f} m",
                        style.text_height * vertical_exaggeration, style=text_style,
                    ))

        return scene.add_layer(Layer(style.layer, color=style.tick_color)).add_all(primitives)
