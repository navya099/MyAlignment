from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
import math
import re
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.alignment.curve_label_style import CurveLabelStyle
from myalignment.alignment.curve_spiral_extractor import CurveSpiralExtractor
from myalignment.alignment.label_component import AlignmentLabelComponentType, ReferenceObjectType
from myalignment.alignment.label_type import AlignmentLabelType
from myalignment.alignment.spiral_label_style import SpiralLabelStyle
from myalignment.alignment.station_equation_type import StationEquationType
from myalignment.enum.alignmententitytype import AlignmentEntityType
from myalignment.profile.geometry_extractor import GeometryPointExtractor
from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.alignment.station_offset_label import StationOffsetLabel
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


def _geometry_fields(alignment, info, style, label_type):
    specialized = isinstance(style, (CurveLabelStyle, SpiralLabelStyle))

    def number(key):
        value = info[key]
        precision = 3 if specialized else 2
        return f"{value:.{precision}f}" if value is not None else "—"

    def station(key):
        value = info[key]
        return f"{alignment.raw_to_display_station(value):.2f}" if value is not None else "—"

    key = "delta" if label_type is AlignmentLabelType.CURVE else "theta"
    angle = (CurveSpiralExtractor.format_angle(info[key], style.angle_format) if specialized
             else f"{math.degrees(info[key]):.2f}°")
    fields = {"Radius": number("radius"), "Length": number("length"), "Delta": angle}
    if label_type is AlignmentLabelType.CURVE:
        fields.update({
            "Tangent": number("tangent"), "External": number("external"),
            "Mid-ordinate": number("mid_ordinate"), "Mid Ordinate": number("mid_ordinate"),
            "Chord": number("chord"), "BC Station": station("start_station"), "EC Station": station("end_station"),
            "BC Easting": f"{info['bc_point'].x:.3f}", "BC Northing": f"{info['bc_point'].y:.3f}",
            "EC Easting": f"{info['ec_point'].x:.3f}", "EC Northing": f"{info['ec_point'].y:.3f}",
        })
        if not specialized and info["tangent"] is None:
            fields["Tangent"] = "???"
    else:
        fields.update({
            "Theta": angle, "A Value": number("a_value"), "Spiral Type": info["spiral_type"],
            "X": number("x"), "Y": number("y"),
            **{f"{code.upper()} Station": station(f"{code}_station") for code in ("ts", "sc", "cs", "st")},
        })
    return fields


def _hidden_fields(style):
    options = {
        "Radius": "show_radius", "Delta": "show_delta", "Length": "show_length",
        "Distance": "show_length", "Tangent": "show_tangent", "External": "show_external",
        "Mid-ordinate": "show_mid_ordinate", "Mid Ordinate": "show_mid_ordinate",
        "Chord": "show_chord", "BC Station": "show_bc_station", "EC Station": "show_ec_station",
        "A Value": "show_a_value", "Theta": "show_theta",
        **{f"{code.upper()} Station": f"show_{code}_station" for code in ("ts", "sc", "cs", "st")},
    }
    if isinstance(style, SpiralLabelStyle):
        options["Delta"] = "show_theta"
    return frozenset(field for field, flag in options.items() if not getattr(style, flag, True))


def _anchors(alignment, major_interval, minor_interval, render_curves, render_spirals):
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

    show_points = alignment.label_set.get_style(kind.CURVE_POINT) is not None
    curve_style = alignment.label_set.curve_style if render_curves else None
    spiral_style = alignment.label_set.spiral_style if render_spirals else None
    curves = (
        {id(item["entity"]): item for item in CurveSpiralExtractor.extract_curves(alignment)}
        if curve_style is not None or show_points else {}
    )
    spirals = (
        {id(item["entity"]): item for item in CurveSpiralExtractor.extract_spirals(alignment)}
        if spiral_style is not None else {}
    )
    if show_points:
        for info in curves.values():
            yield kind.CURVE_POINT, info["start_station"], {"Geometry Point Text": "BC"}
            yield kind.CURVE_POINT, info["end_station"], {"Geometry Point Text": "EC"}

    for entity in entities:
        label_type = _SEGMENT_TYPES.get(entity.entity_type)
        style = alignment.label_set.get_style(label_type) if label_type is not None else None
        if style is None:
            continue
        station = (entity.start_station + entity.end_station) / 2
        fields = {"Distance": f"{entity.length:.2f}", "Length": f"{entity.length:.2f}"}
        if label_type is kind.CURVE:
            if not render_curves or id(entity) not in curves:
                continue
            fields.update(_geometry_fields(alignment, curves[id(entity)], style, label_type))
        elif label_type is kind.SPIRAL:
            if not render_spirals or id(entity) not in spirals:
                continue
            fields.update(_geometry_fields(alignment, spirals[id(entity)], style, label_type))
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


