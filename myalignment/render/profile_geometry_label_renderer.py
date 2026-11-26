from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
import math
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.alignment.label_component import AlignmentLabelComponentType, ReferenceObjectType
from myalignment.alignment.profile_geometry_label_style import ProfileGeometryLabelStyle
from myalignment.render.alignment_label_renderer import _component_primitives, _reference_values
from myalignment.render.primitives import Primitive, PrimitiveType, Style
from myalignment.render.scene import Layer, Scene

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.alignment.profile_geometry_label import ProfileGeometryLabel
    from myalignment.profile.profile import Profile
    from myalignment.surface.tin_surface import TinSurface


class ProfileGeometryLabelRenderer:
    """종단 기하점의 측점을 평면 선형에 표식기와 텍스트로 표시한다."""

    LAYER = "C-ALIGN-PROF-GEOM"

    @staticmethod
    def render(
        scene: Scene, alignment: Alignment, labels: Iterable[ProfileGeometryLabel],
        style: ProfileGeometryLabelStyle | None = None, *,
        reference_profile: Profile | None = None, reference_alignment: Alignment | None = None,
        surface: TinSurface | None = None,
    ) -> Scene:
        """기하 측점에 배치하고 표시 측점은 방정식을 적용해 계산한다."""
        if not alignment.is_valid:
            return scene
        style = style or ProfileGeometryLabelStyle.standard()
        components = tuple(c for c in style.components if c.visible)
        allowed = set(style.labeled_points)
        targets = {
            ReferenceObjectType.PROFILE: reference_profile,
            ReferenceObjectType.ALIGNMENT: reference_alignment,
            ReferenceObjectType.SURFACE: surface,
        }
        marker = Style(color=style.marker_color, layer=style.marker_layer, lineweight=0.5)
        primitives = []
        counts = {}
        band = (
            max((c.offset_y for c in components), default=0) - min((c.offset_y for c in components), default=0)
            + max((c.text_height * max(1, len(c.contents.replace("\\P", "\n").splitlines())) for c in components),
                  default=0) + 1
        )
        for label in labels:
            station = label.station
            if label.point_type not in allowed or not alignment.start_station <= station <= alignment.end_station:
                continue
            point, azimuth = alignment.point_at(station), alignment.tangent_at(station)
            ux, uy = math.cos(azimuth), math.sin(azimuth)
            nx, ny = -uy, ux
            count = counts.get(station, 0)
            counts[station] = count + 1
            if style.show_marker and count == 0:
                size = style.marker_size
                primitives.extend((
                    Primitive.line(Point2d(point.x - nx * size, point.y - ny * size),
                                   Point2d(point.x + nx * size, point.y + ny * size), marker),
                    Primitive.circle(point, 0.8 * size, marker),
                ))
            fields = label.to_fields(alignment.raw_to_display_station(station))
            fields.update(Easting=f"{point.x:.3f}", Northing=f"{point.y:.3f}")
            references = {}
            for reference, target in targets.items():
                if target is not None:
                    references[reference] = _reference_values(reference, target, station, point)
            fields.update({f"Ref {key}": value for values in references.values() for key, value in values.items()})
            if "Ref Alignment Station" in fields:
                fields["Ref Station"] = fields["Ref Alignment Station"]
                fields["Ref Offset"] = fields["Ref Alignment Offset"]
            items = []
            for component in components:
                offset_y = component.offset_y + count * band
                origin = Point2d(point.x + component.offset_x * ux + offset_y * nx,
                                 point.y + component.offset_x * uy + offset_y * ny)
                values = fields
                if component.component_type is AlignmentLabelComponentType.TEXT:
                    values = {**fields, **references.get(component.reference_type, {})}
                items.extend(_component_primitives(
                    replace(component, offset_x=0, offset_y=0), origin, azimuth, values,
                ))
            if style.show_leader:
                anchors = [p.points[0] for p in items if p.type is PrimitiveType.TEXT]
                if anchors:
                    anchor = min(anchors, key=point.distance_to)
                    if anchor.distance_to(point) > style.marker_size:
                        primitives.append(Primitive.line(point, anchor, marker))
            primitives.extend(items)
        layers = {}
        for primitive in primitives:
            layer = primitive.style.layer
            layers.setdefault(layer, Layer(layer, color=primitive.style.color))
        for layer in layers.values():
            scene = scene.add_layer(layer)
        return scene.add_all(primitives) if primitives else scene
