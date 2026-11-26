from __future__ import annotations

import math


def surface_section_segments(surface, alignment, station):
    """횡단 평면과 TIN 삼각형의 교선을 횡거·표고 쌍으로 반환한다."""
    axis = alignment.point_at(station)
    bearing = alignment.tangent_at(station)
    ux, uy = math.cos(bearing), math.sin(bearing)
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
        if not intersections:
            continue
        yield min(intersections), max(intersections)
