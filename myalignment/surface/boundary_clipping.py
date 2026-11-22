from collections.abc import Iterator
from dataclasses import replace

from shapely import constrained_delaunay_triangles, prepare, union_all
from shapely.geometry import LineString, Point, Polygon
from shapely.validation import explain_validity

from myalignment.surface.boundary import Boundary
from myalignment.surface.boundary_set import BoundarySet
from myalignment.surface.breakline_set import BreaklineSet
from myalignment.surface.breakline_type import BreaklineType
from myalignment.surface.breakline_vertex import BreaklineVertex
from myalignment.surface.tin_point import TinPoint
from myalignment.surface.triangle import Triangle


def _polygon(boundary: Boundary):
    polygon = Polygon([(vertex.x, vertex.y) for vertex in boundary.vertices])
    if not polygon.is_valid:
        raise ValueError(f"경계 {boundary.name!r}: {explain_validity(polygon)}")
    return polygon


def _data_mask(boundaries: BoundarySet):
    mask = None
    for boundary in boundaries.data_clip_boundaries:
        polygon = _polygon(boundary)
        mask = polygon if mask is None else mask.intersection(polygon)
    return mask


def clip_input_data(
    points: tuple[TinPoint, ...], breaklines: BreaklineSet, boundaries: BoundarySet,
) -> tuple[tuple[TinPoint, ...], BreaklineSet]:
    """DATA_CLIP 외부의 측량점과 브레이크라인 부분을 삼각분할 전에 제외한다."""
    mask = _data_mask(boundaries)
    if mask is None:
        return points, breaklines
    prepare(mask)

    selected = tuple(p for p in points if mask.covers(Point(p.x, p.y)))
    clipped = []
    for line in breaklines:
        if line.breakline_type is BreaklineType.NON_DESTRUCTIVE:
            continue
        if all(mask.covers(Point(p.x, p.y)) for p in line.vertices):
            path = LineString([(p.x, p.y) for p in line.vertices])
            if mask.covers(path):
                clipped.append(line)
                continue
        for i, (a, b) in enumerate(zip(line.vertices, line.vertices[1:])):
            dx, dy = b.x - a.x, b.y - a.y
            length2 = dx * dx + dy * dy
            if not length2:
                continue
            segment = LineString([(a.x, a.y), (b.x, b.y)])
            for part in _line_parts(mask.intersection(segment)):
                vertices = []
                right = []
                ends = sorted(
                    (((x - a.x) * dx + (y - a.y) * dy) / length2, x, y)
                    for x, y in (part.coords[0], part.coords[-1])
                )
                if ends[0][0] == ends[-1][0]:
                    continue
                for fraction, x, y in ends:
                    vertices.append(BreaklineVertex(x, y, a.z + fraction * (b.z - a.z)))
                    if line.right_elevations:
                        z0, z1 = line.right_elevations[i:i + 2]
                        right.append(z0 + fraction * (z1 - z0))
                clipped.append(replace(line, vertices=tuple(vertices), right_elevations=tuple(right)))
    return selected, BreaklineSet(tuple(clipped))


def _mask(boundaries: BoundarySet, points: tuple[TinPoint, ...]):
    if boundaries.outer is not None:
        mask = _polygon(boundaries.outer)
    elif boundaries.show_boundaries:
        mask = union_all([_polygon(boundary) for boundary in boundaries.show_boundaries])
    else:
        min_x, max_x = min(p.x for p in points), max(p.x for p in points)
        min_y, max_y = min(p.y for p in points), max(p.y for p in points)
        # 외곽이 없을 때는 점 집합을 완전히 포함하는 영역에서 빼기만 한다.
        pad = max(1.0, max_x - min_x, max_y - min_y)
        mask = Polygon([
            (min_x - pad, min_y - pad), (max_x + pad, min_y - pad),
            (max_x + pad, max_y + pad), (min_x - pad, max_y + pad),
        ])
    if boundaries.outer is not None and boundaries.show_boundaries:
        mask = mask.intersection(union_all([_polygon(b) for b in boundaries.show_boundaries]))
    data = _data_mask(boundaries)
    if data is not None:
        mask = mask.intersection(data)
    if boundaries.hide_boundaries:
        mask = mask.difference(union_all([_polygon(b) for b in boundaries.hide_boundaries]))
    return mask


def _polygon_parts(geometry) -> Iterator[Polygon]:
    if geometry.geom_type == "Polygon":
        if not geometry.is_empty:
            yield geometry
    elif geometry.geom_type in ("MultiPolygon", "GeometryCollection"):
        for part in geometry.geoms:
            yield from _polygon_parts(part)


def _line_parts(geometry) -> Iterator[LineString]:
    if geometry.geom_type == "LineString":
        if not geometry.is_empty:
            yield geometry
    elif geometry.geom_type in ("MultiLineString", "GeometryCollection"):
        for part in geometry.geoms:
            yield from _line_parts(part)


