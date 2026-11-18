# cant/curve.py
from dataclasses import dataclass, field
from enum import Enum
import math

class CantPivotMethod(Enum):
    CENTERLINE = "centerline"
    LEFT_RAIL = "left_rail"
    RIGHT_RAIL = "right_rail"

@dataclass(frozen=True, slots=True)
class CantCriticalStation:
    """캔트 임계 측점 (C3D SuperelevationCriticalStation 호환)."""
    station: float = 0.0
    cant_value: float = 0.0          # mm 또는 m
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

    def cant_at(self, station: float) -> CantCriticalStation | None:
        """측점의 캔트 값 (선형 보간)."""
        if not self.critical_stations:
            return None
        for i in range(len(self.critical_stations) - 1):
            a, b = self.critical_stations[i], self.critical_stations[i+1]
            if a.station <= station <= b.station:
                t = (station - a.station) / (b.station - a.station) if b.station > a.station else 0
                return CantCriticalStation(
                    station=station,
                    cant_value=a.cant_value + t * (b.cant_value - a.cant_value),
                    left_rail_delta=a.left_rail_delta + t * (b.left_rail_delta - a.left_rail_delta),
                    right_rail_delta=a.right_rail_delta + t * (b.right_rail_delta - a.right_rail_delta),
                )
        return self.critical_stations[-1]