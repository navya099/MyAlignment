# alignment/alignment_query.py
from __future__ import annotations
import math
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.alignment.alignment_side import AlignmentSide
from myalignment.alignment.intersection import intersect_ray_with_collection
from myalignment.core.station_offset import StationOffsetPoint

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment


class AlignmentQuery:
    """C3D 호환 Alignment 고급 쿼리."""

    # ================================================================
    # DistanceToAlignment
    # ================================================================
    @staticmethod
    def distance_to_alignment(
            alignment: "Alignment",
            station: float,
            other: "Alignment",
            side: AlignmentSide | None = None,
    ) -> tuple[float, float]:
        """
        C3D DistanceToAlignment 호환.

        Args:
            alignment: 기준 선형.
            station: 기준 측점.
            other: 대상 선형.
            side: 탐색 방향 (None이면 BOTH).

        Returns:
            (signed_distance, station_on_other)
            - signed_distance: LEFT(+), RIGHT(−).
            - station_on_other: 대상 선형의 측점.

        Raises:
            ValueError: 교차점이 없을 때.
        """
        if not alignment.is_valid:
            raise ValueError("기준 Alignment가 비어있음")
        if not other.is_valid:
            raise ValueError("대상 Alignment가 비어있음")
        if side is None:
            side = AlignmentSide.BOTH

        # 1) 기준점 + 접선 방위각
        ref_pt = alignment.point_at(station)
        ref_az = alignment.tangent_at(station)

        # 2) 수직 방향 (LEFT/RIGHT)
        normals: list[tuple[float, int]] = []  # (방위각, 부호)
        if side in (AlignmentSide.LEFT, AlignmentSide.BOTH):
            normals.append((ref_az + math.pi / 2, +1))  # LEFT: +
        if side in (AlignmentSide.RIGHT, AlignmentSide.BOTH):
            normals.append((ref_az - math.pi / 2, -1))  # RIGHT: -

        # 3) 각 수직 반직선과 대상의 교차점 탐색
        candidates: list[tuple[float, float]] = []  # (signed_dist, sta_other)
        for ray_az, sign in normals:
            hits = intersect_ray_with_collection(ref_pt, ray_az, other.entities)
            for pt, sta_other in hits:
                dist = ref_pt.distance_to(pt)
                candidates.append((sign * dist, sta_other))

        if not candidates:
            raise ValueError(
                f"station {station}에서 대상 Alignment와 교차점 없음 "
                f"(side={side.name})"
            )

        # 4) 최단 거리 (BOTH는 절댓값 최소)
        return min(candidates, key=lambda c: abs(c[0]))

    # ================================================================
    # Intersection
    # ================================================================
    @staticmethod
    def intersection(
            a: "Alignment", b: "Alignment", tol: float = 1e-3
    ) -> list[StationOffsetPoint]:
        """
        두 선형의 교차점들 (station-offset).

        전략:
            - A의 각 Entity를 B에 투영
            - 오프셋 ≈ 0인 점만 교차점으로 채택
            - 중복 제거 (tol)
        """
        if not a.is_valid or not b.is_valid:
            return []

        candidates: list[StationOffsetPoint] = []

        # A의 각 Entity 순회
        for entity in a.entities:
            # Entity 끝점/시작점 + 중간 샘플로 B에 투영
            sample_stations = _sample_stations(entity, n=10)
            for sta in sample_stations:
                pt = a.point_at(sta)
                pr = b.project(pt)
                if abs(pr.offset) < tol:
                    candidates.append(StationOffsetPoint(sta, 0.0))

        # 중복 제거
        return _dedupe_by_station(candidates, tol)

    # ================================================================
    # 편의
    # ================================================================
    @staticmethod
    def nearest_point_on_alignment(
            alignment: "Alignment", point: Point2d
    ) -> StationOffsetPoint:
        """점에서 가장 가까운 선형 위 측점/횡거."""
        pr = alignment.project(point)
        return pr.to_station_offset()

    @staticmethod
    def point_on_alignment_at(
            alignment: "Alignment", station: float, offset: float = 0.0
    ) -> Point2d:
        return alignment.point_at(station, offset)


# ================================================================
# 내부 헬퍼
# ================================================================
def _sample_stations(entity, n: int = 10) -> list[float]:
    """Entity 내부 등간격 측점 샘플."""
    return [
        entity.start_station + entity.length * i / n
        for i in range(n + 1)
    ]


def _dedupe_by_station(
        points: list[StationOffsetPoint], tol: float
) -> list[StationOffsetPoint]:
    """측점 기준 중복 제거."""
    if not points:
        return []
    points_sorted = sorted(points, key=lambda p: p.station)
    result = [points_sorted[0]]
    for p in points_sorted[1:]:
        if p.station - result[-1].station > tol:
            result.append(p)
    return result