from __future__ import annotations

from dataclasses import dataclass
import math

from cadgeom import Point2d

from myalignment.surface.contour_type import ContourType


@dataclass(frozen=True, slots=True)
class ContourLine:
    """한 표고에 놓이는 평면 폴리라인."""

    elevation: float = 0.0
    contour_type: ContourType = ContourType.MINOR
    points: tuple[Point2d, ...] = ()
    closed: bool = False

    def __post_init__(self):
        if not math.isfinite(self.elevation):
            raise ValueError("elevation must be finite")
        if not isinstance(self.contour_type, ContourType):
            raise ValueError("contour_type must be a ContourType")
        points = tuple(self.points)
        if self.closed and len(points) > 1 and points[0] == points[-1]:
            points = points[:-1]
        object.__setattr__(self, "points", points)

    def _segments(self):
        following = (*self.points[1:], self.points[0]) if self.closed and self.points else self.points[1:]
        return zip(self.points, following)

    @property
    def length(self) -> float:
        return math.fsum(a.distance_to(b) for a, b in self._segments())

    @property
    def point_count(self) -> int:
        return len(self.points)

    def midpoint(self) -> Point2d | None:
        """선 길이의 절반에 해당하는 위치를 반환한다."""
        if not self.points:
            return None
        return next(self._points_at_distances((self.length / 2,)), self.points[0])

    def _points_at_distances(self, distances):
        samples = iter(distances)
        target = next(samples, None)
        start = 0.0
        for a, b in self._segments():
            length = a.distance_to(b)
            end = start + length
            while target is not None and target <= end:
                fraction = (target - start) / length if length else 0.0
                yield Point2d(a.x + fraction * (b.x - a.x), a.y + fraction * (b.y - a.y))
                target = next(samples, None)
            if target is None:
                break
            start = end


@dataclass(frozen=True, slots=True)
class ContourSet:
    """표고별로 조회할 수 있는 불변 등고선 집합."""

    contours: tuple[ContourLine, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "contours", tuple(self.contours))

    def __len__(self) -> int:
        return len(self.contours)

    def __iter__(self):
        return iter(self.contours)

    def total_length(self) -> float:
        return math.fsum(line.length for line in self)

    def by_elevation(self, elevation: float, tol: float = 1e-3) -> tuple[ContourLine, ...]:
        if not math.isfinite(tol) or tol < 0:
            raise ValueError("tol must be finite and nonnegative")
        return tuple(line for line in self if abs(line.elevation - elevation) <= tol)

    def major_contours(self) -> tuple[ContourLine, ...]:
        return tuple(line for line in self if line.contour_type is ContourType.MAJOR)

    def minor_contours(self) -> tuple[ContourLine, ...]:
        return tuple(line for line in self if line.contour_type is ContourType.MINOR)
