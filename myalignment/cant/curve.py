# cant/curve.py
from dataclasses import dataclass, field, replace
from enum import Enum

class CantPivotMethod(Enum):
    CENTERLINE = "centerline"
    LEFT_RAIL = "left_rail"
    RIGHT_RAIL = "right_rail"

@dataclass(frozen=True, slots=True)
class CantCriticalStation:
    """캔트 임계 측점 (C3D SuperelevationCriticalStation 호환)."""
    station: float = 0.0
    cant_value: float = 0.0          # 우측 - 좌측 레일 표고차 (m)
    left_rail_delta: float = 0.0     # 좌측 레일 표고차
    right_rail_delta: float = 0.0    # 우측 레일 표고차
    is_full_cant: bool = False

@dataclass(frozen=True, slots=True)
class CantCurve:
    """하나의 곡선 구간에 대한 캔트 데이터 (불변)."""
    name: str = ""
    start_station: float = 0.0
    end_station: float = 0.0
    pivot_method: CantPivotMethod = CantPivotMethod.CENTERLINE
    critical_stations: tuple[CantCriticalStation, ...] = field(default_factory=tuple)

    @property
    def length(self) -> float:
        return self.end_station - self.start_station

    def _with_rail_deltas(self, critical: CantCriticalStation) -> CantCriticalStation:
        if critical.left_rail_delta or critical.right_rail_delta:
            return critical

        value = critical.cant_value
        if self.pivot_method is CantPivotMethod.LEFT_RAIL:
            left, right = 0.0, value
        elif self.pivot_method is CantPivotMethod.RIGHT_RAIL:
            left, right = -value, 0.0
        else:
            left, right = -value / 2, value / 2
        return replace(critical, left_rail_delta=left, right_rail_delta=right)

    def cant_at(self, station: float) -> CantCriticalStation | None:
        """레일 표고 변위를 포함한 캔트를 선형 보간한다."""
        critical = self.critical_stations
        if not critical:
            return None
        if self.end_station > self.start_station and not (
            self.start_station <= station <= self.end_station
        ):
            return None
        if station <= critical[0].station:
            return self._with_rail_deltas(critical[0])
        for start, end in zip(critical, critical[1:]):
            if station == end.station:
                return self._with_rail_deltas(end)
            if start.station < station < end.station:
                a = self._with_rail_deltas(start)
                b = self._with_rail_deltas(end)
                t = (station - a.station) / (b.station - a.station)
                return CantCriticalStation(
                    station=station,
                    cant_value=a.cant_value + t * (b.cant_value - a.cant_value),
                    left_rail_delta=a.left_rail_delta + t * (b.left_rail_delta - a.left_rail_delta),
                    right_rail_delta=a.right_rail_delta + t * (b.right_rail_delta - a.right_rail_delta),
                )
        return self._with_rail_deltas(critical[-1])
