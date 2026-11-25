from __future__ import annotations

from collections.abc import Sequence
import math
from typing import TYPE_CHECKING, Protocol

from cadgeom import Point2d

from myalignment.profile.projection_object_type import ProjectionObjectType as Kind
from myalignment.profile.projection_style import ProjectionStyle
from myalignment.profile.view_projection import ProfileViewProjection, ProjectedPoint

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.featureline.feature_line import FeatureLine
    from myalignment.profile.profile import Profile
    from myalignment.structure.structure import Structure


class _Point3DLike(Protocol):
    @property
    def x(self) -> float: ...

    @property
    def y(self) -> float: ...

    @property
    def z(self) -> float: ...


def _station(alignment, point):
    if not math.isfinite(point.x) or not math.isfinite(point.y):
        raise ValueError("projection point coordinates must be finite")
    return alignment.project(Point2d(point.x, point.y)).station


def _style(style, default, *kinds):
    if style is None:
        return default()
    if style.object_type not in kinds:
        raise ValueError("projection style does not match the projected object type")
    return style


class ProjectionBuilder:
    """평면 객체를 원시 측점과 표고로 변환한다."""

    @classmethod
    def project_structure(
        cls, alignment: Alignment, profile: Profile, structure: Structure,
        style: ProjectionStyle | None = None,
    ) -> ProfileViewProjection:
        """구조물 범위와 표시 가능한 구간 중앙의 참조 종단 표고를 사용한다."""
        style = _style(style, ProjectionStyle.structure_style, Kind.STRUCTURE)
        start = max(alignment.start_station, profile.start_station, structure.start_station)
        end = min(alignment.end_station, profile.end_station, structure.end_station)
        if not alignment.is_valid or not profile.is_valid or start > end:
            raise ValueError(f"{structure.name}: structure outside alignment and profile coverage")
        elevation = profile.elevation_at((start + end) / 2)
        return ProfileViewProjection(
            structure, structure.name or "Structure", structure.start_station, structure.end_station,
            elevation, style=style,
        )

    @classmethod
    def project_feature_line(
        cls, alignment: Alignment, profile: Profile, feature_line: FeatureLine,
        style: ProjectionStyle | None = None,
    ) -> ProfileViewProjection:
        """정점 표고와 원래 순서를 유지한다. 대표 표고는 참조 종단을 우선한다."""
        style = _style(style, ProjectionStyle.feature_line_style, Kind.FEATURE_LINE)
        vertices = feature_line.vertices
        if feature_line.is_closed and vertices[-1] != vertices[0]:
            vertices = (*vertices, vertices[0])
        points = tuple(ProjectedPoint(_station(alignment, point), point.z) for point in vertices)
        start, end = min(p.station for p in points), max(p.station for p in points)
        mid = (start + end) / 2
        elevation = profile.elevation_at(mid) if profile.is_valid and profile.start_station <= mid <= profile.end_station else (
            points[0].elevation
        )
        return ProfileViewProjection(feature_line, feature_line.name or "FeatureLine", start, end, elevation, points, style)

    @classmethod
    def project_alignment_crossing(
        cls, main_alignment: Alignment, profile: Profile, cross_alignment: Alignment,
        style: ProjectionStyle | None = None,
    ) -> ProfileViewProjection | None:
        """참조 종단에서 표고를 읽을 수 있는 첫 교차점의 투영을 반환한다."""
        return next(iter(cls.project_alignment_crossings(main_alignment, profile, cross_alignment, style)), None)

    @classmethod
    def project_alignment_crossings(
        cls, main_alignment: Alignment, profile: Profile, cross_alignment: Alignment,
        style: ProjectionStyle | None = None,
    ) -> list[ProfileViewProjection]:
        """참조 종단 범위에 있는 모든 교차점을 원시 측점 순서로 반환한다."""
        style = _style(style, ProjectionStyle.alignment_style, Kind.ALIGNMENT)
        if not profile.is_valid:
            raise ValueError("a valid reference profile is required")
        return [
            ProfileViewProjection(
                cross_alignment, cross_alignment.name or "CrossAlignment", station, station,
                profile.elevation_at(station), style=style,
            )
            for station in sorted({point.station for point in main_alignment.intersection_with(cross_alignment)})
            if profile.start_station <= station <= profile.end_station
        ]

    @classmethod
    def project_point(
        cls, alignment: Alignment, profile: Profile, point: Point2d | _Point3DLike,
        name: str = "Point", style: ProjectionStyle | None = None, *, elevation: float | None = None,
    ) -> ProfileViewProjection:
        """점 또는 블록 삽입점을 투영한다. 명시한 표고, 점 Z, 종단 표고 순으로 사용한다."""
        style = _style(style, ProjectionStyle.point_style, Kind.POINT, Kind.BLOCK)
        station = _station(alignment, point)
        if elevation is None:
            elevation = getattr(point, "z", None)
        if elevation is None:
            elevation = profile.elevation_at(station)
        return ProfileViewProjection(point, name, station, station, elevation, style=style)

    @classmethod
    def project_pipe(
        cls, alignment: Alignment, vertices: Sequence[_Point3DLike], name: str = "Pipe",
        style: ProjectionStyle | None = None,
    ) -> ProfileViewProjection:
        """좌표가 주어진 관로 중심 경로를 정점 표고 그대로 투영한다."""
        style = _style(style, lambda: ProjectionStyle(name="Pipe", object_type=Kind.PIPE), Kind.PIPE)
        points = tuple(ProjectedPoint(_station(alignment, point), point.z) for point in vertices)
        if len(points) < 2:
            raise ValueError("at least two pipe vertices are required")
        return ProfileViewProjection(
            tuple(vertices), name, min(p.station for p in points), max(p.station for p in points),
            points[0].elevation, points, style,
        )
