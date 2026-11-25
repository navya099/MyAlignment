from __future__ import annotations

from collections.abc import Iterable
import math
from typing import TYPE_CHECKING

from myalignment.render.slope_pattern_2d_renderer import _draw_patterns
from myalignment.section.section_view_style import section_projection

if TYPE_CHECKING:
    from myalignment.corridor.slope_pattern import SlopePattern
    from myalignment.render.scene import Scene
    from myalignment.section.section_view_data import SectionViewData
    from myalignment.section.section_view_style import SectionViewStyle


def _section_coordinates(pattern, point):
    start, end = pattern.start_point, pattern.end_point
    dx, dy = end.x - start.x, end.y - start.y
    length_squared = dx * dx + dy * dy
    if length_squared == 0:
        return pattern.start_offset, point.z
    fraction = ((point.x - start.x) * dx + (point.y - start.y) * dy) / length_squared
    return pattern.start_offset + fraction * (pattern.end_offset - pattern.start_offset), point.z


class SlopePatternSectionRenderer:
    """사면 패턴을 횡거·표고 좌표로 바꾸어 횡단 뷰에 추가한다."""

    @classmethod
    def render_patterns(
        cls, scene: Scene, patterns: Iterable[SlopePattern], data: SectionViewData,
        view_style: SectionViewStyle, min_elev: float | None = None, max_elev: float | None = None,
    ) -> Scene:
        """기존 단면의 축척과 해당 측점의 패턴을 사용한다."""
        matching = cls._at_station(patterns, data.station)
        if not matching:
            return scene
        *_, plot = section_projection(data, view_style, min_elev, max_elev)
        return cls._render_projected(scene, matching, plot, view_style.text_height)

    @staticmethod
    def _at_station(patterns, station):
        return tuple(p for p in patterns if math.isclose(p.station, station, rel_tol=0, abs_tol=1e-8))

    @staticmethod
    def _extent_points(patterns):
        return (
            _section_coordinates(pattern, point)
            for pattern in patterns for element in pattern.elements for point in element.points
        )

    @staticmethod
    def _render_projected(scene, patterns, plot, text_height):
        return _draw_patterns(scene, patterns, lambda p, point: plot(*_section_coordinates(p, point)), text_height)
