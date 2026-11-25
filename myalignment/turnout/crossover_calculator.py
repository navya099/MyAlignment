from __future__ import annotations

from dataclasses import replace
import math
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.alignment.intersection import line_line_intersection
from myalignment.turnout.crossover_geometry import ConnectionGeometry, CrossoverGeometry
from myalignment.turnout.geometry import TurnoutGeometryCalculator, _offset_branch_rails, _sample_main_rails

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.turnout.crossover import Crossover


def _diamond_center(first: ConnectionGeometry, second: ConnectionGeometry) -> Point2d | None:
    if min(first.length, second.length) <= 0:
        return None
    lines = (first, second)
    directions = tuple(
        (line.end_point.x - line.start_point.x, line.end_point.y - line.start_point.y)
        for line in lines
    )
    first_angle, second_angle = (math.atan2(dy, dx) for dx, dy in directions)
    point = line_line_intersection(first.start_point, first_angle, second.start_point, second_angle)
    if point is None:
        return None
    tolerance = max(1e-8, 8 * math.ulp(max(abs(point.x), abs(point.y))))
    for line, (dx, dy) in zip(lines, directions):
        run, rise = dx / line.length, dy / line.length
        x, y = point.x - line.start_point.x, point.y - line.start_point.y
        along = x * run + y * rise
        if abs(x * rise - y * run) > tolerance or not -tolerance <= along <= line.length + tolerance:
            return None
    return point


class CrossoverGeometryCalculator:
    """기존 크로스오버 기하에 2D와 3D에 공통으로 쓰는 레일과 마커를 추가한다."""

    @classmethod
    def calculate(
        cls,
        crossover: Crossover,
        alignment1: Alignment,
        alignment2: Alignment,
        gauge: float | None = None,
        *,
        sample_step: float = 0.5,
        extension: float = 30.0,
    ) -> CrossoverGeometry:
        """단일 또는 이중 크로스오버의 좌우 레일 좌표를 계산한다.

        본선 이름과 순서를 크로스오버에 맞춘다. 궤간을 생략한 경우
        철도 선형에 설정된 궤간 또는 표준 궤간을 사용한다.
        기하가 유효하지 않으면 원본 오류 메시지를 반환한다.
        """
        if not math.isfinite(sample_step) or sample_step <= 0:
            raise ValueError("sample_step must be finite and positive")
        if not math.isfinite(extension) or extension < 0:
            raise ValueError("extension must be finite and nonnegative")
        if (alignment1.name, alignment2.name) != (crossover.source_alignment1_name, crossover.source_alignment2_name):
            raise ValueError("source alignments must match the crossover names and order")
        if gauge is None:
            gauge1 = getattr(alignment1, "gauge", None)
            gauge2 = getattr(alignment2, "gauge", None)
            if gauge1 is not None and gauge2 is not None and not math.isclose(gauge1, gauge2, rel_tol=0, abs_tol=1e-9):
                raise ValueError("source alignment gauges must match")
            gauge = gauge1 if gauge1 is not None else gauge2
            if gauge is None:
                gauge = TurnoutGeometryCalculator.STANDARD_GAUGE
        if not math.isfinite(gauge) or gauge <= 0:
            raise ValueError("gauge must be finite and positive")

        base = crossover.compute_geometry(alignment1, alignment2)
        if not base.is_valid:
            return base

        # DOUBLE paths are ordered (T1,T2), (T3,T4). T3 belongs to main 2.
        sources = (alignment1, alignment2, alignment2, alignment1)
        breaks = {alignment1.name: [], alignment2.name: []}
        markers = []
        curves = (curve for path in base.paths for curve in (path.first, path.second))
        run = crossover.turnout1.turnout_type.run
        for index, (source, turnout, curve) in enumerate(zip(sources, crossover.turnouts, curves), 1):
            ps = turnout.station_on_source
            pf = ps - run if curve.reverse else ps + run
            try:
                pf_point = source.point_at(pf)
            except ValueError as error:
                return replace(base, is_valid=False, error_message=f"T{index}-PF: {error}")
            breaks[source.name].extend((ps, pf))
            pc = curve.connector_point
            markers.extend((
                (f"T{index}-PS", Point2d(curve.toe.x, curve.toe.y), ps),
                (f"T{index}-PF", pf_point, pf),
                (f"T{index}-PC", Point2d(pc.x, pc.y), None),
            ))

        main1_left, main1_right = cls._main_rails(alignment1, breaks[alignment1.name], gauge, sample_step, extension)
        main2_left, main2_right = cls._main_rails(alignment2, breaks[alignment2.name], gauge, sample_step, extension)
        rails = tuple(_offset_branch_rails(path.sample_frames(sample_step), gauge) for path in base.paths)
        center = None
        length1 = length2 = 0.0
        if len(base.connections) == 2:
            first, second = base.connections
            center = _diamond_center(first, second)
            if center is not None:
                length1, length2 = first.length, second.length
        return replace(
            base, gauge=gauge, main1_left_rail=main1_left, main1_right_rail=main1_right,
            main2_left_rail=main2_left, main2_right_rail=main2_right,
            connecting_rails=rails, turnout_markers=tuple(markers),
            diamond_center=center, diamond_diagonal1=length1, diamond_diagonal2=length2,
        )

    @staticmethod
    def _main_rails(alignment, breaks, gauge, step, extension):
        start = max(alignment.start_station, min(breaks) - extension)
        end = min(alignment.end_station, max(breaks) + extension)
        return _sample_main_rails(alignment, sorted({start, end, *breaks}), gauge, step)
