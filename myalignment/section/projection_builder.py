from __future__ import annotations

import math
from typing import TYPE_CHECKING

from myalignment.alignment.intersection import intersect_ray_with_collection
from myalignment.section.projection_object_type import SectionProjectionObjectType as ObjectType
from myalignment.section.projection_style import SectionProjectionStyle
from myalignment.section.section_projection import SectionProjectedPoint, SectionProjection
from myalignment.structure.struturetype import StructureType

if TYPE_CHECKING:
    from cadgeom import Point2d
    from myalignment.alignment.alignment import Alignment
    from myalignment.featureline.feature_line import FeatureLine
    from myalignment.profile.profile import Profile
    from myalignment.structure.structure import Structure


_PLANE_TOLERANCE = 1e-8


def _section_axes(alignment, station):
    origin = alignment.point_at(station)
    bearing = alignment.tangent_at(station)
    return origin, bearing


def _local_coordinates(origin, bearing, x, y):
    dx, dy = x - origin.x, y - origin.y
    ux, uy = math.cos(bearing), math.sin(bearing)
    return dx * ux + dy * uy, dx * uy - dy * ux


def _point_offset(alignment, station, point, tolerance):
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("station_tolerance must be finite and nonnegative")
    origin, bearing = _section_axes(alignment, station)
    along, offset = _local_coordinates(origin, bearing, point.x, point.y)
    if not (math.isfinite(along) and math.isfinite(offset)):
        raise ValueError("projection point must have finite coordinates")
    return offset if abs(along) <= tolerance + _PLANE_TOLERANCE else None


def _profile_at(profiles, station):
    return next((p for p in profiles if p.is_valid and p.start_station <= station <= p.end_station), None)


def _projected_geometry(source, name, object_type, points, style, links=()):
    points = tuple(points)
    if not points:
        return None
    return SectionProjection(
        source, name, object_type,
        min(p.offset for p in points), max(p.offset for p in points),
        min(p.elevation for p in points), max(p.elevation for p in points),
        points, style, projected_links=links,
    )


