"""교차점과 접점을 선형 요소의 실제 측점 범위에서 계산한다."""
from __future__ import annotations

from collections.abc import Callable, Iterator
from fractions import Fraction
import math
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.enitity.alignment_entity import AlignmentEntity
from myalignment.enitity.arc_entity import ArcEntity
from myalignment.enitity.line_entity import LineEntity
from myalignment.enitity.spiral_entity import SpiralEntity
from myalignment.utils.curvedirection import CurveDirection

if TYPE_CHECKING:
    from myalignment.enitity.entity_collection import AlignmentEntityCollection


_DISTANCE_EPS = 1e-8
_STATION_EPS = 1e-9


def line_line_intersection(
    p1: Point2d, az1: float, p2: Point2d, az2: float,
) -> Point2d | None:
    """두 무한 직선의 교점. 평행이면 None."""
    if math.remainder(az2 - az1, math.pi) == 0:
        return None
    d1x, d1y = math.cos(az1), math.sin(az1)
    parameters = _line_parameters(p1, (d1x, d1y), p2, (math.cos(az2), math.sin(az2)))
    if parameters is None:
        return None
    t, _ = parameters
    return Point2d(p1.x + t * d1x, p1.y + t * d1y)


def _determinant(ax: float, ay: float, bx: float, by: float) -> float:
    left, right = ax * by, ay * bx
    determinant = left - right
    # 거의 평행한 벡터의 상쇄 오차는 입력 부동소수점의 정확한 값으로 다시 계산한다.
    if min(abs(left), abs(right)) > 0 and abs(determinant) <= max(abs(left), abs(right)) / 256:
        return float(Fraction(ax) * Fraction(by) - Fraction(ay) * Fraction(bx))
    return determinant


def _coordinate_roundoff(*points: Point2d) -> float:
    return 8 * math.ulp(max(abs(coord) for point in points for coord in (point.x, point.y)))


def _line_parameters(
    p1: Point2d, d1: tuple[float, float], p2: Point2d, d2: tuple[float, float],
) -> tuple[float, float] | None:
    """각 직선의 원점에서 교차점까지의 벡터 배율을 계산한다."""
    d1x, d1y = d1
    d2x, d2y = d2
    determinant = _determinant(d1x, d1y, d2x, d2y)
    if determinant == 0:
        return None
    x, y = p2.x - p1.x, p2.y - p1.y
    return _determinant(x, y, d2x, d2y) / determinant, _determinant(x, y, d1x, d1y) / determinant


def _within_length(distance: float, entity: LineEntity) -> bool:
    return -_DISTANCE_EPS <= distance <= entity.length + _DISTANCE_EPS


def _arc_center(entity: ArcEntity) -> Point2d:
    az = entity.start_azimuth
    radius = entity.geometry.radius
    signed_radius = radius if entity.geometry.direction is CurveDirection.LEFT else -radius
    return Point2d(
        entity.start_coord.x - signed_radius * math.sin(az),
        entity.start_coord.y + signed_radius * math.cos(az),
    )


def _on_entity(entity: AlignmentEntity, point: Point2d) -> float | None:
    projected = entity.project(point)
    return projected.station if projected.distance <= _DISTANCE_EPS else None


def intersect_ray_with_line_entity(
    origin: Point2d, ray_az: float, entity: LineEntity,
) -> list[tuple[Point2d, float]]:
    """반직선과 선분이 겹치면 공통 구간의 양 끝을 반환한다."""
    dx, dy = math.cos(ray_az), math.sin(ray_az)
    parameters = None
    if math.remainder(ray_az - entity.start_azimuth, math.pi) != 0:
        parameters = _line_parameters(origin, (dx, dy), entity.start_coord, entity.coordinate_delta)

    if parameters is not None:
        along_ray, fraction = parameters
        along_line = fraction * entity.length
        if along_ray >= -_DISTANCE_EPS and _within_length(along_line, entity):
            station = entity.start_station + max(0.0, min(entity.length, along_line))
            return [(entity.point_at(station), station)]
        return []

    def ahead(p: Point2d) -> bool:
        return (p.x - origin.x) * dx + (p.y - origin.y) * dy >= -_DISTANCE_EPS

    start = entity.start_coord
    if abs(dx * (start.y - origin.y) - dy * (start.x - origin.x)) > _DISTANCE_EPS:
        return []
    candidates = [(start, entity.start_station), (entity.end_coord, entity.end_station)]
    origin_station = _on_entity(entity, origin)
    if origin_station is not None:
        candidates.append((origin, origin_station))
    return _unique_hits((p, s) for p, s in candidates if ahead(p))


