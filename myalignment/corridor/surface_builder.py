from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from myalignment.assembly.codes import LinkCode, PointCode
from myalignment.corridor.surface_code import CorridorSurfaceCode
from myalignment.surface.boundary import Boundary
from myalignment.surface.boundary_set import BoundarySet
from myalignment.surface.boundary_type import BoundaryType
from myalignment.surface.tin_point import TinPoint
from myalignment.surface.tin_surface import TinSurface
from myalignment.surface.triangle import Triangle

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.assembly.point import AssemblyPoint
    from myalignment.corridor.corridor import Corridor
    from myalignment.corridor.region import CorridorRegion
    from myalignment.profile.profile import Profile


_LINK_CODES = {
    CorridorSurfaceCode.TOP: (LinkCode.TOP, LinkCode.LANE, LinkCode.PAVEMENT, LinkCode.PAVEMENT_TOP, LinkCode.SHOULDER, LinkCode.SLOPE),
    CorridorSurfaceCode.PAVEMENT: (LinkCode.PAVEMENT, LinkCode.PAVEMENT_TOP),
    CorridorSurfaceCode.SUBBASE: (LinkCode.SUBBASE,),
    CorridorSurfaceCode.DATUM: (LinkCode.DATUM,),
    CorridorSurfaceCode.SLOPE: (LinkCode.SLOPE,),
    CorridorSurfaceCode.SHOULDER: (LinkCode.SHOULDER,),
    CorridorSurfaceCode.BALLAST: (LinkCode.BALLAST,),
}


@dataclass(frozen=True, slots=True)
class CorridorSurfaceSpec:
    """코드, 경계 및 측점 간격을 지정하는 표면 추출 사양."""

    name: str = ""
    code: CorridorSurfaceCode = CorridorSurfaceCode.TOP
    link_code: Enum | None = None
    point_code: Enum | None = None
    use_boundary: bool = True
    sample_frequency: float | None = 5.0

    def __post_init__(self):
        if self.sample_frequency is not None and (
            not math.isfinite(self.sample_frequency) or self.sample_frequency <= 0
        ):
            raise ValueError("sample_frequency must be finite and positive")
        if self.code is CorridorSurfaceCode.CUSTOM and self.link_code is None and self.point_code is None:
            raise ValueError("CUSTOM requires a link_code or point_code")


class CorridorSurfaceBuilder:
    """횡단면을 기준선 좌표계에 배치하고 TIN 표면을 추출한다."""

    @staticmethod
    def build(
        corridor: Corridor,
        spec: CorridorSurfaceSpec,
        *,
        alignments: Mapping[str, Alignment],
        profiles: Mapping[str, Profile] | None = None,
    ) -> TinSurface:
        """영역의 측점 범위에 해당하는 기준선과 이름으로 연결한다.

        종단 이름이 없는 기준선의 표고는 0이다. 종단 이름이 있으면
        기준선의 선형에서 먼저 찾고 profiles에서 보완한다.
        """
        use_region_mesh = spec.use_boundary or len(corridor.baselines) > 1
        points: dict[tuple[float, float], TinPoint] = {}
        boundaries: list[Boundary] = []
        triangles: list[Triangle] = []
        indices: dict[tuple[float, float], int] = {}

        def register(vertex: TinPoint) -> int:
            key = (vertex.x, vertex.y)
            previous = points.setdefault(key, vertex)
            if not math.isclose(previous.z, vertex.z, rel_tol=0, abs_tol=1e-8):
                raise ValueError(f"Conflicting elevations at XY {key}")
            return indices.setdefault(key, len(indices))

        for region in corridor.regions:
            if region.assembly is None:
                continue
            sections = []
            for station in region.sample_stations(spec.sample_frequency):
                selected = _section_points(region, station, spec)
                if selected:
                    sections.append((station, selected))
            if not sections:
                continue

            alignment, profile = _resolve_baseline(corridor, region, alignments, profiles)

            left_edge, right_edge = [], []
            region_points: dict[tuple[float, float], TinPoint] = {}
            for station, section in sections:
                elevation = profile.elevation_at(station) if profile is not None else 0.0
                xy = []
                for point in sorted(section, key=lambda p: p.x):
                    world = alignment.point_at(station, point.x)
                    key = (world.x, world.y)
                    vertex = TinPoint(*key, elevation + point.z)
                    if not use_region_mesh:
                        register(vertex)
                    previous = region_points.setdefault(key, vertex)
                    if not math.isclose(previous.z, vertex.z, rel_tol=0, abs_tol=1e-8):
                        raise ValueError(f"Conflicting elevations at XY {key}")
                    xy.append(key)
                left_edge.append(xy[0])
                right_edge.append(xy[-1])

            if use_region_mesh:
                ring = list(dict.fromkeys(left_edge + right_edge[::-1]))
                if len(left_edge) >= 2 and len(ring) >= 3:
                    boundary = Boundary.from_coords(ring, f"{region.name}_boundary")
                    region_surface = TinSurface.from_points(
                        list(region_points.values()), boundaries=BoundarySet((boundary,))
                    )
                    if region_surface.triangles:
                        boundaries.append(boundary)
                        region_indices = [register(vertex) for vertex in region_surface.points]
                        for triangle in region_surface.triangles:
                            triangles.append(Triangle(*sorted((
                                region_indices[triangle.a],
                                region_indices[triangle.b],
                                region_indices[triangle.c],
                            ))))

        name = spec.name or f"{corridor.name}_{spec.code.value}"
        if use_region_mesh:
            if not spec.use_boundary:
                boundaries = []
            elif len(boundaries) > 1:
                boundaries = [
                    Boundary(boundary.name, BoundaryType.SHOW, boundary.vertices)
                    for boundary in boundaries
                ]
            surface = TinSurface(
                name=name, points=tuple(points.values()),
                triangles=tuple(dict.fromkeys(triangles)),
                boundaries=BoundarySet(tuple(boundaries)),
            )
        else:
            surface = TinSurface.from_points(list(points.values()), name=name)
        if not surface.triangles:
            raise ValueError("Selected corridor points do not form a TIN")
        return surface


def _resolve_baseline(
    corridor: Corridor, region: CorridorRegion, alignments: Mapping[str, Alignment],
    profiles: Mapping[str, Profile] | None,
) -> tuple[Alignment, Profile | None]:
    baseline = corridor.baseline_for_region(region)
    if baseline is None:
        raise ValueError(f"{region.name}: expected exactly one baseline covering the region")
    alignment = alignments.get(baseline.alignment_name)
    if alignment is None:
        raise ValueError(f"Missing alignment: {baseline.alignment_name}")
    profile = None
    if baseline.profile_name:
        profile = next((p for p in alignment.profiles if p.name == baseline.profile_name), None)
        if profile is None and profiles is not None:
            profile = profiles.get(baseline.profile_name)
        if profile is None:
            raise ValueError(f"Missing profile: {baseline.profile_name}")
    return alignment, profile


def _section_points(
    region: CorridorRegion, station: float, spec: CorridorSurfaceSpec
) -> tuple[AssemblyPoint, ...]:
    points, links = region.cross_section_at(station)
    if spec.point_code is not None:
        return tuple(p for p in points if p.code == spec.point_code)
    if spec.link_code is None and spec.code is CorridorSurfaceCode.RAIL_TOP:
        return tuple(p for p in points if p.code in (PointCode.LEFT_RAIL, PointCode.RIGHT_RAIL))
    codes = (spec.link_code,) if spec.link_code is not None else _LINK_CODES[spec.code]
    return tuple(dict.fromkeys(
        point for link in links if link.code in codes for point in (link.start, link.end)
    ))
