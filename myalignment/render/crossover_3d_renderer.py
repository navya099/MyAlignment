from __future__ import annotations

from collections.abc import Sequence
import math
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.render._rail_3d import rail_polylines, rail_ties, rail_top, vertical_marker
from myalignment.render.primitives_3d import Point3D, Primitive3D, Style3D
from myalignment.render.scene_3d import Scene3D

if TYPE_CHECKING:
    from myalignment.turnout.crossover_geometry import CrossoverGeometry


class Crossover3DRenderer:
    """공통 평면 기하로 크로스오버의 레일과 침목을 3D 와이어로 배치한다."""

    MAIN1_LAYER = "C-CROSSOVER-3D-MAIN1"
    MAIN2_LAYER = "C-CROSSOVER-3D-MAIN2"
    CONNECT_LAYER = "C-CROSSOVER-3D-CONNECT"
    TIE_LAYER = "C-CROSSOVER-3D-TIE"
    DIAMOND_LAYER = "C-CROSSOVER-3D-DIAMOND"
    MARKER_LAYER = "C-CROSSOVER-3D-MARKER"

    RAIL_ELEVATION = 0.15
    TIE_SPACING = 0.6
    TIE_OVERHANG = 0.3
    MARKER_HEIGHT = 3.0

    @classmethod
    def render_3d(
        cls,
        scene: Scene3D,
        geometry: CrossoverGeometry,
        elevation: float = 0.0,
        gauge: float | None = None,
        show_ties: bool = True,
        show_markers: bool = True,
        show_diamond: bool = True,
        *,
        rail_elevation: float = RAIL_ELEVATION,
        tie_spacing: float = TIE_SPACING,
        track_levels: Sequence[Sequence[float]] | None = None,
        marker_levels: Sequence[float] | None = None,
        diamond_level: float = 0.0,
    ) -> Scene3D:
        """단일 또는 이중 크로스오버를 기존 Scene3D에 추가한다.

        CrossoverGeometryCalculator로 계산한 레일을 사용한다.
        레일 상단은 elevation에 rail_elevation을 더한 표고다.
        gauge를 지정하는 경우 좌표 계산에 사용한 궤간과 일치해야 한다.
        track_levels는 두 본선과 연결 경로 순서의 샘플별 표고 오프셋이다.
        marker_levels는 geometry.turnout_markers 순서의 표고 오프셋이다.
        """
        if not geometry.is_valid:
            raise ValueError(geometry.error_message)
        if not geometry.connecting_rails:
            raise ValueError("use CrossoverGeometryCalculator.calculate to generate the plan rails")
        if gauge is not None and (
            geometry.gauge is None or not math.isclose(gauge, geometry.gauge, rel_tol=0, abs_tol=1e-9)
        ):
            raise ValueError("gauge must match crossover geometry")
        top = rail_top(elevation, rail_elevation, tie_spacing)
        if track_levels is not None and len(track_levels) != 2 + len(geometry.connecting_rails):
            raise ValueError("track_levels must contain both main tracks and each connection")

        primitives = []
        tie_style = Style3D(color=6, layer=cls.TIE_LAYER, lineweight=0.3)
        track_index = 0
        for style, pairs in (
            (Style3D(color=7, layer=cls.MAIN1_LAYER, lineweight=0.6),
             ((geometry.main1_left_rail, geometry.main1_right_rail),)),
            (Style3D(color=5, layer=cls.MAIN2_LAYER, lineweight=0.6),
             ((geometry.main2_left_rail, geometry.main2_right_rail),)),
            (Style3D(color=3, layer=cls.CONNECT_LAYER, lineweight=0.5), geometry.connecting_rails),
        ):
            for left, right in pairs:
                levels = None if track_levels is None else track_levels[track_index]
                track_index += 1
                primitives.extend(rail_polylines(left, right, top, style, levels=levels))
                if show_ties:
                    primitives.extend(rail_ties(
                        left, right, elevation + rail_elevation / 2, tie_spacing, tie_style,
                        overhang=cls.TIE_OVERHANG, levels=levels,
                    ))

        if show_markers:
            marker_style = Style3D(color=2, layer=cls.MARKER_LAYER, lineweight=0.5)
            markers = geometry.turnout_markers
            levels = (0.0,) * len(markers) if marker_levels is None else marker_levels
            for (_, point, station), dz in zip(markers, levels, strict=True):
                # PS and PF have source stations. PC uses the branch path instead.
                if station is not None:
                    base = elevation + dz
                    primitives.append(vertical_marker(point, base, cls.MARKER_HEIGHT, marker_style))
                    primitives.extend(cls._cross(point, base + cls.MARKER_HEIGHT, 1.5, marker_style))

        if show_diamond and geometry.diamond_center is not None:
            diamond_style = Style3D(color=1, layer=cls.DIAMOND_LAYER, lineweight=0.8)
            center = geometry.diamond_center
            base = elevation + diamond_level
            primitives.append(vertical_marker(center, base, cls.MARKER_HEIGHT, diamond_style))
            primitives.extend(cls._cross(center, base + 0.5, 3.0, diamond_style))

        return scene.add_all(primitives) if primitives else scene

    @staticmethod
    def _cross(point: Point2d, elevation: float, size: float, style: Style3D) -> tuple[Primitive3D, Primitive3D]:
        x, y = point.x, point.y
        return (
            Primitive3D.line(Point3D(x - size, y - size, elevation), Point3D(x + size, y + size, elevation), style),
            Primitive3D.line(Point3D(x - size, y + size, elevation), Point3D(x + size, y - size, elevation), style),
        )
