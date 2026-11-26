from collections.abc import Iterable
from typing import TYPE_CHECKING

from shapely import LineString, Point, Polygon, STRtree

if TYPE_CHECKING:
    from myalignment.pressure.pipe import PressurePipe
    from myalignment.surface.tin_surface import TinSurface


def _pipe_cover(pipe, points, faces, triangles, index):
    if not pipe.centerline:
        return None
    start, end = pipe.centerline
    outer_radius = pipe.part.outer_diameter_m / 2
    a, b = (start.x, start.y), (end.x, end.y)
    if a == b:
        return min((
            faces[i].elevation_at(*a, points) - max(start.z, end.z) - outer_radius
            for i in index.query(Point(*a), predicate="intersects")
        ), default=None)

    path = LineString((a, b))
    dx, dy = b[0] - a[0], b[1] - a[1]
    ux, uy = dx / path.length, dy / path.length
    dz = end.z - start.z
    intervals = []
    min_cover = None
    for i in index.query(path, predicate="intersects"):
        face = faces[i]
        crossing = triangles[i].intersection(path)
        if crossing.is_empty:
            continue
        fractions = []
        for x, y in crossing.coords:
            fraction = min(1.0, max(0.0, ((x - a[0]) * ux + (y - a[1]) * uy) / path.length))
            fractions.append(fraction)
            cover = face.elevation_at(x, y, points) - (start.z + fraction * dz) - outer_radius
            min_cover = cover if min_cover is None else min(min_cover, cover)
        intervals.append((min(fractions), max(fractions)))

    cursor = 0.0
    tolerance = max(1e-12, 1e-8 / path.length)
    for low, high in sorted(intervals):
        if low > cursor + tolerance:
            return None
        cursor = max(cursor, high)
    return min_cover if cursor >= 1 - tolerance else None


def _minimum_covers(pipes: Iterable["PressurePipe"], surface: "TinSurface") -> tuple[float | None, ...]:
    points = surface.points
    faces = tuple(face for face in surface.triangles if face.area_2d(points) >= 5e-13)
    triangles = tuple(Polygon([(p.x, p.y) for p in face.vertices(points)]) for face in faces)
    index = STRtree(triangles)
    return tuple(_pipe_cover(pipe, points, faces, triangles, index) for pipe in pipes)