def _component_primitives(component, point, azimuth, values, hidden_fields=frozenset()):
    origin = Point2d(point.x + component.offset_x, point.y + component.offset_y)
    style = Style(color=component.text_color, layer=component.layer)
    kind = component.component_type
    if kind is AlignmentLabelComponentType.TEXT:
        def evaluate(match):
            key = match[1].split("(", 1)[0]
            return values.get(key, "???")

        contents = component.contents
        if hidden_fields:
            contents = "\n".join(
                line for line in contents.replace("\\P", "\n").splitlines()
                if not any(field.split("(", 1)[0] in hidden_fields for field in _FIELD.findall(line))
            )
        text = _FIELD.sub(evaluate, contents)
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
        fg_profile: Profile | None = None,
        major_interval: float | None = None, minor_interval: float | None = None,
        render_equations: bool = True,
        render_curves: bool = True, render_spirals: bool = True,
        station_offset_labels: Sequence[StationOffsetLabel] | None = None,
        reference_alignments: Mapping[str, Alignment] | None = None,
        reference_points: Mapping[str, Point2d] | None = None,
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
        for label_type, station, fields in _anchors(
            alignment, major_interval, minor_interval, render_curves, render_spirals,
        ):
            point = alignment.point_at(station)
            azimuth = alignment.tangent_at(station)
            fields.update({
                "Station Value": f"{alignment.raw_to_display_station(station):.2f}",
                "Raw Station": f"{station:.2f}", "Northing": f"{point.y:.3f}",
                "Easting": f"{point.x:.3f}", "Design Speed": f"{alignment.design_speed:g}",
                "Bearing": f"{math.degrees(azimuth) % 360:.2f}°",
            })
            style = alignment.label_set.get_style(label_type)
            hidden = _hidden_fields(style) if isinstance(style, (CurveLabelStyle, SpiralLabelStyle)) else frozenset()
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
                primitives.extend(_component_primitives(component, point, azimuth, values, hidden))

        equation_style = alignment.label_set.equation_style
        if render_equations and equation_style is not None:
            primitives.extend(_equation_primitives(alignment, equation_style))

        for primitive in primitives:
            style = primitive.style
            layers.setdefault(style.layer, Layer(style.layer, color=style.color))
        for layer in layers.values():
            scene = scene.add_layer(layer)
        if primitives:
            scene = scene.add_all(primitives)
        geometry_style = alignment.label_set.profile_geometry_style
        if geometry_style is not None:
            design = fg_profile if fg_profile is not None else alignment.fg_profile or profile
            if design is not None and design.is_valid:
                from myalignment.alignment.profile_geometry_label_extractor import ProfileGeometryLabelExtractor
                from myalignment.render.profile_geometry_label_renderer import ProfileGeometryLabelRenderer

                kinds = alignment.label_set.profile_geometry_labeled_points
                if kinds is not None:
                    geometry_style = replace(geometry_style, labeled_points=kinds)
                labels = ProfileGeometryLabelExtractor.extract(design, geometry_style.labeled_points)
                scene = ProfileGeometryLabelRenderer.render(
                    scene, alignment, labels, geometry_style,
                    reference_profile=profile, reference_alignment=reference_alignment, surface=surface,
                )

        offsets = alignment.station_offset_labels if station_offset_labels is None else station_offset_labels
        if offsets:
            from myalignment.render.station_offset_label_renderer import StationOffsetLabelRenderer

            scene = StationOffsetLabelRenderer.render_multiple(
                scene, offsets, alignment, reference_alignment,
                reference_alignments=reference_alignments, reference_points=reference_points,
            )
        return scene