class SectionProjectionBuilder:
    """원본 객체를 선택한 기하 측점의 횡거와 표고로 변환한다."""

    @classmethod
    def project_structure(
        cls, alignment: Alignment, station: float, structure: Structure,
        style: SectionProjectionStyle | None = None, *, profile: Profile | None = None,
    ) -> SectionProjection | None:
        """구조물 구간에서 상판 또는 터널의 단면 외곽 범위를 계산한다."""
        if not structure.contains_station(station):
            return None
        alignment.point_at(station)
        style = style or SectionProjectionStyle.structure_style()
        metadata = structure.metadata
        if profile is None:
            profile = _profile_at(alignment.profiles, station)
        bottom = float(metadata["bottom_elevation"]) if "bottom_elevation" in metadata else (
            profile.elevation_at(station) if profile is not None else 0.0
        )
        if structure.structure_type is StructureType.TUNNEL:
            width = height = float(metadata.get("diameter", 2 * style.deck_height))
            pier_bottom = None
        else:
            width = float(metadata.get("width", 20.0))
            height = float(metadata.get("deck_height", style.deck_height))
            pier_bottom = float(metadata["pier_bottom_elevation"]) if "pier_bottom_elevation" in metadata else None
        if any(not math.isfinite(value) or value <= 0 for value in (width, height)):
            raise ValueError("structure width and height must be finite and positive")
        return SectionProjection(
            structure, structure.name, ObjectType.STRUCTURE,
            -width / 2, width / 2, bottom, bottom + height, style=style,
            pier_bottom_elevation=pier_bottom,
        )

    @classmethod
    def project_pipe(
        cls, alignment: Alignment, station: float, pipe_center: Point2d,
        pipe_elevation: float, pipe_diameter: float | None = None,
        name: str = "Pipe", style: SectionProjectionStyle | None = None, *,
        station_tolerance: float = 1.0,
    ) -> SectionProjection | None:
        """횡단면 허용 거리 안에 있는 원형 관의 단면을 만든다."""
        style = style or SectionProjectionStyle.pipe_style()
        diameter = style.pipe_diameter if pipe_diameter is None else pipe_diameter
        if not math.isfinite(diameter) or diameter <= 0 or not math.isfinite(pipe_elevation):
            raise ValueError("pipe diameter must be positive and elevation finite")
        offset = _point_offset(alignment, station, pipe_center, station_tolerance)
        if offset is None:
            return None
        radius = diameter / 2
        return SectionProjection(
            pipe_center, name, ObjectType.PIPE, offset - radius, offset + radius,
            pipe_elevation - radius, pipe_elevation + radius, style=style, diameter=diameter,
        )

    @classmethod
    def project_point(
        cls, alignment: Alignment, station: float, point: Point2d, elevation: float,
        name: str = "Point", style: SectionProjectionStyle | None = None, *,
        station_tolerance: float = 1.0,
    ) -> SectionProjection | None:
        """횡단면 허용 거리 안에 있는 원본 점을 투영한다."""
        if not math.isfinite(elevation):
            raise ValueError("point elevation must be finite")
        offset = _point_offset(alignment, station, point, station_tolerance)
        if offset is None:
            return None
        return _projected_geometry(point, name, ObjectType.POINT, (SectionProjectedPoint(offset, elevation),),
                                   style or SectionProjectionStyle.point_style())

    @classmethod
    def project_feature_line(
        cls, alignment: Alignment, station: float, feature_line: FeatureLine,
        style: SectionProjectionStyle | None = None,
    ) -> SectionProjection | None:
        """횡단면을 지나는 선분의 교차 표고를 보간하고 면 위의 선분을 보존한다."""
        origin, bearing = _section_axes(alignment, station)
        vertices = []
        for vertex in feature_line.vertices:
            along, offset = _local_coordinates(origin, bearing, vertex.x, vertex.y)
            vertices.append((0.0 if abs(along) <= _PLANE_TOLERANCE else along,
                             SectionProjectedPoint(offset, vertex.z)))
        following = vertices[1:] + (vertices[:1] if feature_line.is_closed else [])
        indices = {}
        links = {}
        for (a, start), (b, end) in zip(vertices, following):
            if a == 0:
                start_index = indices.setdefault(start, len(indices))
            if b == 0:
                end_index = indices.setdefault(end, len(indices))
                if a == 0 and start_index != end_index:
                    links.setdefault(tuple(sorted((start_index, end_index))), None)
            if (a < 0 < b) or (b < 0 < a):
                fraction = a / (a - b)
                hit = SectionProjectedPoint(
                    start.offset + fraction * (end.offset - start.offset),
                    start.elevation + fraction * (end.elevation - start.elevation),
                )
                indices.setdefault(hit, len(indices))
        return _projected_geometry(
            feature_line, feature_line.name or "FeatureLine", ObjectType.FEATURE_LINE, indices,
            style or SectionProjectionStyle.feature_line_style(), tuple(links),
        )

    @classmethod
    def project_alignment(
        cls, alignment: Alignment, station: float, other: Alignment,
        style: SectionProjectionStyle | None = None, *, profile: Profile | None = None,
    ) -> SectionProjection | None:
        """대상 선형과 횡단선의 교차점을 대상 종단 표고에 표시한다."""
        origin, bearing = _section_axes(alignment, station)
        profiles = (profile,) if profile is not None else other.profiles
        points = {}
        for normal in (bearing - math.pi / 2, bearing + math.pi / 2):
            for point, target_station in intersect_ray_with_collection(origin, normal, other.entities):
                target_profile = _profile_at(profiles, target_station)
                if target_profile is None:
                    continue
                _, offset = _local_coordinates(origin, bearing, point.x, point.y)
                hit = SectionProjectedPoint(offset, target_profile.elevation_at(target_station))
                points.setdefault((round(offset, 8), round(hit.elevation, 8)), hit)
        return _projected_geometry(
            other, other.name or "Alignment", ObjectType.ALIGNMENT, points.values(),
            style or SectionProjectionStyle.alignment_style(),
        )
