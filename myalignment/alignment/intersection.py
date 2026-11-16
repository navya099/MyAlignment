# alignment/intersection.py
from __future__ import annotations
import math
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.enitity.alignment_entity import AlignmentEntity
from myalignment.enitity.arc_entity import ArcEntity
from myalignment.enitity.line_entity import LineEntity
from myalignment.enitity.spiral_entity import SpiralEntity

def line_line_intersection(
        p1: Point2d, az1: float, p2: Point2d, az2: float
) -> Point2d | None:
    """두 직선(점+방위각)의 교점. 평행이면 None."""
    d1x, d1y = math.cos(az1), math.sin(az1)
    d2x, d2y = math.cos(az2), math.sin(az2)
    denom = d1x * d2y - d1y * d2x
    if abs(denom) < 1e-12:
        return None
    t = ((p2.x - p1.x) * d2y - (p2.y - p1.y) * d2x) / denom
    return Point2d(p1.x + t * d1x, p1.y + t * d1y)


def intersect_ray_with_line_entity(
        origin: Point2d, ray_az: float, entity: LineEntity
) -> list[tuple[Point2d, float]]:
    """반직선 ∩ 직선 Entity."""
    seg_az = entity.start_azimuth
    pt = line_line_intersection(origin, ray_az, entity.start_coord, seg_az)
    if pt is None:
        return []

    dx, dy = math.cos(ray_az), math.sin(ray_az)
    t_ray = (pt.x - origin.x) * dx + (pt.y - origin.y) * dy
    if t_ray < -1e-9:
        return []

    # Entity 범위 확인 (project) - 부동소수점 경계 오차(1e-6) 허용
    pr = entity.project(pt)
    is_within_range = pr.is_on_entity or (
            -1e-6 <= pr.station - entity.start_station <= entity.length + 1e-6
    )
    if pr.distance < 1e-6 and is_within_range:
        return [(pt, pr.station)]
    return []


def intersect_ray_with_arc_entity(
        origin: Point2d, ray_az: float, entity: ArcEntity
) -> list[tuple[Point2d, float]]:
    """반직선 ∩ 원호 Entity (해석적)."""
    g = entity.geometry
    # 원호 중심 (로컬 → 월드)

    local_center = Point2d(0.0, (1 if g.direction.value == 0 else -1) * g.radius)
    world_center = AlignmentEntity._local_to_world(
        local_center, entity.start_azimuth, entity.start_coord
    )
    cx, cy = world_center.x, world_center.y
    r = g.radius

    dx, dy = math.cos(ray_az), math.sin(ray_az)
    ox, oy = origin.x - cx, origin.y - cy

    a = dx * dx + dy * dy  # = 1
    b = 2 * (ox * dx + oy * dy)
    c = ox * ox + oy * oy - r * r
    disc = b * b - 4 * a * c
    if disc < 0:
        return []

    sqrt_d = math.sqrt(disc)
    ts = [(-b - sqrt_d) / (2 * a), (-b + sqrt_d) / (2 * a)]

    results = []
    for t in ts:
        if t < -1e-9:
            continue
        pt = Point2d(origin.x + t * dx, origin.y + t * dy)
        pr = entity.project(pt)
        if pr.is_on_entity and pr.distance < 1e-6:
            results.append((pt, pr.station))
    return results


def intersect_ray_with_spiral_entity(
        origin: Point2d, ray_az: float, entity: SpiralEntity, n: int = 200
) -> list[tuple[Point2d, float]]:
    """
    반직선 ∩ 완화곡선 Entity (수치 탐색).

    샘플링 → 부호 변화 감지 → 이분법.
    """
    dx, dy = math.cos(ray_az), math.sin(ray_az)

    def signed_dist(pt: Point2d) -> float:
        # 반직선 기준 외적 부호 (0이면 반직선 위)
        return dx * (pt.y - origin.y) - dy * (pt.x - origin.x)

    results = []
    length = entity.length
    start_sta = entity.start_station

    prev_s = 0.0
    prev_pt = entity.point_at(start_sta)
    prev_v = signed_dist(prev_pt)

    for i in range(1, n + 1):
        s = length * i / n
        pt = entity.point_at(start_sta + s)
        v = signed_dist(pt)

        if prev_v == 0.0:
            # 시작점이 반직선 위
            t = (prev_pt.x - origin.x) * dx + (prev_pt.y - origin.y) * dy
            if t >= -1e-9:
                results.append((prev_pt, start_sta + prev_s))
        elif prev_v * v < 0:
            # 이분법
            lo, hi = prev_s, s
            for _ in range(40):
                mid = 0.5 * (lo + hi)
                mp = entity.point_at(start_sta + mid)
                if signed_dist(mp) * prev_v < 0:
                    hi = mid
                else:
                    lo = mid
            mid = 0.5 * (lo + hi)
            mp = entity.point_at(start_sta + mid)
            t = (mp.x - origin.x) * dx + (mp.y - origin.y) * dy
            if t >= -1e-9:
                results.append((mp, start_sta + mid))

        prev_s, prev_pt, prev_v = s, pt, v

    return results


def intersect_ray_with_entity(
        origin: Point2d, ray_az: float, entity: AlignmentEntity
) -> list[tuple[Point2d, float]]:
    """반직선 ∩ 단일 Entity."""
    if isinstance(entity, LineEntity):
        return intersect_ray_with_line_entity(origin, ray_az, entity)
    if isinstance(entity, ArcEntity):
        return intersect_ray_with_arc_entity(origin, ray_az, entity)
    if isinstance(entity, SpiralEntity):
        return intersect_ray_with_spiral_entity(origin, ray_az, entity)
    raise TypeError(f"지원하지 않는 Entity: {type(entity).__name__}")


def intersect_ray_with_collection(
        origin: Point2d,
        ray_az: float,
        collection: "AlignmentEntityCollection",
) -> list[tuple[Point2d, float]]:
    """반직선 ∩ 전체 Entity 컬렉션."""
    results = []
    for entity in collection:
        results.extend(intersect_ray_with_entity(origin, ray_az, entity))
    return results