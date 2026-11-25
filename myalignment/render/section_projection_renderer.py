from __future__ import annotations

from collections.abc import Sequence
import math
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene
from myalignment.section.projection_object_type import SectionProjectionObjectType as ObjectType
from myalignment.section.section_view_style import section_projection
from myalignment.structure.struturetype import StructureType

if TYPE_CHECKING:
    from myalignment.section.section_projection import SectionProjection
    from myalignment.section.section_view_data import SectionViewData
    from myalignment.section.section_view_style import SectionViewStyle


def _outline(projection, plot, style, tunnel):
    if projection.object_type is ObjectType.PIPE or tunnel:
        center_x = projection.offset_center
        center_z = (projection.bottom_elevation + projection.top_elevation) / 2
        angles = (i * math.tau / 48 for i in range(48))
        yield Primitive.polyline((
            plot(center_x + projection.offset_width / 2 * math.cos(angle),
                 center_z + projection.elevation_height / 2 * math.sin(angle))
            for angle in angles
        ), closed=True, style=style)
    elif projection.object_type is ObjectType.STRUCTURE:
        left, right = projection.left_offset, projection.right_offset
        bottom, top = projection.bottom_elevation, projection.top_elevation
        yield Primitive.polyline(
            (plot(left, bottom), plot(right, bottom), plot(right, top), plot(left, top)),
            closed=True, style=style,
        )
    else:
        points = projection.projected_points
        for a, b in projection.projected_links:
            yield Primitive.line(plot(points[a].offset, points[a].elevation),
                                 plot(points[b].offset, points[b].elevation), style)


def _markers(projection, plot, style, tunnel):
    kind = projection.object_type
    if kind is ObjectType.STRUCTURE and not tunnel:
        bottom = projection.bottom_elevation
        base = projection.pier_bottom_elevation
        if base is None:
            for offset in (projection.left_offset, projection.right_offset):
                anchor = plot(offset, bottom)
                yield Primitive.line(Point2d(anchor.x, anchor.y - 3), Point2d(anchor.x, anchor.y + 3), style)
        else:
            width = min(projection.style.pier_width, projection.offset_width / 2)
            for left in (projection.left_offset, projection.right_offset - width):
                right = left + width
                yield Primitive.polyline(
                    (plot(left, bottom), plot(left, base), plot(right, base), plot(right, bottom)),
                    style=style,
                )
        return

    center_z = (projection.bottom_elevation + projection.top_elevation) / 2
    coordinates = [(p.offset, p.elevation) for p in projection.projected_points]
    if not coordinates:
        coordinates = [(projection.offset_center, center_z)]
    for offset, elevation in coordinates:
        anchor = plot(offset, elevation)
        x, y = anchor.x, anchor.y
        if kind is ObjectType.ALIGNMENT:
            yield Primitive.line(Point2d(x, y - 3), Point2d(x, y + 3), style)
        else:
            yield Primitive.line(Point2d(x - 2, y), Point2d(x + 2, y), style)
            yield Primitive.line(Point2d(x, y - 2), Point2d(x, y + 2), style)


def _primitives(projection, plot, height, station):
    style = projection.style
    source = projection.original_object
    tunnel = (projection.object_type is ObjectType.STRUCTURE
              and getattr(source, "structure_type", None) is StructureType.TUNNEL)
    if style.show_outline:
        yield from _outline(projection, plot, Style(
            color=style.outline_color, lineweight=style.outline_lineweight, layer=style.layer,
        ), tunnel)
    if style.show_marker:
        yield from _markers(projection, plot, Style(
            color=style.marker_color, lineweight=style.marker_lineweight, layer=style.layer,
        ), tunnel)
    if style.show_label:
        offset = projection.offset_center
        elevation = (projection.bottom_elevation + projection.top_elevation) / 2
        anchor = plot(offset, projection.top_elevation)
        if projection.projected_points:
            first = projection.projected_points[0]
            offset, elevation = first.offset, first.elevation
            anchor = plot(offset, elevation)
        label = style.format_label(
            name=projection.name, offset=offset, elevation=elevation,
            start_sta=getattr(source, "start_station", station),
            end_sta=getattr(source, "end_station", station),
            pipe_diameter=projection.diameter,
        )
        rows = [line for line in label.replace("\\P", "\n").splitlines() if line]
        text_style = Style(color=style.label_color, layer=style.layer)
        for index, row in enumerate(rows):
            at = Point2d(anchor.x + height, anchor.y + (len(rows) - index) * height)
            yield Primitive.text(at, row, height, style=text_style)


class SectionProjectionRenderer:
    """횡단 뷰와 동일한 좌표 변환으로 투영 객체를 렌더링한다."""

    @classmethod
    def render(
        cls, scene: Scene, projections: Sequence[SectionProjection], data: SectionViewData,
        view_style: SectionViewStyle, min_elev: float | None = None, max_elev: float | None = None,
    ) -> Scene:
        """횡단 단면과 투영 객체를 포함하는 범위에서 투영 레이어를 추가한다."""
        *_, plot = section_projection(data, view_style, min_elev, max_elev, projections=projections)
        return cls._render_projected(scene, projections, plot, view_style.text_height, data.station)

    @staticmethod
    def _render_projected(scene, projections, plot, height, station):
        primitives = []
        for projection in projections:
            items = list(_primitives(projection, plot, height, station))
            if items:
                style = projection.style
                scene = scene.add_layer(Layer(style.layer, color=style.outline_color))
                primitives.extend(items)
        return scene.add_all(primitives) if primitives else scene
