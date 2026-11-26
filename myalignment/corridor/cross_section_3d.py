from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import math
from typing import TYPE_CHECKING

from myalignment.assembly.section_context import SectionContext
from myalignment.render.primitives_3d import Point3D

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.assembly.assembly import Assembly
    from myalignment.corridor.region import CorridorRegion
    from myalignment.target.mapping import TargetMapping


@dataclass(frozen=True, slots=True)
class CrossSection3D:
    """한 측점의 월드 좌표 횡단면과 링크 연결 정보."""

    station: float = 0.0
    points: tuple[Point3D, ...] = ()
    links: tuple[tuple[int, int], ...] = ()
    point_codes: tuple[Enum | None, ...] = ()
    link_codes: tuple[Enum | None, ...] = ()

    def __post_init__(self):
        if not math.isfinite(self.station):
            raise ValueError("station must be finite")
        if any(a == b or not 0 <= a < len(self.points) or not 0 <= b < len(self.points) for a, b in self.links):
            raise ValueError("Invalid cross-section link indices")
        if self.point_codes and len(self.point_codes) != len(self.points):
            raise ValueError("point_codes must match points")
        if self.link_codes and len(self.link_codes) != len(self.links):
            raise ValueError("link_codes must match links")

    @classmethod
    def from_assembly(
        cls, alignment: Alignment, station: float, assembly: Assembly,
        target_mapping: TargetMapping | None = None, offset_elevation: float = 0.0, *,
        context: SectionContext | None = None,
    ) -> CrossSection3D:
        if assembly.has_conditional:
            context = replace(context, station=station) if context is not None else SectionContext(station=station)
            points, links = assembly.generate_cross_section(target_mapping, context=context)
        else:
            points, links = assembly.generate_cross_section(target_mapping)
        return cls._from_local(alignment, station, points, links, offset_elevation)

    @classmethod
    def from_region(
        cls, alignment: Alignment, station: float, region: CorridorRegion, offset_elevation: float = 0.0, *,
        design_elevation: float | None = None, grade: float | None = None,
    ) -> CrossSection3D:
        if region.assembly.has_conditional and region.context_provider is None:
            context = SectionContext(station, design_elevation, grade)
            points, links = region.cross_section_at(station, context=context)
        else:
            points, links = region.cross_section_at(station)
        return cls._from_local(alignment, station, points, links, offset_elevation)

    @classmethod
    def _from_local(cls, alignment, station, points, links, elevation):
        indices = {}
        vertices = []
        point_codes = []

        def index_of(point):
            key = (round(point.x, 9), round(point.z, 9))
            if key not in indices:
                indices[key] = len(vertices)
                world = alignment.point_at(station, point.x)
                vertices.append(Point3D(world.x, world.y, elevation + point.z))
                point_codes.append(point.code)
            return indices[key]

        for point in points:
            index_of(point)
        indexed_links = []
        link_codes = []
        for link in links:
            start, end = index_of(link.start), index_of(link.end)
            if start != end:
                indexed_links.append((start, end))
                link_codes.append(link.code)
        return cls(station, tuple(vertices), tuple(indexed_links), tuple(point_codes), tuple(link_codes))
