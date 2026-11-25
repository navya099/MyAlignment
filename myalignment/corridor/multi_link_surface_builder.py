from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
import math
from typing import TYPE_CHECKING

from shapely import Polygon, union_all

from myalignment.assembly.codes import LinkCode
from myalignment.corridor.link_surface_spec import LinkSurfaceSpec
from myalignment.corridor.surface_builder import CorridorSurfaceBuilder, CorridorSurfaceSpec, _resolve_baseline
from myalignment.corridor.surface_code import CorridorSurfaceCode
from myalignment.corridor.surface_extraction_mode import SurfaceExtractionMode
from myalignment.surface.boundary import Boundary
from myalignment.surface.boundary_set import BoundarySet
from myalignment.surface.boundary_type import BoundaryType
from myalignment.surface.tin_point import TinPoint
from myalignment.surface.tin_surface import TinSurface
from myalignment.surface.triangle import Triangle

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.corridor.corridor import Corridor
    from myalignment.profile.profile import Profile


_Face = tuple[TinPoint, TinPoint, TinPoint]
_ELEVATION_TOL = 1e-8


@dataclass(frozen=True, slots=True)
class LinkSurfaceResult:
    """추출된 표면과 선택한 링크 코드, 렌더링 색상."""

    surface: TinSurface
    link_code: LinkCode | None = None
    link_codes: tuple[LinkCode, ...] = ()
    color: int | None = None

    @property
    def point_count(self) -> int:
        return len(self.surface.points)

    @property
    def triangle_count(self) -> int:
        return len(self.surface.triangles)


def _xy(point: TinPoint) -> tuple[float, float]:
    return point.x, point.y


def _det(face: _Face) -> float:
    a, b, c = face
    return (b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y)


def _section_links(selected, station, alignment, profile):
    elevation = profile.elevation_at(station) if profile is not None else 0.0
    vertices = {}
    sections = defaultdict(list)
    for link in selected:
        start, end = sorted((link.start, link.end), key=lambda point: point.x)
        for point in (start, end):
            if point not in vertices:
                world = alignment.point_at(station, point.x)
                vertices[point] = TinPoint(world.x, world.y, elevation + point.z)
        sections[link.code].append((
            (start.code, end.code, link.shape_code), vertices[start], vertices[end],
        ))
    return sections


def _collect_faces(corridor, alignments, profiles, codes, sample_frequency):
    faces = defaultdict(list)
    for region in corridor.regions:
        if region.assembly is None:
            continue
        stations = region.sample_stations(sample_frequency)
        if len(stations) < 2:
            continue
        alignment = None
        previous = {}
        for station in stations:
            _, links = region.cross_section_at(station)
            selected = [link for link in links if link.code in codes]
            if not selected:
                previous = {}
                continue
            if alignment is None:
                alignment, profile = _resolve_baseline(corridor, region, alignments, profiles)
            current = _section_links(selected, station, alignment, profile)
            for code in current.keys() & previous.keys():
                first, second = previous[code], current[code]
                if [item[0] for item in first] != [item[0] for item in second]:
                    raise ValueError(f"{region.name} STA {station}: {code.value} link topology changed")
                for (_, a, b), (_, c, d) in zip(first, second, strict=True):
                    for face in ((a, b, d), (a, d, c)):
                        if abs(_det(face)) >= 1e-12:
                            faces[code].append(face)
            previous = current
    return faces


def _unique_faces(faces, overhang_correction):
    unique = {}
    for face in faces:
        ordered = tuple(sorted(face, key=_xy))
        key = tuple(map(_xy, ordered))
        previous = unique.setdefault(key, ordered)
        differences = tuple(a.z - b.z for a, b in zip(ordered, previous, strict=True))
        if all(abs(dz) <= _ELEVATION_TOL for dz in differences):
            continue
        if overhang_correction and all(dz >= 0 for dz in differences):
            unique[key] = ordered
        elif not (overhang_correction and all(dz <= 0 for dz in differences)):
            raise ValueError("Conflicting elevations in coincident projected link triangles")
    return unique.values()


