from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.alignment.label_component import AlignmentLabelComponentType, ReferenceObjectType
from myalignment.alignment.label_type import AlignmentLabelType
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
    for label_type, interval in ((kind.MAJOR_STATION, major_interval), (kind.MINOR_STATION, minor_interval)):
        if alignment.label_set.get_style(label_type) is None:
            continue
        for station in _stations(alignment, interval):
            if label_type is kind.MINOR_STATION and math.isclose(
                station, round(station / major_interval) * major_interval,
                rel_tol=0.0, abs_tol=min(interval, major_interval) * 1e-9,
            ) and alignment.label_set.get_style(kind.MAJOR_STATION) is not None:
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
                "Alignment Station": f"{projection.station:.2f}",
                "Alignment Offset": f"{projection.offset:.3f}",
            }
    except ValueError:
        pass
    return {}


class AlignmentLabelRenderer:
    """평면선형의 측점, 기하점, 구간 및 참조 텍스트를 렌더링한다."""

    @classmethod
    def render(
        cls, scene: Scene, alignment: Alignment, surface: TinSurface | None = None, *,
        profile: Profile | None = None, reference_alignment: Alignment | None = None,
        major_interval: float = 100.0, minor_interval: float = 20.0,
    ) -> Scene:
        """종단은 현재 STA, 참조 선형은 현재 XY의 투영점으로 조회한다."""
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
                "Station Value": f"{station:.2f}", "Northing": f"{point.y:.3f}",
                "Easting": f"{point.x:.3f}", "Design Speed": f"{alignment.design_speed:g}",
                "Bearing": f"{math.degrees(azimuth) % 360:.2f}°",
            })
            style = alignment.label_set.get_style(label_type)
            cached_references = {}
            for component in style.components:
                if not component.visible:
                    continue
                origin = Point2d(point.x + component.offset_x, point.y + component.offset_y)
                primitive_style = Style(color=component.text_color, layer=component.layer)
                component_type = component.component_type
                if component_type is AlignmentLabelComponentType.TEXT:
                    values = fields
                    if component.reference_type is not ReferenceObjectType.NONE:
                        if component.reference_type not in cached_references:
                            cached_references[component.reference_type] = _reference_values(
                                component.reference_type, references[component.reference_type], station, point,
                            )
                        values = {**fields, **cached_references[component.reference_type]}

                    def evaluate(match):
                        key = match[1].split("(", 1)[0]
                        return values.get(key, "???")

                    text = _FIELD.sub(evaluate, component.contents)
                    for row, line in enumerate(text.replace("\\P", "\n").splitlines()):
                        if line:
                            primitives.append(Primitive.text(
                                Point2d(origin.x, origin.y - row * component.text_height),
                                line, component.text_height, component.rotation, primitive_style,
                            ))
                elif component_type in (AlignmentLabelComponentType.LINE, AlignmentLabelComponentType.TICK):
                    angle = component.rotation
                    if component_type is AlignmentLabelComponentType.TICK:
                        angle += azimuth + math.pi / 2
                    dx, dy = math.cos(angle), math.sin(angle)
                    primitives.append(Primitive.line(
                        Point2d(origin.x - dx, origin.y - dy),
                        Point2d(origin.x + dx, origin.y + dy), primitive_style,
                    ))
                else:
                    continue
                layers.setdefault(component.layer, Layer(component.layer, color=component.text_color))

        for layer in layers.values():
            scene = scene.add_layer(layer)
        return scene.add_all(primitives) if primitives else scene
