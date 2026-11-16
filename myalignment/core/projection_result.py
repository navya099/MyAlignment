# core/projection_result.py
from __future__ import annotations
from dataclasses import dataclass
import math

from .station_offset import StationOffsetPoint


@dataclass(frozen=True, slots=True)
class ProjectionResult:
    """
    점을 선형(또는 기하 요소)에 투영한 결과.

    C3D의 Alignment.PointLocationOptions 결과와 호환.

    Attributes:
        point: 투영점 (월드 좌표)
        station: 투영점의 측점 (m). 선형 시작 기준.
        offset: 투영점의 횡거 (m). 진행 방향 기준 좌(-)/우(+).
        distance: 원점에서 투영점까지의 거리 (항상 ≥ 0).
        tangent: 투영점에서의 접선 방위각 (rad).
        is_on_entity: 투영점이 기하 요소 범위 내인지 (경계 포함).
    """
    point: "Point2d"
    station: float
    offset: float
    distance: float
    tangent: float
    is_on_entity: bool = True

    # ---- 검증 ----
    def __post_init__(self):
        if self.distance < 0:
            raise ValueError(f"distance는 ≥ 0이어야 함: {self.distance}")
        if not math.isfinite(self.tangent):
            raise ValueError(f"tangent가 유한하지 않음: {self.tangent}")

    # ---- 편의 ----
    def to_station_offset(self) -> StationOffsetPoint:
        """StationOffsetPoint로 변환."""
        return StationOffsetPoint(self.station, self.offset)

    def side(self) -> int:
        """좌(-1) / 중심(0) / 우(+1)."""
        if self.offset < -1e-9:
            return -1
        if self.offset > 1e-9:
            return +1
        return 0

    def signed_offset(self) -> float:
        """부호 있는 offset."""
        return self.offset

    # ---- 비교 ----
    def is_closer_than(self, other: "ProjectionResult") -> bool:
        """더 가까운 투영 결과인지 (distance 기준)."""
        return self.distance < other.distance

    # ---- 표현 ----
    def __repr__(self) -> str:
        return (
            f"ProjectionResult("
            f"sta={self.station:.3f}, off={self.offset:+.3f}, "
            f"dist={self.distance:.3f}, on={self.is_on_entity})"
        )