def _wall_parts(vertices: tuple[TinPoint, ...], mask):
    """XY 투영이 선분인 수직 벽면을 원래 3D 면에서 잘라낸다."""
    a, b = max(
        ((a, b) for i, a in enumerate(vertices) for b in vertices[i + 1:]),
        key=lambda pair: (pair[1].x - pair[0].x) ** 2 + (pair[1].y - pair[0].y) ** 2,
    )
    dx, dy = b.x - a.x, b.y - a.y
    length2 = dx * dx + dy * dy
    if not length2:
        return
    line = LineString([(a.x, a.y), (b.x, b.y)])

    def parameter(x, y):
        return ((x - a.x) * dx + (y - a.y) * dy) / length2

    for segment in _line_parts(line.intersection(mask)):
        lo, hi = sorted((parameter(*segment.coords[0]), parameter(*segment.coords[-1])))
        polygon = [(parameter(p.x, p.y), p) for p in vertices]
        for limit, direction in ((lo, 1), (hi, -1)):
            clipped = []
            for (t0, p0), (t1, p1) in zip(polygon[-1:] + polygon[:-1], polygon):
                inside0, inside1 = (t0 - limit) * direction >= 0, (t1 - limit) * direction >= 0
                if inside0 != inside1:
                    fraction = (limit - t0) / (t1 - t0)
                    clipped.append((limit, TinPoint(
                        a.x + limit * dx, a.y + limit * dy, p0.z + fraction * (p1.z - p0.z),
                    )))
                if inside1:
                    clipped.append((t1, p1))
            polygon = clipped
        corners = list(dict.fromkeys(point for _, point in polygon))
        if len(corners) >= 3:
            for p, q in zip(corners[1:], corners[2:]):
                yield corners[0], p, q


def clip_mesh(
    points: tuple[TinPoint, ...], triangles: tuple[Triangle, ...], boundaries: BoundarySet,
) -> tuple[tuple[TinPoint, ...], tuple[Triangle, ...]]:
    """경계로 자른 면에 원본 삼각형의 표고를 보간한다."""
    if not triangles or not (
        boundaries.outer or boundaries.hide_boundaries or boundaries.show_boundaries or boundaries.data_clip_boundaries
    ):
        return points, triangles
    mask = _mask(boundaries, points)
    prepare(mask)
    mask_edges = mask.boundary
    prepare(mask_edges)
    vertices = list(points)

    def key(point):
        return round(point.x, 9), round(point.y, 9), round(point.z, 9)

    indices = {key(point): i for i, point in enumerate(points)}
    faces = []

    def append_face(corners):
        ids = []
        for point in corners:
            index = indices.setdefault(key(point), len(vertices))
            if index == len(vertices):
                vertices.append(point)
            ids.append(index)
        if len(set(ids)) == 3:
            faces.append(Triangle(*sorted(ids)))

    for face in triangles:
        a, b, c = face.vertices(points)
        dx1, dy1, dx2, dy2 = b.x - a.x, b.y - a.y, c.x - a.x, c.y - a.y
        det = dx1 * dy2 - dy1 * dx2
        if abs(det) < 1e-12:
            if face.area_3d(points) > 0:
                for piece in _wall_parts((a, b, c), mask):
                    append_face(piece)
            continue

        polygon = Polygon([(a.x, a.y), (b.x, b.y), (c.x, c.y)])
        if not mask.intersects(polygon):
            continue
        covered = mask.covers(polygon)
        if covered and not mask_edges.intersects(polygon):
            faces.append(face)
            continue

        # 경계가 공유 변에 접하면 양쪽 면이 같은 정점을 사용해야 한다.
        intersection = mask.intersection(polygon)
        if covered and intersection.geom_type == "Polygon" and len(intersection.exterior.coords) == 4:
            faces.append(face)
            continue
        for piece in _polygon_parts(intersection):
            if piece.area < 5e-13:
                continue
            for fragment in constrained_delaunay_triangles(piece).geoms:
                corners = []
                for x, y in fragment.exterior.coords[:-1]:
                    dx, dy = x - a.x, y - a.y
                    w1 = (dx * dy2 - dy * dx2) / det
                    w2 = (dx1 * dy - dy1 * dx) / det
                    corners.append(TinPoint(x, y, a.z + w1 * (b.z - a.z) + w2 * (c.z - a.z)))
                append_face(corners)

    if tuple(faces) == triangles:
        return points, triangles
    used = sorted({i for face in faces for i in (face.a, face.b, face.c)})
    remap = {index: compact for compact, index in enumerate(used)}
    return (
        tuple(vertices[i] for i in used),
        tuple(Triangle(remap[face.a], remap[face.b], remap[face.c]) for face in dict.fromkeys(faces)),
    )