def intersect_ray_with_arc_entity(
    origin: Point2d, ray_az: float, entity: ArcEntity,
) -> list[tuple[Point2d, float]]:
    """반직선과 원호의 해석적 교차."""
    center = _arc_center(entity)
    dx, dy = math.cos(ray_az), math.sin(ray_az)
    ox, oy = center.x - origin.x, center.y - origin.y
    along = ox * dx + oy * dy
    perpendicular = abs(dx * oy - dy * ox)
    radius = entity.geometry.radius
    if perpendicular > radius + _DISTANCE_EPS:
        return []

    radial_gap = radius - perpendicular
    roundoff = 4 * math.ulp(max(abs(center.x), abs(center.y), abs(origin.x), abs(origin.y), radius))
    half_chord = 0.0 if abs(radial_gap) <= roundoff else math.sqrt(max(0.0, radial_gap * (radius + perpendicular)))
    hits = []
    for t in (along - half_chord, along + half_chord):
        if t >= -_DISTANCE_EPS:
            point = Point2d(origin.x + t * dx, origin.y + t * dy)
            station = _on_entity(entity, point)
            if station is not None:
                hits.append((point, station))
    return _unique_hits(hits)


def _bisect(function: Callable[[float], float], lo: float, hi: float, value_lo: float) -> float:
    while hi - lo > _STATION_EPS:
        mid = lo + (hi - lo) / 2
        if mid == lo or mid == hi:
            break
        value = function(mid)
        if value == 0:
            return mid
        if (value < 0) == (value_lo < 0):
            lo = mid
        else:
            hi = mid
    return lo + (hi - lo) / 2


def _roots(
    value: Callable[[float], float], derivative_sign: Callable[[float], float],
    start: float, end: float, count: int, *, roundoff: float,
) -> list[float]:
    """끝점과 극점을 검사하고 부호가 다른 단조 구간에서 근을 찾는다."""
    if start == end:
        return [start] if abs(value(start)) <= _DISTANCE_EPS else []
    extrema = [start]
    left, d_left = start, derivative_sign(start)
    for i in range(1, count + 1):
        right = end if i == count else start + (end - start) * i / count
        d_right = derivative_sign(right)
        if d_left * d_right < 0:
            extrema.append(_bisect(derivative_sign, left, right, d_left))
        elif d_right == 0 and d_left != 0 and right < end:
            extrema.append(right)
        left, d_left = right, d_right
    extrema.append(end)

    values = [value(station) for station in extrema]
    # 반올림 오차 범위의 접점은 양쪽에 수치상 가짜 교차가 생길 수 있다.
    contacts = {
        i for i, (station, height) in enumerate(zip(extrema, values))
        if abs(height) <= roundoff and (
            0 < i < len(extrema) - 1 or abs(derivative_sign(station)) <= 1e-12
        )
    }
    bracketed = set()
    hits = []
    for i, (h_lo, h_hi) in enumerate(zip(values, values[1:])):
        if i not in contacts and i + 1 not in contacts and h_lo * h_hi < 0:
            hits.append(_bisect(value, extrema[i], extrema[i + 1], h_lo))
            bracketed.update((i, i + 1))
    hits.extend(
        station for i, (station, height) in enumerate(zip(extrema, values))
        if i not in bracketed and abs(height) <= _DISTANCE_EPS
    )
    return sorted(hits)


def intersect_ray_with_spiral_entity(
    origin: Point2d, ray_az: float, entity: SpiralEntity, n: int = 200,
) -> list[tuple[Point2d, float]]:
    """반직선에 대한 부호 거리의 극점도 검사해 완화곡선 접점을 구한다."""
    dx, dy = math.cos(ray_az), math.sin(ray_az)

    def signed_distance(station: float) -> float:
        point = entity.point_at(station)
        return dx * (point.y - origin.y) - dy * (point.x - origin.x)

    def derivative_sign(station: float) -> float:
        return math.sin(entity.tangent_at(station) - ray_az)

    roundoff = _coordinate_roundoff(origin, entity.start_coord, entity.end_coord)
    stations = _roots(
        signed_distance, derivative_sign, entity.start_station, entity.end_station, max(1, n),
        roundoff=roundoff,
    )
    hits = []
    for station in stations:
        point = entity.point_at(station)
        if (point.x - origin.x) * dx + (point.y - origin.y) * dy >= -_DISTANCE_EPS:
            hits.append((point, station))
    return hits


