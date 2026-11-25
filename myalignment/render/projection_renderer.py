from __future__ import annotations

from collections.abc import Iterator, Sequence
import math
from string import Formatter
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.profile.projection_object_type import ProjectionObjectType as Kind
from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene
from myalignment.render.viewport import Viewport, ViewportType

if TYPE_CHECKING:
    from myalignment.profile.profile import Profile
    from myalignment.profile.view_projection import ProfileViewProjection
    from myalignment.profile.view_style import ProfileViewStyle


def _marker(point: Point2d, style: Style, kind: Kind) -> Iterator[Primitive]:
    x, y = point.x, point.y
    if kind in (Kind.POINT, Kind.BLOCK):
        yield Primitive.line(Point2d(x - 2, y - 2), Point2d(x + 2, y + 2), style)
        yield Primitive.line(Point2d(x - 2, y + 2), Point2d(x + 2, y - 2), style)
    else:
        height = 5 if kind is Kind.ALIGNMENT else 2
        yield Primitive.line(Point2d(x, y - height), Point2d(x, y + height), style)


def _primitives(projection, viewport, station_range):
    paths = projection.clipped_paths(station_range)
    if not paths:
        return
    style = projection.style
    kind = style.object_type
    if style.show_range:
        line = Style(color=style.range_color, layer=style.layer, lineweight=style.range_lineweight)
        for path in paths:
            if len(path) == 2:
                yield Primitive.line(*(viewport.project(point.station, point.elevation) for point in path), style=line)
            elif len(path) > 2:
                yield Primitive.polyline((viewport.project(point.station, point.elevation) for point in path), style=line)

    if style.show_marker:
        marker = Style(color=style.marker_color, layer=style.layer, lineweight=style.marker_lineweight)
        if projection.projected_points:
            endpoints = dict.fromkeys((projection.projected_points[0], projection.projected_points[-1]))
            for point in endpoints:
                if station_range[0] <= point.station <= station_range[1]:
                    yield from _marker(viewport.project(point.station, point.elevation), marker, kind)
        else:
            for station in dict.fromkeys((projection.start_station, projection.end_station)):
                if station_range[0] <= station <= station_range[1]:
                    yield from _marker(viewport.project(station, projection.elevation), marker, kind)

    if style.show_label:
        path = max(paths, key=len)
        left, right = path[(len(path) - 1) // 2], path[len(path) // 2]
        elevation = (left.elevation + right.elevation) / 2
        at = viewport.project((left.station + right.station) / 2, elevation)
        values = {
            "name": projection.name, "start_sta": projection.start_station, "end_sta": projection.end_station,
            "elevation": elevation,
        }
        rows = style.label_format.replace("\\P", "\n").splitlines()
        rendered = []
        has_elevation = False
        for row in rows:
            includes = any(field == "elevation" for _, field, _, _ in Formatter().parse(row))
            if not includes or style.show_elevation:
                rendered.extend(row.format(**values).splitlines())
                has_elevation |= includes
        if style.show_elevation and not has_elevation:
            rendered.append(f"EL {elevation:.3f}")
        label = Style(color=style.label_color, layer=style.layer)
        for index, row in enumerate(line for line in rendered if line):
            yield Primitive.text(
                Point2d(at.x + 2, at.y + (len(rendered) - index) * style.text_height),
                row, style.text_height, style=label,
            )


class ProjectionRenderer:
    """투영 객체를 종단 뷰 그리드와 동일한 좌표계에 렌더링한다."""

    @classmethod
    def render(
        cls,
        scene: Scene,
        projections: Sequence[ProfileViewProjection],
        view_style: ProfileViewStyle,
        profile: Profile | None = None,
        min_sta: float | None = None,
        max_sta: float | None = None,
    ) -> Scene:
        """패널 범위 안의 경로와 레이블만 기존 장면에 추가한다."""
        if not projections:
            return scene
        if min_sta is None:
            min_sta = profile.start_station if profile is not None else min(item.start_station for item in projections)
        if max_sta is None:
            max_sta = profile.end_station if profile is not None else max(item.end_station for item in projections)
        if not math.isfinite(min_sta) or not math.isfinite(max_sta) or min_sta > max_sta:
            raise ValueError("projection station range must be finite and ordered")
        viewport = Viewport(ViewportType.PROFILE, view_style.vertical_exaggeration)
        primitives = [
            primitive
            for projection in projections
            for primitive in _primitives(projection, viewport, (min_sta, max_sta))
        ]
        if not primitives:
            return scene
        layers = {}
        for primitive in primitives:
            appearance = primitive.style
            layers.setdefault(appearance.layer, Layer(appearance.layer, color=appearance.color))
        for layer in layers.values():
            scene = scene.add_layer(layer)
        return scene.add_all(primitives)
