# core/station_offset.py
from __future__ import annotations
from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class StationOffsetPoint:
    """
    선형 위의 측점(Station)과 횡거(Offset)로 표현되는 점.

    C3D의 StationOffsetPoint와 호환.

    Attributes:
        station: 측점 (m). 선형 시작 기준 누적 거리.
        offset: 횡거 (m). 진행 방향 기준 좌(-)/우(+).
    """
    station: float
    offset: float = 0.0

    # ---- 검증 ----
    def __post_init__(self):
        if not math.isfinite(self.station):
            raise ValueError(f"station이 유한하지 않음: {self.station}")
        if not math.isfinite(self.offset):
            raise ValueError(f"offset이 유한하지 않음: {self.offset}")

    # ---- 변환 (Alignment 의존) ----
    def to_point(self, alignment: "Alignment") -> "Point2d":
        """월드 좌표(Point2d)로 변환. Alignment.point_at에 위임."""
        return alignment.point_at(self.station, self.offset)

    @classmethod
    def from_point(
            cls, alignment: "Alignment", point: "Point2d"
    ) -> "StationOffsetPoint":
        """월드 좌표 → 측점/횡거. Alignment.station_offset_of에 위임."""
        return alignment.station_offset_of(point)

    # ---- 거리 ----
    def distance_to(self, other: "StationOffsetPoint") -> float:
        """
        두 측점/오프셋 점 사이의 '선형상 거리'.

        주의: 월드 좌표 거리가 아니라 station-offset 평면 거리.
        (C3D도 동일한 의미)
        """
        return math.hypot(self.station - other.station, self.offset - other.offset)

    def signed_offset(self) -> float:
        """부호 있는 offset (좌-, 우+)."""
        return self.offset

    def abs_offset(self) -> float:
        """절댓값 offset (거리)."""
        return abs(self.offset)

    # ---- 연산 ----
    def shifted(self, d_station: float = 0.0, d_offset: float = 0.0) -> "StationOffsetPoint":
        """측점/횡거 이동한 새 점."""
        return StationOffsetPoint(self.station + d_station, self.offset + d_offset)

    # ---- 표현 ----
    def __repr__(self) -> str:
        return f"StationOffsetPoint(sta={self.station:.3f}, off={self.offset:+.3f})"

    def __str__(self) -> str:
        side = "L" if self.offset < 0 else ("R" if self.offset > 0 else "C")
        return f"STA {self.station:.3f} / OFF {self.offset:+.3f} ({side})"