def intersect_ray_with_entity(
    origin: Point2d, ray_az: float, entity: AlignmentEntity,
) -> list[tuple[Point2d, float]]:
    """반직선 ∩ 단일 Entity."""
    if isinstance(entity, LineEntity):
        return intersect_ray_with_line_entity(origin, ray_az, entity)
    if isinstance(entity, ArcEntity):
        return intersect_ray_with_arc_entity(origin, ray_az, entity)
    if isinstance(entity, SpiralEntity):
        return intersect_ray_with_spiral_entity(origin, ray_az, entity)
    raise TypeError(f"지원하지 않는 Entity: {type(entity).__name__}")


def _unique_hits(hits) -> list[tuple[Point2d, float]]:
    result = []
    for point, station in sorted(hits, key=lambda item: item[1]):
        if not result or station - result[-1][1] > _DISTANCE_EPS:
            result.append((point, station))
    return result


def intersect_ray_with_collection(
    origin: Point2d, ray_az: float, collection: AlignmentEntityCollection,
) -> list[tuple[Point2d, float]]:
    """반직선 ∩ 전체 Entity 컬렉션."""
    return _unique_hits(
        hit for entity in collection for hit in intersect_ray_with_entity(origin, ray_az, entity)
    )


def _arc_arc_points(a: ArcEntity, b: ArcEntity) -> tuple[Point2d, ...]:
    first, second = _arc_center(a), _arc_center(b)
    x, y = second.x - first.x, second.y - first.y
    distance = math.hypot(x, y)
    r, s = a.geometry.radius, b.geometry.radius
    if distance <= _DISTANCE_EPS:
        if abs(r - s) <= _DISTANCE_EPS:
            return a.start_coord, a.end_coord, b.start_coord, b.end_coord
        return ()
    if distance > r + s + _DISTANCE_EPS or distance < abs(r - s) - _DISTANCE_EPS:
        return ()

    along = (distance * distance + (r - s) * (r + s)) / (2 * distance)
    height = math.sqrt(max(0.0, (r - along) * (r + along)))
    ux, uy = x / distance, y / distance
    mid_x, mid_y = first.x + ux * along, first.y + uy * along
    return (
        Point2d(mid_x - uy * height, mid_y + ux * height),
        Point2d(mid_x + uy * height, mid_y - ux * height),
    )


def _arc_spiral_stations(arc: ArcEntity, spiral: SpiralEntity) -> list[float]:
    center = _arc_center(arc)

    def radial_distance(station: float) -> float:
        return spiral.point_at(station).distance_to(center) - arc.geometry.radius

    def derivative_sign(station: float) -> float:
        point, az = spiral.point_at(station), spiral.tangent_at(station)
        return (point.x - center.x) * math.cos(az) + (point.y - center.y) * math.sin(az)

    roundoff = _coordinate_roundoff(center, spiral.start_coord, spiral.end_coord)
    return _roots(
        radial_distance, derivative_sign, spiral.start_station, spiral.end_station, 200,
        roundoff=roundoff + 4 * math.ulp(arc.geometry.radius),
    )


def _spiral_spans(curve: SpiralEntity) -> Iterator[tuple[float, float, float]]:
    """공통 축에 투영해 역으로 측점을 찾을 수 있도록 접선 회전이 작은 구간으로 나눈다."""
    def split(start: float, end: float, depth: int):
        middle = (start + end) / 2
        az = curve.tangent_at(middle)
        if depth < 12 and any(
            abs(math.remainder(curve.tangent_at(start + (end - start) * t) - az, math.tau)) > math.pi / 12
            for t in (0, 0.25, 0.75, 1)
        ):
            yield from split(start, middle, depth + 1)
            yield from split(middle, end, depth + 1)
        else:
            yield start, end, az

    stations = [curve.start_station + curve.length * i / 8 for i in range(8)] + [curve.end_station]
    for start, end in zip(stations, stations[1:]):
        yield from split(start, end, 0)


