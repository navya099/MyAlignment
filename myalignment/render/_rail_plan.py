from cadgeom import Point2d

from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene


def cross_marker(point: Point2d, style: Style, size: float = 2, *, radius: float | None = None):
    x, y = point.x, point.y
    return (
        Primitive.line(Point2d(x - size, y - size), Point2d(x + size, y + size), style),
        Primitive.line(Point2d(x - size, y + size), Point2d(x + size, y - size), style),
        Primitive.circle(point, size if radius is None else radius, style),
    )


def add_plan_primitives(scene: Scene, primitives: list[Primitive]) -> Scene:
    for layer, color in {p.style.layer: p.style.color for p in primitives}.items():
        scene = scene.add_layer(Layer(layer, color=color))
    return scene.add_all(primitives) if primitives else scene
