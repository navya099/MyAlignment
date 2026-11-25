from __future__ import annotations

from dataclasses import dataclass
import math
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.turnout.geometry_sampling import SamplePoint, TurnoutCurve

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.turnout.turnout import Turnout


@dataclass(frozen=True, slots=True)
class TurnoutGeometry:
    """PS와 공칭 PF·PC, 본선과 분기선의 좌우 레일을 담는 기하 결과.

    PF는 분기 곡선 끝의 종방향 길이에 해당하는 본선 위치이며, PC는
    분기 중심선에서 곡선이 끝나는 점이다. PC 측점은 PS를 0으로 하는
    분기 중심선 거리다.
    """

    ps_station: float = 0.0
    ps_point: Point2d | None = None
    ps_azimuth: float = 0.0
    pf_point: Point2d | None = None
    pf_station: float = 0.0
    pc_point: Point2d | None = None
    pc_station: float = 0.0
    branch_azimuth: float = 0.0
    branch_angle: float = 0.0
    lead_length: float = 0.0
    radius: float = 0.0
    gauge: float = 1.435
    main_left_rail: tuple[Point2d, ...] = ()
    main_right_rail: tuple[Point2d, ...] = ()
    branch_left_rail: tuple[Point2d, ...] = ()
    branch_right_rail: tuple[Point2d, ...] = ()
    is_valid: bool = True
    error_message: str = ""

    def __post_init__(self):
        if not self.is_valid and not self.error_message:
            raise ValueError("invalid turnout geometry requires error_message")

    @property
    def markers(self) -> tuple[tuple[str, Point2d, float], ...]:
        """표시 가능한 마커의 이름, 좌표와 측점."""
        return tuple(
            (name, point, station)
            for name, point, station in (
                ("PS", self.ps_point, self.ps_station),
                ("PF", self.pf_point, self.pf_station),
                ("PC", self.pc_point, self.pc_station),
            )
            if point is not None
        )


def _interval(start: float, end: float, step: float):
    count = math.ceil((end - start) / step)
    return (start + (end - start) * i / count for i in range(count))


class TurnoutGeometryCalculator:
    """기존 직선 리드·원곡선 모델에서 표시용 레일을 생성한다."""

    STANDARD_GAUGE = 1.435

    @classmethod
    def calculate(
        cls,
        alignment: Alignment,
        turnout: Turnout,
        gauge: float | None = None,
        *,
        sample_step: float = 0.5,
        extension: float = 30.0,
    ) -> TurnoutGeometry:
        """본선과 분기선의 레일을 표본화한다.

        궤간을 생략하면 철도 선형의 궤간 또는 표준 궤간을 사용한다.
        extension은 PS 앞과 PF 뒤의 본선, PC 뒤의 분기선 표시 길이다.
        본선의 표시 범위는 선형 끝에서 잘린다. PS 또는 PF가 선형
        범위 밖이면 유효하지 않은 결과와 오류 메시지를 반환한다.
        """
        gauge = getattr(alignment, "gauge", cls.STANDARD_GAUGE) if gauge is None else gauge
        if not (math.isfinite(gauge) and gauge > 0):
            raise ValueError("gauge must be finite and positive")
        if not (math.isfinite(sample_step) and sample_step > 0):
            raise ValueError("sample_step must be finite and positive")
        if not (math.isfinite(extension) and extension >= 0):
            raise ValueError("extension must be finite and nonnegative")
        if turnout.source_alignment_name != alignment.name:
            return TurnoutGeometry(is_valid=False, error_message="turnout source alignment does not match")

        kind = turnout.turnout_type
        ps_station = turnout.station_on_source
        pf_station = ps_station + kind.run
        try:
            ps = alignment.point_at(ps_station)
            azimuth = alignment.tangent_at(ps_station)
            pf = alignment.point_at(pf_station)
        except ValueError as error:
            return TurnoutGeometry(ps_station=ps_station, pf_station=pf_station, is_valid=False, error_message=str(error))

        curve = TurnoutCurve(
            SamplePoint(ps.x, ps.y), azimuth, kind.lead_length, kind.radius,
            kind.frog_angle, turnout.side.sign,
        )
        pc = curve.connector_point
        branch_azimuth = azimuth + turnout.side.sign * kind.frog_angle
        branch_frames = curve.sample_frames(sample_step)
        # A zero-length lead produces two samples at the PS.
        if kind.lead_length == 0:
            branch_frames = branch_frames[1:]
        branch_frames += tuple(
            (SamplePoint(pc.x + distance * math.cos(branch_azimuth),
                         pc.y + distance * math.sin(branch_azimuth)), branch_azimuth)
            for distance in (*_interval(0.0, extension, sample_step), extension)
            if distance > 0
        )

        start = max(alignment.start_station, ps_station - extension)
        end = min(alignment.end_station, pf_station + extension)
        stations = (*_interval(start, ps_station, sample_step), *_interval(ps_station, pf_station, sample_step),
                    *_interval(pf_station, end, sample_step), end)
        half = gauge / 2
        rails = []
        for offset in (-half, half):
            rails.append(tuple(alignment.point_at(station, offset) for station in stations))
        for offset in (half, -half):
            rails.append(tuple(
                Point2d(point.x - offset * math.sin(heading), point.y + offset * math.cos(heading))
                for point, heading in branch_frames
            ))
        main_left, main_right, branch_left, branch_right = rails
        return TurnoutGeometry(
            ps_station=ps_station, ps_point=ps, ps_azimuth=azimuth,
            pf_station=pf_station, pf_point=pf, pc_station=kind.lead_length + kind.arc_length,
            pc_point=Point2d(pc.x, pc.y), branch_azimuth=branch_azimuth, branch_angle=kind.frog_angle,
            lead_length=kind.lead_length, radius=kind.radius, gauge=gauge,
            main_left_rail=main_left, main_right_rail=main_right,
            branch_left_rail=branch_left, branch_right_rail=branch_right,
        )
