from __future__ import annotations

from dataclasses import dataclass
import math

from myalignment.corridor.feature_line_spec import CorridorFeatureLineSpec
from myalignment.render.primitives_3d import Point3D


@dataclass(frozen=True, slots=True)
class FeatureLinePoint:
    """기하 측점과 코리더의 월드 좌표 점."""

    station: float
    point: Point3D

    def __post_init__(self):
        if not math.isfinite(self.station):
            raise ValueError("station must be finite")
        if not isinstance(self.point, Point3D):
            raise TypeError("point must be a Point3D")


@dataclass(frozen=True, slots=True)
class CorridorFeatureLine:
    """한 사양으로 추출한 점과 연결이 끊기는 위치."""

    name: str = ""
    points: tuple[FeatureLinePoint, ...] = ()
    spec: CorridorFeatureLineSpec | None = None
    break_indices: tuple[int, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "points", tuple(self.points))
        object.__setattr__(self, "break_indices", tuple(self.break_indices))
        if any(type(i) is not int or not 0 < i < len(self.points) for i in self.break_indices):
            raise ValueError("break_indices must be internal point indices")
        if tuple(sorted(set(self.break_indices))) != self.break_indices:
            raise ValueError("break_indices must be strictly increasing")
        for segment in self.segments:
            if any(a.station >= b.station for a, b in zip(segment, segment[1:])):
                raise ValueError("stations must strictly increase within a segment")

    @property
    def segments(self) -> tuple[tuple[FeatureLinePoint, ...], ...]:
        """연결된 점 열을 구간별로 반환한다."""
        if not self.points:
            return ()
        bounds = (0, *self.break_indices, len(self.points))
        return tuple(self.points[a:b] for a, b in zip(bounds, bounds[1:]))

    @property
    def length(self) -> float:
        """연결된 점 사이의 3D 길이 합계."""
        return sum(a.point.distance_to(b.point) for run in self.segments for a, b in zip(run, run[1:]))

    @property
    def start_point(self) -> Point3D | None:
        return self.points[0].point if self.points else None

    @property
    def end_point(self) -> Point3D | None:
        return self.points[-1].point if self.points else None

    @property
    def start_station(self) -> float:
        """첫 구간의 시작 측점."""
        return self.points[0].station if self.points else 0.0

    @property
    def end_station(self) -> float:
        """마지막 구간의 끝 측점."""
        return self.points[-1].station if self.points else 0.0

    def point_at_station(self, station: float, tol: float = 1e-3) -> Point3D | None:
        """구간 안에서 보간하고 공차 안의 구간 끝점에 스냅한다.

        같은 측점에 서로 다른 구간 좌표가 있으면 ValueError를 발생시킨다.
        """
        if not math.isfinite(station) or not math.isfinite(tol) or tol < 0:
            raise ValueError("station must be finite and tolerance finite and nonnegative")
        candidates = []
        for run in self.segments:
            if station <= run[0].station:
                candidates.append((run[0].station - station, run[0].point))
            elif station >= run[-1].station:
                candidates.append((station - run[-1].station, run[-1].point))
            else:
                for a, b in zip(run, run[1:]):
                    if station <= b.station:
                        t = (station - a.station) / (b.station - a.station)
                        p, q = a.point, b.point
                        hit = q if station == b.station else Point3D(
                            p.x + t * (q.x - p.x), p.y + t * (q.y - p.y), p.z + t * (q.z - p.z),
                        )
                        candidates.append((0.0, hit))
                        break
        distance = min((gap for gap, _ in candidates), default=math.inf)
        if distance > tol:
            return None
        points = [p for gap, p in candidates if gap == distance]
        if any(points[0].distance_to(p) > 1e-8 for p in points[1:]):
            raise ValueError(f"STA {station}: multiple feature line positions")
        return points[0]
