from __future__ import annotations

from collections.abc import Sequence
import math
from typing import TYPE_CHECKING

from myalignment.render._rail_3d import rail_polylines, rail_ties, rail_top, vertical_marker
from myalignment.render.primitives_3d import Style3D
from myalignment.render.scene_3d import Scene3D
from myalignment.turnout.geometry import TurnoutGeometry, TurnoutGeometryCalculator

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.turnout.turnout import Turnout


class Turnout3DRenderer:
    """공통 평면 기하를 사용해 레일, 침목과 마커를 3D 와이어로 배치한다."""

    MAIN_RAIL_LAYER = "C-TURNOUT-3D-MAIN"
    BRANCH_RAIL_LAYER = "C-TURNOUT-3D-BRANCH"
    TIE_LAYER = "C-TURNOUT-3D-TIE"
    MARKER_LAYER = "C-TURNOUT-3D-MARKER"

    RAIL_HEIGHT = 0.15
    TIE_SPACING = 0.6
    TIE_OVERHANG = 0.3

    @classmethod
    def render_3d(
        cls,
        scene: Scene3D,
        geometry: TurnoutGeometry,
        elevation: float = 0.0,
        rail_elevation: float = RAIL_HEIGHT,
        gauge: float | None = None,
        show_ties: bool = True,
        show_markers: bool = True,
        *,
        tie_spacing: float = TIE_SPACING,
        track_levels: Sequence[Sequence[float]] | None = None,
        marker_levels: Sequence[float] | None = None,
    ) -> Scene3D:
        """기준 표고와 그 위 레일 높이를 적용한다.

        gauge를 지정하는 경우 기하의 궤간과 일치해야 한다. 침목은
        두 레일의 중점 경로를 따라 tie_spacing 간격으로 배치한다.
        track_levels는 본선과 분기선 순서의 샘플별 표고 오프셋이다.
        marker_levels는 geometry.markers 순서의 표고 오프셋이다.
        """
        if not geometry.is_valid:
            raise ValueError(geometry.error_message)
        top = rail_top(elevation, rail_elevation, tie_spacing)
        if gauge is not None and not math.isclose(gauge, geometry.gauge, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("gauge must match turnout geometry")
        if track_levels is not None and len(track_levels) != 2:
            raise ValueError("track_levels must contain the main and branch tracks")

        primitives = []
        tie_style = Style3D(color=6, layer=cls.TIE_LAYER, lineweight=0.3)
        for index, (layer, color, left, right) in enumerate((
            (cls.MAIN_RAIL_LAYER, 7, geometry.main_left_rail, geometry.main_right_rail),
            (cls.BRANCH_RAIL_LAYER, 3, geometry.branch_left_rail, geometry.branch_right_rail),
        )):
            levels = None if track_levels is None else track_levels[index]
            style = Style3D(color=color, layer=layer, lineweight=0.5)
            primitives.extend(rail_polylines(left, right, top, style, levels=levels))
            if show_ties:
                primitives.extend(rail_ties(
                    left, right, elevation + rail_elevation / 2, tie_spacing, tie_style,
                    overhang=cls.TIE_OVERHANG, levels=levels,
                ))

        if show_markers:
            style = Style3D(color=1, layer=cls.MARKER_LAYER)
            markers = geometry.markers
            levels = (0.0,) * len(markers) if marker_levels is None else marker_levels
            primitives.extend(
                vertical_marker(p, elevation + dz, 2, style)
                for (_, p, _), dz in zip(markers, levels, strict=True)
            )
        return scene.add_all(primitives) if primitives else scene

    @classmethod
    def render_turnout_set_3d(
        cls,
        scene: Scene3D,
        turnouts: Sequence[Turnout],
        alignment: Alignment,
        elevation: float = 0.0,
        rail_elevation: float = RAIL_HEIGHT,
    ) -> Scene3D:
        """같은 본선에 배치된 턴아웃을 그린다. 유효하지 않은 기하는 오류로 알린다."""
        primitives = []
        for turnout in turnouts:
            geometry = TurnoutGeometryCalculator.calculate(alignment, turnout)
            if not geometry.is_valid:
                raise ValueError(f"{turnout.name}: {geometry.error_message}")
            primitives.extend(cls.render_3d(Scene3D(), geometry, elevation, rail_elevation).primitives)
        return scene.add_all(primitives) if primitives else scene
