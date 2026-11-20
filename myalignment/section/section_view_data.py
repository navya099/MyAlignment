from __future__ import annotations

from dataclasses import dataclass
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.corridor.cross_section_3d import CrossSection3D


@dataclass(frozen=True, slots=True)
class SectionPoint:
    offset: float = 0.0
    elevation: float = 0.0

    def __post_init__(self):
        if not math.isfinite(self.offset) or not math.isfinite(self.elevation):
            raise ValueError("Section coordinates must be finite")


@dataclass(frozen=True, slots=True)
class SectionLink:
    start: SectionPoint
    end: SectionPoint
    code: str = ""
    slope: float = 0.0


@dataclass(frozen=True, slots=True)
class SectionViewData:
    station: float = 0.0
    points: tuple[SectionPoint, ...] = ()
    links: tuple[SectionLink, ...] = ()
    surface_points: tuple[SectionPoint, ...] = ()
    surface_links: tuple[tuple[int, int], ...] = ()

    def __post_init__(self):
        if not math.isfinite(self.station):
            raise ValueError("station must be finite")
        if any(a == b or not (0 <= a < len(self.surface_points) and 0 <= b < len(self.surface_points))
               for a, b in self.surface_links):
            raise ValueError("Invalid surface link indices")

    @property
    def min_offset(self) -> float:
        return min((p.offset for p in self.points + self.surface_points), default=0.0)

    @property
    def max_offset(self) -> float:
        return max((p.offset for p in self.points + self.surface_points), default=0.0)

    @property
    def min_elevation(self) -> float:
        return min((p.elevation for p in self.points + self.surface_points), default=0.0)

    @property
    def max_elevation(self) -> float:
        return max((p.elevation for p in self.points + self.surface_points), default=0.0)

    @classmethod
    def from_cross_section_3d(cls, section_3d: CrossSection3D, alignment: Alignment) -> SectionViewData:
        station = section_3d.station
        center = alignment.point_at(station)
        azimuth = alignment.tangent_at(station)
        # Alignment.point_at()과 동일하게 진행 방향 오른쪽이 양의 횡거다.
        nx, ny = math.sin(azimuth), -math.cos(azimuth)
        points = tuple(SectionPoint((p.x - center.x) * nx + (p.y - center.y) * ny, p.z)
                       for p in section_3d.points)
        links = []
        for index, (a, b) in enumerate(section_3d.links):
            start, end = points[a], points[b]
            dx = end.offset - start.offset
            slope = 100 * (end.elevation - start.elevation) / dx if abs(dx) > 1e-9 else 0.0
            code = section_3d.link_codes[index] if section_3d.link_codes else None
            links.append(SectionLink(start, end, getattr(code, "value", ""), slope))
        return cls(station, points, tuple(links))
