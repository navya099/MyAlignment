from collections.abc import Callable

from myalignment.surface.tin_surface import TinSurface


XY = tuple[float, float]


def _cross(a: XY, b: XY, p: XY) -> float:
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def _clip(polygon: list[XY], signed_distance: Callable[[XY], float]) -> list[XY]:
    """선형 함수가 0 이상인 반평면으로 폴리곤을 자른다."""
    if not polygon:
        return []
    result = []
    start = polygon[-1]
    start_distance = signed_distance(start)
    for end in polygon:
        end_distance = signed_distance(end)
        if (start_distance < 0) != (end_distance < 0):
            fraction = start_distance / (start_distance - end_distance)
            result.append((
                start[0] + fraction * (end[0] - start[0]),
                start[1] + fraction * (end[1] - start[1]),
            ))
        if end_distance >= 0:
            result.append(end)
        start, start_distance = end, end_distance
    return result


def _faces(surface: TinSurface):
    for triangle in surface.triangles:
        vertices = triangle.vertices(surface.points)
        polygon = [(p.x, p.y) for p in vertices]
        winding = _cross(*polygon)
        if abs(winding) < 1e-12:
            continue
        if winding < 0:
            polygon.reverse()
        xs, ys = zip(*polygon)
        yield polygon, (min(xs), min(ys), max(xs), max(ys)), triangle.compute_coefficients(surface.points)


def _integrate(polygon: list[XY], height: Callable[[XY], float]) -> float:
    if len(polygon) < 3:
        return 0.0
    origin = polygon[0]
    return sum(
        abs(_cross(origin, a, b)) * (height(origin) + height(a) + height(b)) / 6
        for a, b in zip(polygon[1:], polygon[2:])
    )


def cut_fill_between(existing: TinSurface, design: TinSurface) -> tuple[float, float]:
    """공통 TIN 면적에서 원지형과 설계면의 표고차를 적분한다."""
    if (
        existing.triangles == design.triangles
        and len(existing.points) == len(design.points)
        and all((a.x, a.y) == (b.x, b.y) for a, b in zip(existing.points, design.points))
    ):
        return _cut_fill_matching_mesh(existing, design)

    cut = fill = 0.0
    existing_faces = list(_faces(existing))
    for design_polygon, (dx0, dy0, dx1, dy1), (da, db, dc) in _faces(design):
        for existing_polygon, (ex0, ey0, ex1, ey1), (ea, eb, ec) in existing_faces:
            if dx1 <= ex0 or ex1 <= dx0 or dy1 <= ey0 or ey1 <= dy0:
                continue
            overlap = design_polygon
            for a, b in zip(existing_polygon, existing_polygon[1:] + existing_polygon[:1]):
                overlap = _clip(overlap, lambda p: _cross(a, b, p))
            if len(overlap) < 3:
                continue

            def depth(p: XY) -> float:
                return (ea - da) * p[0] + (eb - db) * p[1] + (ec - dc)

            def fill_depth(p: XY) -> float:
                return -depth(p)

            cut += _integrate(_clip(overlap, depth), depth)
            fill += _integrate(_clip(overlap, fill_depth), fill_depth)
    return cut, fill


def cut_fill_at_elevation(existing: TinSurface, target_elevation: float) -> tuple[float, float]:
    """기준 표고의 위와 아래에서 체적을 각각 적분한다."""
    return _cut_fill_on_mesh(existing, lambda _: target_elevation)


def _cut_fill_matching_mesh(existing: TinSurface, design: TinSurface) -> tuple[float, float]:
    return _cut_fill_on_mesh(existing, lambda index: design.points[index].z)


def _cut_fill_on_mesh(existing: TinSurface, design_elevation: Callable[[int], float]) -> tuple[float, float]:
    cut = fill = 0.0
    for triangle in existing.triangles:
        a, b, c = triangle.vertices(existing.points)
        polygon = [(a.x, a.y), (b.x, b.y), (c.x, c.y)]
        heights = (
            a.z - design_elevation(triangle.a),
            b.z - design_elevation(triangle.b),
            c.z - design_elevation(triangle.c),
        )
        twice_area = _cross(*polygon)
        if abs(twice_area) < 1e-12:
            continue
        if min(heights) >= 0:
            cut += abs(twice_area) * sum(heights) / 6
        elif max(heights) <= 0:
            fill -= abs(twice_area) * sum(heights) / 6
        else:
            def depth(p: XY) -> float:
                wb = _cross(polygon[0], p, polygon[2]) / twice_area
                wc = _cross(polygon[0], polygon[1], p) / twice_area
                return heights[0] + wb * (heights[1] - heights[0]) + wc * (heights[2] - heights[0])

            def fill_depth(p: XY) -> float:
                return -depth(p)

            cut += _integrate(_clip(polygon, depth), depth)
            fill += _integrate(_clip(polygon, fill_depth), fill_depth)
    return cut, fill
