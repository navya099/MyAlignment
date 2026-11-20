from __future__ import annotations

from typing import TYPE_CHECKING

from myalignment.cant.curve import CantPivotMethod
from myalignment.profile.cant_band_extractor import CantBandSegmentExtractor
from myalignment.profile.cant_band_segment import CantBandSegment
from myalignment.profile.cant_band_style import CantBandStyle
from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene
from myalignment.render.viewport import Viewport, ViewportType
from myalignment.superelevation.critical_station import TransitionRegionType

if TYPE_CHECKING:
    from myalignment.rail.rail_alignment import RailAlignment


_REGION_LABELS = {
    TransitionRegionType.NORMAL: "N",
    TransitionRegionType.TRANSITION_IN: "TI",
    TransitionRegionType.FULL_SUPERELEVATION: "FC",
    TransitionRegionType.TRANSITION_OUT: "TO",
}
_PIVOT_LABELS = {
    CantPivotMethod.CENTERLINE: "Center",
    CantPivotMethod.LEFT_RAIL: "LeftRail",
    CantPivotMethod.RIGHT_RAIL: "RightRail",
}


class CantBandRenderer:
    """캔트 구간을 종단 뷰 범위로 자르고 구간별 텍스트와 틱을 그린다."""

    @classmethod
    def render(
        cls, scene: Scene, alignment: RailAlignment, band_y_base: float,
        style: CantBandStyle, vertical_exaggeration: float = 10.0,
        start_station: float | None = None, end_station: float | None = None,
    ) -> Scene:
        start = max(alignment.start_station, start_station) if start_station is not None else alignment.start_station
        end = min(alignment.end_station, end_station) if end_station is not None else alignment.end_station
        if start >= end:
            return scene

        extracted = CantBandSegmentExtractor.extract(alignment.cant_curves)
        clipped = []
        cursor = start
        for segment in extracted:
            left, right = max(cursor, segment.start_station), min(end, segment.end_station)
            if left >= right:
                continue
            if cursor < left:
                clipped.append((CantBandSegment(cursor, left), cursor, left))
            clipped.append((segment, left, right))
            cursor = right
        if not clipped:
            return scene
        if cursor < end:
            clipped.append((CantBandSegment(cursor, end), cursor, end))

        viewport = Viewport(ViewportType.PROFILE, vertical_exaggeration)
        top, bottom = band_y_base, band_y_base - style.band_height
        frame_style = Style(color=style.normal_color, layer=style.layer, lineweight=0.2)
        primitives = [
            Primitive.line(viewport.project(x, bottom), viewport.project(x, top), frame_style)
            for x in (start, end)
        ]
        value_marks = set()
        ticks = set()
        text_style = Style(color=style.text_color, layer=style.layer)
        height = style.text_height * vertical_exaggeration

        for segment, left, right in clipped:
            middle = (left + right) / 2
            segment_style = Style(color=style.color_for_region(segment.region_type), layer=style.layer, lineweight=0.3)
            for y in (bottom, top):
                primitives.append(Primitive.line(viewport.project(left, y), viewport.project(right, y), segment_style))
            for station in (left, right):
                if station not in ticks and station in (segment.start_station, segment.end_station):
                    ticks.add(station)
                    primitives.append(Primitive.line(
                        viewport.project(station, top), viewport.project(station, top + style.tick_length),
                        segment_style,
                    ))
                if style.show_cant_value:
                    value = cls._format_cant(segment.cant_at(station), style.unit)
                    if (station, value) not in value_marks:
                        value_marks.add((station, value))
                        primitives.append(Primitive.text(viewport.project(station, bottom + .1 * style.band_height),
                                                         value, height, style=text_style))

            if style.show_cant_value and segment.region_type in (
                TransitionRegionType.TRANSITION_IN, TransitionRegionType.TRANSITION_OUT,
            ):
                primitives.append(Primitive.text(
                    viewport.project(middle, bottom + .4 * style.band_height),
                    cls._format_cant(segment.cant_at(middle), style.unit), height, style=text_style,
                ))
            labels = []
            if style.show_region_label:
                labels.append(_REGION_LABELS[segment.region_type])
            if style.show_pivot and segment.pivot_method is not None:
                labels.append(f"P: {_PIVOT_LABELS[segment.pivot_method]}")
            if labels:
                primitives.append(Primitive.text(
                    viewport.project(middle, bottom + .7 * style.band_height),
                    " | ".join(labels), height, style=segment_style,
                ))
        return scene.add_layer(Layer(style.layer, color=style.normal_color)).add_all(primitives)

    @staticmethod
    def _format_cant(value: float, unit: str) -> str:
        return f"{value / 1000:.3f} m" if unit == "m" else f"{value:.0f} mm"