def _spiral_spiral_stations(a: SpiralEntity, b: SpiralEntity) -> Iterator[tuple[float, float]]:
    # 같은 완화곡선은 겹치는 구간의 끝점만 반환한다.
    if math.isclose(a.length, b.length, rel_tol=0, abs_tol=_DISTANCE_EPS):
        for reverse in (False, True):
            if all(
                a.point_at(a.start_station + a.length * t).distance_to(
                    b.point_at(b.start_station + b.length * (1 - t if reverse else t))
                ) <= _DISTANCE_EPS for t in (0, 0.25, 0.5, 0.75, 1)
            ):
                yield a.start_station, b.end_station if reverse else b.start_station
                yield a.end_station, b.start_station if reverse else b.end_station
                return

    b_spans = tuple(_spiral_spans(b))
    for a_start, a_end, a_az in _spiral_spans(a):
        for b_start, b_end, b_az in b_spans:
            # 진행 방향을 무시한 접선 사이의 이등분축에서 두 구간은 단조다.
            az = a_az + math.remainder(b_az - a_az, math.pi) / 2
            dx, dy = math.cos(az), math.sin(az)
            origin = a.point_at(a_start)

            def projected(curve, station):
                point = curve.point_at(station)
                return (point.x - origin.x) * dx + (point.y - origin.y) * dy

            a0, a1 = projected(a, a_start), projected(a, a_end)
            b0, b1 = projected(b, b_start), projected(b, b_end)
            lo, hi = max(min(a0, a1), min(b0, b1)), min(max(a0, a1), max(b0, b1))
            if lo > hi + _DISTANCE_EPS:
                continue
            hi = max(lo, hi)

            def station_at(curve, x, start, end, x0, x1):
                if x <= min(x0, x1):
                    return start if x0 <= x1 else end
                if x >= max(x0, x1):
                    return end if x0 <= x1 else start
                return _bisect(lambda station: projected(curve, station) - x, start, end, x0 - x)

            def stations_at(x: float) -> tuple[float, float]:
                return (
                    station_at(a, x, a_start, a_end, a0, a1),
                    station_at(b, x, b_start, b_end, b0, b1),
                )

            def difference(x: float) -> float:
                sa, sb = stations_at(x)
                pa, pb = a.point_at(sa), b.point_at(sb)
                return dx * (pa.y - pb.y) - dy * (pa.x - pb.x)

            def derivative_sign(x: float) -> float:
                sa, sb = stations_at(x)
                az_a, az_b = a.tangent_at(sa), b.tangent_at(sb)
                return math.sin(az_a - az_b) * math.cos(az_a - az) * math.cos(az_b - az)

            roundoff = _coordinate_roundoff(origin, b.start_coord, b.end_coord) + _STATION_EPS
            for x in _roots(difference, derivative_sign, lo, hi, 12, roundoff=roundoff):
                yield stations_at(x)


def intersection_stations(a: AlignmentEntity, b: AlignmentEntity) -> list[float]:
    """두 유한 요소의 교차점을 첫 요소의 측점으로 반환한다."""
    if isinstance(a, LineEntity) and isinstance(b, LineEntity):
        parameters = _line_parameters(a.start_coord, a.coordinate_delta, b.start_coord, b.coordinate_delta)
        if parameters is not None:
            fraction_a, fraction_b = parameters
            along_a, along_b = fraction_a * a.length, fraction_b * b.length
            if _within_length(along_a, a) and _within_length(along_b, b):
                return [a.start_station + max(0.0, min(a.length, along_a))]
            return []
        candidates = (a.start_coord, a.end_coord, b.start_coord, b.end_coord)
        return [
            station for point in candidates
            if (station := _on_entity(a, point)) is not None and _on_entity(b, point) is not None
        ]
    if isinstance(a, LineEntity):
        return [
            station for point, _ in intersect_ray_with_entity(a.start_coord, a.start_azimuth, b)
            if (station := _on_entity(a, point)) is not None
        ]
    if isinstance(b, LineEntity):
        return [station for point, station in intersect_ray_with_entity(b.start_coord, b.start_azimuth, a)
                if _on_entity(b, point) is not None]
    if isinstance(a, ArcEntity) and isinstance(b, ArcEntity):
        return [station for point in _arc_arc_points(a, b)
                if (station := _on_entity(a, point)) is not None and _on_entity(b, point) is not None]
    if isinstance(a, ArcEntity) and isinstance(b, SpiralEntity):
        return [station for sb in _arc_spiral_stations(a, b)
                if (station := _on_entity(a, b.point_at(sb))) is not None]
    if isinstance(a, SpiralEntity) and isinstance(b, ArcEntity):
        return [sa for sa in _arc_spiral_stations(b, a) if _on_entity(b, a.point_at(sa)) is not None]
    if isinstance(a, SpiralEntity) and isinstance(b, SpiralEntity):
        return [sa for sa, sb in _spiral_spiral_stations(a, b)
                if a.point_at(sa).distance_to(b.point_at(sb)) <= _DISTANCE_EPS]
    raise TypeError(f"지원하지 않는 Entity 조합: {type(a).__name__}, {type(b).__name__}")
