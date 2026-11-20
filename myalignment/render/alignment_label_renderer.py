from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.alignment.label_component import AlignmentLabelComponentType, ReferenceObjectType
from myalignment.alignment.label_type import AlignmentLabelType
from myalignment.alignment.station_equation_type import StationEquationType
from myalignment.enum.alignmententitytype import AlignmentEntityType
from myalignment.profile.geometry_extractor import GeometryPointExtractor
from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.profile.profile import Profile
    from myalignment.surface.tin_surface import TinSurface


_FIELD = re.compile(r"<\[([^\[\]]+)\]>")
_SEGMENT_TYPES = {
    AlignmentEntityType.Line: AlignmentLabelType.LINE,
    AlignmentEntityType.Arc: AlignmentLabelType.CURVE,
    AlignmentEntityType.Spiral: AlignmentLabelType.SPIRAL,
}


def _stations(alignment, interval):
    first = math.ceil(math.nextafter(alignment.start_station / interval, -math.inf))
    last = math.floor(math.nextafter(alignment.end_station / interval, math.inf))
    return (
        min(alignment.end_station, max(alignment.start_station, i * interval))
        for i in range(first, last + 1)
    )


def _anchors(alignment, major_interval, minor_interval):
    kind = AlignmentLabelType
    for label_type, interval in ((kind.MINOR_STATION, minor_interval), (kind.MAJOR_STATION, major_interval)):
        if alignment.label_set.get_style(label_type) is None:
            continue
        for station in _stations(alignment, interval):
            if label_type is kind.MINOR_STATION and math.isclose(
                station, round(station / major_interval) * major_interval,
                rel_tol=0.0, abs_tol=min(interval, major_interval) * 1e-9,
            ):
                continue
            yield label_type, station, {}

    entities = alignment.entities.entities
    if alignment.label_set.get_style(kind.GEOMETRY_POINT) is not None:
        transitions = {
            before.end_station: (before.entity_type.name, after.entity_type.name)
            for before, after in zip(entities, entities[1:])
        }
        for point in GeometryPointExtractor.extract(alignment):
            before, after = transitions[point.station]
            yield kind.GEOMETRY_POINT, point.station, {
                "Geometry Point Text": point.point_type.value,
                "Entity Before": before,
                "Entity After": after,
                "Radius": f"{point.radius:.2f}" if point.radius > 0 else "???",
            }

    for entity in entities:
        label_type = _SEGMENT_TYPES.get(entity.entity_type)
        if label_type is None or alignment.label_set.get_style(label_type) is None:
            continue
        station = (entity.start_station + entity.end_station) / 2
        fields = {"Distance": f"{entity.length:.2f}", "Length": f"{entity.length:.2f}"}
        if label_type is kind.CURVE:
            radius, delta = entity.geometry.radius, abs(entity.geometry.delta)
            fields.update({
                "Radius": f"{radius:.2f}", "Delta": f"{math.degrees(delta):.2f}°",
                "Tangent": f"{radius * math.tan(delta / 2):.2f}" if delta < math.pi else "???",
            })
        elif label_type is kind.SPIRAL:
            fields.update({
                "Radius": f"{entity.geometry.radius:.2f}",
                "Delta": f"{abs(math.degrees(entity.end_azimuth - entity.start_azimuth)):.2f}°",
            })
        yield label_type, station, fields


def _reference_values(reference_type, target, station, point):
    if target is None:
        return {}
    try:
        if reference_type is ReferenceObjectType.SURFACE:
            elevation = target.elevation_at(point.x, point.y)
            return {"Surface Elevation": f"{elevation:.3f}"} if math.isfinite(elevation) else {}
        if reference_type is ReferenceObjectType.PROFILE:
            return {"Profile Name": target.name, "Profile Elevation": f"{target.elevation_at(station):.3f}"}
        if reference_type is ReferenceObjectType.ALIGNMENT and target.is_valid:
            projection = target.project(point)
            return {
                "Alignment Name": target.name,
                "Alignment Station": f"{target.raw_to_display_station(projection.station):.2f}",
                "Alignment Offset": f"{projection.offset:.3f}",
            }
    except ValueError:
        pass
    return {}


