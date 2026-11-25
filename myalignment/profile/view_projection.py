from __future__ import annotations

from dataclasses import dataclass, field
import math

from myalignment.profile.projection_style import ProjectionStyle


@dataclass(frozen=True, slots=True)
class ProjectedPoint:
    """원시 측점과 표고로 표현한 투영점."""

    station: float = 0.0
    elevation: float = 0.0

    def __post_init__(self):
        if not math.isfinite(self.station) or not math.isfinite(self.elevation):
            raise ValueError("projected station and elevation must be finite")


@dataclass(frozen=True, slots=True)
class ProfileViewProjection:
    """종단 뷰 투영 결과. 경로 점은 원본 경로 순서다."""

    original_object: object | None = None
    name: str = ""
    start_station: float = 0.0
    end_station: float = 0.0
    elevation: float = 0.0
    projected_points: tuple[ProjectedPoint, ...] = ()
    style: ProjectionStyle = field(default_factory=ProjectionStyle.structure_style)

    def __post_init__(self):
        if not all(math.isfinite(value) for value in (self.start_station, self.end_station, self.elevation)):
            raise ValueError("projection stations and elevation must be finite")
        if self.end_station < self.start_station:
            raise ValueError("end_station must be at least start_station")
        points = tuple(self.projected_points)
        if any(not self.contains_station(point.station) for point in points):
            raise ValueError("projected points must be inside the projection station range")
        object.__setattr__(self, "projected_points", points)

    @property
    def length(self) -> float:
        return self.end_station - self.start_station

    def contains_station(self, station: float) -> bool:
        return self.start_station <= station <= self.end_station

    def clipped_paths(self, station_range: tuple[float, float]) -> tuple[tuple[ProjectedPoint, ...], ...]:
        """패널 경계의 표고를 보간하고 떨어진 경로를 별도로 반환한다."""
        low, high = station_range
        if high < self.start_station or low > self.end_station:
            return ()
        points = self.projected_points
        if not points:
            start = ProjectedPoint(max(low, self.start_station), self.elevation)
            end = ProjectedPoint(min(high, self.end_station), self.elevation)
            return ((start,) if start == end else (start, end),)
        if len(points) == 1:
            return (points,) if low <= points[0].station <= high else ()

        paths = []
        current = []
        for first, second in zip(points, points[1:]):
            piece = _clip_segment(first, second, low, high)
            if not piece or (current and current[-1] != piece[0]):
                if current:
                    paths.append(tuple(current))
                    current = []
            if piece:
                if not current:
                    current.append(piece[0])
                if piece[1] != current[-1]:
                    current.append(piece[1])
        if current:
            paths.append(tuple(current))
        return tuple(paths)


def _clip_segment(first, second, low, high):
    a, b = first.station, second.station
    start, end = max(min(a, b), low), min(max(a, b), high)
    if start > end:
        return ()
    if a == b:
        return first, second

    def at(station):
        if station == a:
            return first
        if station == b:
            return second
        fraction = (station - a) / (b - a)
        return ProjectedPoint(station, (1 - fraction) * first.elevation + fraction * second.elevation)

    return (at(start), at(end)) if a < b else (at(end), at(start))
