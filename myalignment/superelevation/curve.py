# superelevation/curve.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import math

from myalignment.superelevation.critical_station import SuperelevationCriticalStation, TransitionRegionType


class PivotMethod(Enum):
    """피벗(회전축) 방법 (C3D 호환)."""
    CENTER_BASELINE = "중심선"
    INSIDE_OF_CURVE = "곡선 내측"
    OUTSIDE_OF_CURVE = "곡선 외측"
    LEFT_SIDE = "좌측"
    RIGHT_SIDE = "우측"
    CENTERS = "중앙"
    MEDIAN_EDGES = "중앙분리대 경계"


@dataclass(frozen=True, slots=True)
class SuperelevationCurve:
    """
    편구배 곡선 (불변).

    C3D의 SuperelevationCurve와 호환.
    - 하나의 원곡선 구간에 대한 편구배 데이터.
    - 임계 측점들의 시퀀스.
    """
    name: str = ""
    start_station: float = 0.0
    end_station: float = 0.0
    pivot_method: PivotMethod = PivotMethod.CENTER_BASELINE
    critical_stations: tuple[SuperelevationCriticalStation, ...] = field(default_factory=tuple)

    def __post_init__(self):
        if self.end_station < self.start_station:
            raise ValueError(f"end < start: {self.end_station} < {self.start_station}")
        # 임계 측점 정렬 검증
        for i in range(len(self.critical_stations) - 1):
            if self.critical_stations[i].station > self.critical_stations[i + 1].station:
                raise ValueError(f"임계 측점 순서 오류: [{i}]")

    @property
    def length(self) -> float:
        return self.end_station - self.start_station

    def critical_station_at(self, station: float) -> SuperelevationCriticalStation | None:
        """측점에 가장 가까운 임계 측점."""
        if not self.critical_stations:
            return None
        return min(self.critical_stations, key=lambda cs: abs(cs.station - station))

    def region_at(self, station: float) -> TransitionRegionType | None:
        """측점의 전이 영역 타입."""
        cs = self.critical_station_at(station)
        return cs.region_type if cs else None