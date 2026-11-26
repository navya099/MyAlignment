from collections.abc import Callable
from dataclasses import replace
import math

from cadgeom import Point2d
from shapely import LineString, Polygon, box, make_valid

from myalignment.render.label_box import LabelBox
from myalignment.render.primitives import Primitive, PrimitiveType
from myalignment.render.scene import Scene
from myalignment.sheet.layout import Viewport


def _inside(bounds, x_min, y_min, x_max, y_max):
    x0, y0, x1, y1 = bounds
    return x0 - 1e-8 <= x_min and y0 - 1e-8 <= y_min and x_max <= x1 + 1e-8 and y_max <= y1 + 1e-8


def _outside(bounds, other):
    x0, y0, x1, y1 = bounds
    a, b, c, d = other
    return c < x0 or a > x1 or d < y0 or b > y1


def _parts(result, kind):
    if result.is_empty:
        return
    if result.geom_type == kind:
        yield result
    elif hasattr(result, "geoms"):
        for part in result.geoms:
            yield from _parts(part, kind)


def _arc_points(primitive):
    radius = primitive.radius
    circle = primitive.type is PrimitiveType.CIRCLE
    start = 0.0 if circle else primitive.start_angle % 360
    sweep = 360.0 if circle else (primitive.end_angle - primitive.start_angle) % 360
    if sweep == 0 and primitive.start_angle != primitive.end_angle:
        sweep = 360.0
    if sweep == 0:
        return ()
    # 최대 0.05mm의 현 오차를 기준으로 잘리는 호를 선분으로 근사한다.
    angle = math.degrees(2 * math.acos(max(-1.0, 1 - 0.05 / radius)))
    count = max(2, math.ceil(sweep / min(10.0, angle or 10.0)))
    center = primitive.points[0]
    angles = (math.radians(start + sweep * i / count) for i in range(count + 1))
    return tuple(Point2d(center.x + radius * math.cos(a), center.y + radius * math.sin(a)) for a in angles)


def _clipped(primitive, mask, bounds):
    kind, points = primitive.type, primitive.points
    if not points:
        return
    anchor = points[0]
    if kind is PrimitiveType.TEXT:
        label = LabelBox.from_text(
            anchor.x, anchor.y, primitive.text, primitive.text_height, rotation=primitive.rotation,
        )
        if _inside(bounds, label.x_min, label.y_min, label.x_max, label.y_max):
            yield primitive
        return
    if kind in (PrimitiveType.CIRCLE, PrimitiveType.ARC):
        radius = primitive.radius
        if radius <= 0:
            return
        extent = (anchor.x - radius, anchor.y - radius, anchor.x + radius, anchor.y + radius)
        if _inside(bounds, *extent):
            yield primitive
            return
        if _outside(bounds, extent):
            return
        points = _arc_points(primitive)
        if not points:
            return
        primitive = Primitive.polyline(points, style=primitive.style)
        kind = primitive.type
    if primitive.closed and points[-1] != anchor and kind is PrimitiveType.POLYLINE:
        points = (*points, anchor)

    xy = tuple((p.x, p.y) for p in points)
    x, y = zip(*xy)
    extent = min(x), min(y), max(x), max(y)
    if _outside(bounds, extent):
        return
    if _inside(bounds, *extent):
        yield primitive
        return
    if kind is PrimitiveType.POLYGON:
        shape = Polygon(xy)
        if not shape.is_valid:
            shape = make_valid(shape)
        for polygon in _parts(shape.intersection(mask), "Polygon"):
            # Primitive은 내부 링을 지원하지 않으므로 필요한 경우 면을 삼각형으로 나눈다.
            if polygon.interiors:
                from shapely import constrained_delaunay_triangles

                pieces = constrained_delaunay_triangles(polygon).geoms
            else:
                pieces = (polygon,)
            for piece in pieces:
                yield Primitive.polygon((Point2d(*p) for p in list(piece.exterior.coords)[:-1]), primitive.style)
        return
    for line in _parts(LineString(xy).intersection(mask), "LineString"):
        vertices = tuple(Point2d(*p) for p in line.coords)
        if kind is PrimitiveType.LINE and len(vertices) == 2:
            yield Primitive.line(*vertices, primitive.style)
        else:
            yield Primitive.polyline(vertices, closed=line.is_ring, style=primitive.style)


def place_scene(
    scene: Scene, source: Scene, viewport: Viewport, project: Callable[[Point2d], Point2d], *,
    rotation: float = 0.0, scale: float | None = None,
) -> Scene:
    """장면을 도면 좌표로 옮긴 뒤 뷰포트 바깥의 기하를 자른다."""
    if scale is None:
        scale = viewport.mm_per_m
    bounds = viewport.bounds
    mask = box(*bounds)
    for layer in source.layers:
        scene = scene.add_layer(layer)
    output = []
    for primitive in source.primitives:
        placed = replace(
            primitive, points=tuple(project(point) for point in primitive.points),
            radius=primitive.radius * scale, text_height=primitive.text_height * scale,
            rotation=primitive.rotation + rotation, start_angle=primitive.start_angle + math.degrees(rotation),
            end_angle=primitive.end_angle + math.degrees(rotation),
        )
        output.extend(_clipped(placed, mask, bounds))
    return scene.add_all(output)
