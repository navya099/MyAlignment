from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass, replace
import math

from cadgeom import Point2d

from myalignment.profile.hatch_pattern import HatchPattern


def _elevation(points, station):
    index = bisect_left(points, station, key=lambda point: point.x)
    if points[index].x == station:
        return points[index].y
    a, b = points[index - 1], points[index]
    return a.y + (station - a.x) / (b.x - a.x) * (b.y - a.y)


@dataclass(frozen=True, slots=True)
class HatchRegion:
    """한 절토·성토 구간의 원시 측점과 표고 경계."""

    area_type: str = "fill"
    start_station: float = 0.0
    end_station: float = 0.0
    top_points: tuple[Point2d, ...] = ()
    bottom_points: tuple[Point2d, ...] = ()
    pattern: HatchPattern = HatchPattern.DIAGONAL
    color: int = 1
    opacity: float = 0.3

    def __post_init__(self):
        top, bottom = tuple(self.top_points), tuple(self.bottom_points)
        object.__setattr__(self, "top_points", top)
        object.__setattr__(self, "bottom_points", bottom)
        if self.area_type not in ("cut", "fill"):
            raise ValueError("area_type must be cut or fill")
        if not all(map(math.isfinite, (self.start_station, self.end_station))) or self.end_station < self.start_station:
            raise ValueError("invalid hatch station range")
        if top or bottom:
            if len(top) != len(bottom) or len(top) < 2:
                raise ValueError("hatch boundaries must have corresponding points")
            if top[0].x != self.start_station or top[-1].x != self.end_station:
                raise ValueError("hatch points must span the station range")
            if any(a.x >= b.x for a, b in zip(top, top[1:])) or any(
                a.x != b.x or a.y < b.y or not all(map(math.isfinite, (a.x, a.y, b.y)))
                for a, b in zip(top, bottom)
            ):
                raise ValueError("invalid hatch boundary coordinates")

    @property
    def length(self) -> float:
        return self.end_station - self.start_station

    @property
    def polygon(self) -> list[Point2d]:
        """공유 교차점의 중복을 제거한 외곽선을 반환한다."""
        points = []
        for point in (*self.top_points, *reversed(self.bottom_points)):
            if not points or point != points[-1]:
                points.append(point)
        return points[:-1] if len(points) > 1 and points[0] == points[-1] else points

    def area(self) -> float:
        """표고차를 적분한 종단면 면적(m²)."""
        depths = [top.y - bottom.y for top, bottom in zip(self.top_points, self.bottom_points)]
        return math.fsum(
            (b.x - a.x) * (d1 + d2) / 2
            for a, b, d1, d2 in zip(self.top_points, self.top_points[1:], depths, depths[1:])
        )

    def clipped(self, station_range: tuple[float, float]) -> HatchRegion | None:
        """렌더링 패널의 측점 범위로 자른다."""
        low, high = max(self.start_station, station_range[0]), min(self.end_station, station_range[1])
        if low >= high or not self.top_points:
            return None
        if (low, high) == (self.start_station, self.end_station):
            return self

        def trim(points):
            return (
                Point2d(low, _elevation(points, low)), *(p for p in points if low < p.x < high),
                Point2d(high, _elevation(points, high)),
            )

        return replace(self, start_station=low, end_station=high, top_points=trim(self.top_points),
                       bottom_points=trim(self.bottom_points))


@dataclass(frozen=True, slots=True)
class HatchCollection:
    """종단 해치와 일정 유효 폭을 적용한 토공량 추정치."""

    regions: tuple[HatchRegion, ...] = ()
    cut_volume_estimate: float = 0.0
    fill_volume_estimate: float = 0.0

    def __post_init__(self):
        object.__setattr__(self, "regions", tuple(self.regions))

    def __iter__(self):
        return iter(self.regions)

    def __len__(self):
        return len(self.regions)

    def cut_regions(self) -> tuple[HatchRegion, ...]:
        return tuple(region for region in self if region.area_type == "cut")

    def fill_regions(self) -> tuple[HatchRegion, ...]:
        return tuple(region for region in self if region.area_type == "fill")

    def total_area(self, area_type: str | None = None) -> float:
        return math.fsum(region.area() for region in self if area_type is None or region.area_type == area_type)

    @property
    def net_area(self) -> float:
        """절토 면적에서 성토 면적을 뺀 값."""
        return self.total_area("cut") - self.total_area("fill")
