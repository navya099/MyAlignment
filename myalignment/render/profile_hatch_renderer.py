from __future__ import annotations

import math
from typing import TYPE_CHECKING

from cadgeom import Point2d
from shapely.geometry import LineString, Point, Polygon

from myalignment.profile.hatch_pattern import HatchPattern
from myalignment.profile.hatch_style import ProfileHatchStyle
from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene
from myalignment.render.viewport import Viewport, ViewportType

if TYPE_CHECKING:
    from myalignment.profile.hatch_region import HatchCollection
    from myalignment.profile.profile import Profile
    from myalignment.profile.view_style import ProfileViewStyle


_ANGLES = {
    HatchPattern.DIAGONAL: (math.pi / 4,),
    HatchPattern.CROSS: (math.pi / 4, -math.pi / 4),
    HatchPattern.HORIZONTAL: (0,),
    HatchPattern.VERTICAL: (math.pi / 2,),
}


def _grid(low, high, spacing):
    return (index * spacing for index in range(math.ceil(low / spacing), math.floor(high / spacing) + 1))


def _lines(geometry):
    if geometry.geom_type == "LineString" and not geometry.is_empty:
        yield geometry
    elif hasattr(geometry, "geoms"):
        for part in geometry.geoms:
            yield from _lines(part)


def _hatch_lines(polygon, angle, spacing, style):
    ux, uy = math.cos(angle), math.sin(angle)
    nx, ny = -uy, ux
    rotated = [(x * ux + y * uy, x * nx + y * ny) for x, y in polygon.exterior.coords]
    along, across = zip(*rotated)
    lo, hi = min(along) - spacing, max(along) + spacing
    for ordinate in _grid(min(across), max(across), spacing):
        line = LineString((
            (lo * ux + ordinate * nx, lo * uy + ordinate * ny),
            (hi * ux + ordinate * nx, hi * uy + ordinate * ny),
        ))
        for part in _lines(polygon.intersection(line)):
            start, end = part.coords[0], part.coords[-1]
            if part.length > 1e-9:
                yield Primitive.line(Point2d(*start), Point2d(*end), style)


def _hatch_dots(polygon, spacing, style):
    x0, y0, x1, y1 = polygon.bounds
    radius = spacing * 0.08
    for x in _grid(x0, x1, spacing):
        for y in _grid(y0, y1, spacing):
            center = Point(x, y)
            if polygon.contains(center) and polygon.exterior.distance(center) >= radius:
                yield Primitive.circle(Point2d(x, y), radius, style)


class ProfileHatchRenderer:
    """종단 뷰 좌표에서 해치 패턴을 영역 경계로 자른다."""

    @staticmethod
    def render(
        scene: Scene, hatches: HatchCollection, view_style: ProfileViewStyle, profile: Profile | None = None,
        style: ProfileHatchStyle | None = None, *, station_range: tuple[float, float] | None = None,
    ) -> Scene:
        viewport = Viewport(ViewportType.PROFILE, view_style.vertical_exaggeration)
        if station_range is None and profile is not None:
            station_range = (profile.start_station, profile.end_station)
        appearance = style or ProfileHatchStyle.standard()
        primitives, layers = [], {}
        for item in hatches:
            region = item.clipped(station_range) if station_range is not None else item
            if region is None or region.area() <= 0:
                continue
            side = region.area_type
            if not getattr(appearance, f"show_{side}"):
                continue
            color = getattr(style, f"{side}_color") if style is not None else region.color
            if appearance.show_net:
                color = appearance.net_color
            pattern = getattr(style, f"{side}_pattern") if style is not None else region.pattern
            opacity = getattr(style, f"{side}_opacity") if style is not None else region.opacity
            layer = getattr(appearance, f"{side}_layer")
            spacing = getattr(appearance, f"{side}_spacing")
            points = tuple(viewport.project(p.x, p.y) for p in region.polygon)
            polygon = Polygon([(p.x, p.y) for p in points])
            if not polygon.is_valid or not polygon.area:
                raise ValueError("hatch region must form a valid polygon")
            stroke = Style(color=color, lineweight=appearance.lineweight, layer=layer, opacity=opacity)
            if opacity > 0:
                layers.setdefault(layer, Layer(layer, color=color))
                if pattern is HatchPattern.SOLID:
                    primitives.append(Primitive.polygon(points, stroke))
                elif pattern is HatchPattern.DOTS:
                    primitives.extend(_hatch_dots(polygon, spacing, stroke))
                else:
                    for angle in _ANGLES[pattern]:
                        primitives.extend(_hatch_lines(polygon, angle, spacing, stroke))
            if appearance.boundary_lineweight > 0:
                name = appearance.boundary_layer
                layers.setdefault(name, Layer(name, color=color))
                boundary = Style(color=color, lineweight=appearance.boundary_lineweight, layer=name)
                primitives.append(Primitive.polyline(points, closed=True, style=boundary))
        for layer in layers.values():
            scene = scene.add_layer(layer)
        return scene.add_all(primitives) if primitives else scene
