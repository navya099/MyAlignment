from __future__ import annotations

from collections.abc import Sequence
import math
from typing import TYPE_CHECKING

from myalignment.render.primitives_3d import Point3D, Primitive3D, Style3D
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
    ) -> Scene3D:
        """기준 표고와 그 위 레일 높이를 적용한다.

        gauge를 지정하는 경우 기하의 궤간과 일치해야 한다. 침목은
        두 레일의 중점 경로를 따라 tie_spacing 간격으로 배치한다.
        """
        if not geometry.is_valid:
            raise ValueError(geometry.error_message)
        top = elevation + rail_elevation
        if not math.isfinite(top) or rail_elevation < 0:
            raise ValueError("elevation and rail_elevation must be finite; rail_elevation must be nonnegative")
        if gauge is not None and not math.isclose(gauge, geometry.gauge, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("gauge must match turnout geometry")
        if not math.isfinite(tie_spacing) or tie_spacing <= 0:
            raise ValueError("tie_spacing must be finite and positive")

        primitives = []
        for layer, color, left, right in (
            (cls.MAIN_RAIL_LAYER, 7, geometry.main_left_rail, geometry.main_right_rail),
            (cls.BRANCH_RAIL_LAYER, 3, geometry.branch_left_rail, geometry.branch_right_rail),
        ):
            style = Style3D(color=color, layer=layer, lineweight=0.5)
            for rail in (left, right):
                if len(rail) >= 2:
                    primitives.append(Primitive3D.polyline((Point3D(p.x, p.y, top) for p in rail), style=style))
            if show_ties:
                primitives.extend(cls._ties(left, right, elevation + rail_elevation / 2, tie_spacing))

        if show_markers:
            style = Style3D(color=1, layer=cls.MARKER_LAYER)
            primitives.extend(
                Primitive3D.line(Point3D(p.x, p.y, elevation), Point3D(p.x, p.y, elevation + 2), style)
                for _, p, _ in geometry.markers
            )
        return scene.add_all(primitives) if primitives else scene

    @classmethod
    def _ties(cls, left, right, elevation: float, spacing: float):
        style = Style3D(color=6, layer=cls.TIE_LAYER, lineweight=0.3)
        if len(left) != len(right):
            raise ValueError("turnout rails must have matching samples for ties")

        travelled = 0.0
        index = 0
        for l0, l1, r0, r1 in zip(left, left[1:], right, right[1:]):
            length = math.hypot(((l1.x - l0.x) + (r1.x - r0.x)) / 2,
                                ((l1.y - l0.y) + (r1.y - r0.y)) / 2)
            if length == 0:
                continue
            end = travelled + length
            while index * spacing <= end:
                fraction = (index * spacing - travelled) / length
                lx, ly = l0.x + (l1.x - l0.x) * fraction, l0.y + (l1.y - l0.y) * fraction
                rx, ry = r0.x + (r1.x - r0.x) * fraction, r0.y + (r1.y - r0.y) * fraction
                width = math.hypot(lx - rx, ly - ry)
                if width > 0:
                    dx = cls.TIE_OVERHANG * (lx - rx) / width
                    dy = cls.TIE_OVERHANG * (ly - ry) / width
                    yield Primitive3D.line(
                        Point3D(lx + dx, ly + dy, elevation), Point3D(rx - dx, ry - dy, elevation), style,
                    )
                index += 1
            travelled = end

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