def _build_surface(name: str, faces, spec: LinkSurfaceSpec) -> TinSurface:
    unique = _unique_faces(faces, spec.overhang_correction)
    if not unique:
        raise ValueError(f"{name}: selected links do not form a TIN")
    polygons = [Polygon(tuple(map(_xy, face))) for face in unique]
    footprint = union_all(polygons)
    if not math.isclose(footprint.area, math.fsum(p.area for p in polygons), rel_tol=1e-9, abs_tol=1e-10):
        raise ValueError(f"{name}: projected link triangles overlap")

    points = {}
    indices = {}
    triangles = []
    for face in unique:
        face_indices = []
        for vertex in face:
            key = _xy(vertex)
            previous = points.setdefault(key, vertex)
            if not math.isclose(previous.z, vertex.z, rel_tol=0, abs_tol=_ELEVATION_TOL):
                raise ValueError(f"{name}: conflicting elevations at XY {key}")
            face_indices.append(indices.setdefault(key, len(indices)))
        triangles.append(Triangle(*sorted(face_indices)))

    boundaries = []
    if spec.use_boundary:
        parts = (footprint,) if footprint.geom_type == "Polygon" else footprint.geoms
        for index, polygon in enumerate(parts, 1):
            boundaries.append(Boundary.from_coords(
                list(polygon.exterior.coords)[:-1], f"{name}_boundary_{index}",
                BoundaryType.SHOW,
            ))
            for hole_index, hole in enumerate(polygon.interiors, 1):
                boundaries.append(Boundary.from_coords(
                    list(hole.coords)[:-1], f"{name}_hole_{index}_{hole_index}", BoundaryType.HIDE,
                ))
    return TinSurface(name, tuple(points.values()), tuple(triangles), BoundarySet(tuple(boundaries)))


class MultiLinkSurfaceBuilder:
    """연속 횡단면의 같은 링크를 연결하여 코드별 TIN을 추출한다."""

    @classmethod
    def build_from_spec(
        cls,
        corridor: Corridor,
        spec: LinkSurfaceSpec,
        *,
        alignments: Mapping[str, Alignment],
        profiles: Mapping[str, Profile] | None = None,
    ) -> LinkSurfaceResult | list[LinkSurfaceResult]:
        """사양으로 표면을 추출한다. ALL_LINKS는 코드별 결과 리스트를 반환한다."""
        mode = spec.mode
        if mode is SurfaceExtractionMode.POINT_BASED:
            surface = CorridorSurfaceBuilder.build(corridor, CorridorSurfaceSpec(
                name=spec.name, code=CorridorSurfaceCode.CUSTOM, point_code=spec.point_code,
                use_boundary=spec.use_boundary, sample_frequency=spec.sample_frequency,
            ), alignments=alignments, profiles=profiles)
            return LinkSurfaceResult(surface, color=spec.color)

        codes = spec.get_all_codes()
        faces = _collect_faces(corridor, alignments, profiles, frozenset(codes or tuple(LinkCode)), spec.sample_frequency)
        if mode is SurfaceExtractionMode.ALL_LINKS:
            return [
                LinkSurfaceResult(_build_surface(f"{spec.name}_{code.value}", faces[code], spec), code, (code,), spec.color)
                for code in (codes or tuple(LinkCode)) if faces.get(code)
            ]
        surface = _build_surface(spec.name, (face for code in codes for face in faces.get(code, ())), spec)
        return LinkSurfaceResult(surface, spec.link_code if mode is SurfaceExtractionMode.SINGLE_LINK else None,
                                 codes, spec.color)

    @classmethod
    def build_all_links(
        cls,
        corridor: Corridor,
        name_prefix: str | None = None,
        use_boundary: bool = True,
        *,
        alignments: Mapping[str, Alignment],
        profiles: Mapping[str, Profile] | None = None,
        sample_frequency: float | None = None,
    ) -> list[LinkSurfaceResult]:
        """평면 투영 면적이 있는 모든 코드에 대해 별도의 TIN을 반환한다."""
        spec = LinkSurfaceSpec(
            name=name_prefix or corridor.name or "Corridor", mode=SurfaceExtractionMode.ALL_LINKS,
            use_boundary=use_boundary, sample_frequency=sample_frequency,
        )
        return cls.build_from_spec(corridor, spec, alignments=alignments, profiles=profiles)