def _component_primitives(component, point, azimuth, values):
    origin = Point2d(point.x + component.offset_x, point.y + component.offset_y)
    style = Style(color=component.text_color, layer=component.layer)
    kind = component.component_type
    if kind is AlignmentLabelComponentType.TEXT:
        def evaluate(match):
            key = match[1].split("(", 1)[0]
            return values.get(key, "???")

        text = _FIELD.sub(evaluate, component.contents)
        for row, line in enumerate(text.replace("\\P", "\n").splitlines()):
            if line:
                yield Primitive.text(
                    Point2d(origin.x, origin.y - row * component.text_height),
                    line, component.text_height, component.rotation, style,
                )
    elif kind in (AlignmentLabelComponentType.LINE, AlignmentLabelComponentType.TICK):
        angle = component.rotation
        if kind is AlignmentLabelComponentType.TICK:
            angle += azimuth
            if component.tick_direction == "vertical":
                angle += math.pi / 2
        dx, dy = component.size * math.cos(angle), component.size * math.sin(angle)
        yield Primitive.line(
            Point2d(origin.x - dx, origin.y - dy), Point2d(origin.x + dx, origin.y + dy), style,
        )


def _equation_primitives(alignment, style):
    previous = None
    for equation in alignment.station_equations:
        raw = equation.raw_station_back
        back = raw
        if previous is not None:
            back = previous.station_ahead + previous.equation_type.sign * (raw - previous.raw_station_back)
        previous = equation
        if not alignment.start_station <= raw <= alignment.end_station:
            continue

        point = alignment.point_at(raw)
        azimuth = alignment.tangent_at(raw)
        suffix = (
            style.increasing_suffix if equation.equation_type is StationEquationType.INCREASING
            else style.decreasing_suffix
        )
        fields = {
            "Station Ahead": f"{equation.station_ahead:.2f}",
            "Station Back": f"{back:.2f}",
            "Raw Station": f"{raw:.2f}",
            "Delta": f"{equation.delta:+.2f}",
            "Station Jump": f"{equation.station_ahead - back:+.2f}",
            "Equation Suffix": suffix,
        }
        for component in style.components:
            if not component.visible:
                continue
            keys = {field.split("(", 1)[0] for field in _FIELD.findall(component.contents)}
            if not style.show_raw_station and "Raw Station" in keys:
                continue
            if not style.show_delta and keys.intersection(("Delta", "Station Jump")):
                continue
            yield from _component_primitives(component, point, azimuth, fields)


class AlignmentLabelRenderer:
    """평면선형의 측점, 기하점, 구간 및 참조 텍스트를 렌더링한다."""

    MAJOR_INTERVAL = 100.0
    MINOR_INTERVAL = 20.0

    @classmethod
    def render(
        cls, scene: Scene, alignment: Alignment, surface: TinSurface | None = None, *,
        profile: Profile | None = None, reference_alignment: Alignment | None = None,
        major_interval: float | None = None, minor_interval: float | None = None,
        render_equations: bool = True,
    ) -> Scene:
        """종단은 현재 STA, 참조 선형은 현재 XY의 투영점으로 조회한다."""
        major_interval = cls.MAJOR_INTERVAL if major_interval is None else major_interval
        minor_interval = cls.MINOR_INTERVAL if minor_interval is None else minor_interval
        for interval in (major_interval, minor_interval):
            if not math.isfinite(interval) or interval <= 0:
                raise ValueError("station intervals must be finite and positive")
        if not alignment.is_valid:
            return scene

        references = {
            ReferenceObjectType.SURFACE: surface,
            ReferenceObjectType.PROFILE: profile,
            ReferenceObjectType.ALIGNMENT: reference_alignment,
        }
        primitives = []
        layers = {}
        for label_type, station, fields in _anchors(alignment, major_interval, minor_interval):
            point = alignment.point_at(station)
            azimuth = alignment.tangent_at(station)
            fields.update({
                "Station Value": f"{alignment.raw_to_display_station(station):.2f}",
                "Raw Station": f"{station:.2f}", "Northing": f"{point.y:.3f}",
                "Easting": f"{point.x:.3f}", "Design Speed": f"{alignment.design_speed:g}",
                "Bearing": f"{math.degrees(azimuth) % 360:.2f}°",
            })
            style = alignment.label_set.get_style(label_type)
            cached_references = {}
            for component in style.components:
                if not component.visible:
                    continue
                values = fields
                reference = component.reference_type
                if (component.component_type is AlignmentLabelComponentType.TEXT
                        and reference is not ReferenceObjectType.NONE):
                    if reference not in cached_references:
                        cached_references[reference] = _reference_values(
                            reference, references[reference], station, point,
                        )
                    values = {**fields, **cached_references[reference]}
                primitives.extend(_component_primitives(component, point, azimuth, values))

        equation_style = alignment.label_set.equation_style
        if render_equations and equation_style is not None:
            primitives.extend(_equation_primitives(alignment, equation_style))

        for primitive in primitives:
            style = primitive.style
            layers.setdefault(style.layer, Layer(style.layer, color=style.color))
        for layer in layers.values():
            scene = scene.add_layer(layer)
        return scene.add_all(primitives) if primitives else scene
