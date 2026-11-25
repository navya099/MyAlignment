from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
import math
from typing import TYPE_CHECKING

from myalignment.render.scene import Scene
from myalignment.render.section_view_renderer import SectionViewRenderer
from myalignment.section.section_view_builder import SectionViewBuilder
from myalignment.section.section_view_data import SectionPoint

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.corridor.corridor import Corridor
    from myalignment.profile.profile import Profile
    from myalignment.section.label_set import SectionLabelSet
    from myalignment.section.section_projection import SectionProjection
    from myalignment.section.section_view_style import SectionViewStyle
    from myalignment.surface.tin_surface import TinSurface


class SectionViewComposer:
    """설계 횡단면에 TIN 지표면 단면을 겹쳐 그린다."""

    @classmethod
    def with_surface(
        cls, corridor: Corridor, alignment: Alignment, station: float, surface: TinSurface,
        style: SectionViewStyle | None = None, *, profile: Profile | None = None,
        label_set: SectionLabelSet | None = None,
        offset_elevation: float = 0.0,
        projections: Sequence[SectionProjection] = (),
    ) -> Scene:
        data = SectionViewBuilder.build_data(
            corridor, alignment, station, profile=profile, offset_elevation=offset_elevation,
        )
        points, links = _surface_section(surface, alignment, station, min(-20, data.min_offset), max(20, data.max_offset))
        return SectionViewRenderer.render(
            Scene(), replace(data, surface_points=points, surface_links=links), style, label_set,
            projections=projections,
        )


def _surface_section(surface, alignment, station, low, high):
    """횡단 직선과 TIN 삼각형의 교선을 구하고 지표면 공백을 보존한다."""
    axis = alignment.point_at(station)
    bearing = alignment.tangent_at(station)
    ux, uy = math.cos(bearing), math.sin(bearing)
    points = []
    indices = {}
    links = {}

    def index(offset, elevation):
        key = round(offset, 9), round(elevation, 9)
        if key not in indices:
            indices[key] = len(points)
            points.append(SectionPoint(offset, elevation))
        return indices[key]

    for triangle in surface.triangles:
        vertices = []
        for p in triangle.vertices(surface.points):
            x, y = p.x - axis.x, p.y - axis.y
            along = x * ux + y * uy
            vertices.append((along if abs(along) > 1e-9 else 0.0, x * uy - y * ux, p.z))
        intersections = [(offset, elevation) for along, offset, elevation in vertices if along == 0]
        for a, b in zip(vertices, vertices[1:] + vertices[:1]):
            if a[0] * b[0] < 0:
                fraction = a[0] / (a[0] - b[0])
                intersections.append((a[1] + fraction * (b[1] - a[1]), a[2] + fraction * (b[2] - a[2])))
        if len(intersections) < 2:
            continue
        (start, z0), (end, z1) = min(intersections), max(intersections)
        left, right = max(low, start), min(high, end)
        if right - left <= 1e-9:
            continue
        slope = (z1 - z0) / (end - start)
        a = index(left, z0 + (left - start) * slope)
        b = index(right, z0 + (right - start) * slope)
        if a != b:
            links.setdefault((a, b), None)
    return tuple(points), tuple(links)
