from __future__ import annotations

from dataclasses import replace
import math

from cadgeom import Point2d

from myalignment.render.primitives import Primitive, Style
from myalignment.render.section_label_renderer import SectionLabelRenderer
from myalignment.render.scene import Layer, Scene
from myalignment.render.stagger_config import StaggerConfig
from myalignment.render.staggered_renderer import StaggeredRenderer
from myalignment.section.label_set import SectionLabelSet
from myalignment.section.section_view_data import SectionViewData
from myalignment.section.section_view_style import SectionViewStyle, section_projection


def _ticks(low, high, interval):
    first = math.ceil(math.nextafter(low / interval, -math.inf))
    last = math.floor(math.nextafter(high / interval, math.inf))
    return (index * interval for index in range(first, last + 1))


class SectionViewRenderer:
    """횡거·표고 격자 위에 코리더 및 지표면 횡단을 그린다."""

    @classmethod
    def render(
        cls, scene: Scene, data: SectionViewData, style: SectionViewStyle | None = None,
        label_set: SectionLabelSet | None = None, *,
        stagger_config: StaggerConfig | None = None,
    ) -> Scene:
        if not data.points and not data.surface_points:
            return scene
        style = style or SectionViewStyle()
        lo, hi, bottom, top, plot = section_projection(data, style)

        grid = Style(color=style.grid_color, layer=style.layer, lineweight=.15)
        axis = Style(color=style.axis_color, layer=style.layer, lineweight=style.axis_lineweight)
        design = Style(color=style.section_line_color, layer=style.layer, lineweight=style.section_lineweight)
        surface = Style(color=style.surface_color, layer=style.layer, lineweight=style.surface_lineweight)
        text = Style(color=style.text_color, layer=style.layer)
        height = style.text_height
        primitives = []

        for offset in _ticks(lo, hi, style.grid_x_interval):
            start = plot(offset, bottom)
            primitives.append(Primitive.line(start, plot(offset, top), grid))
            if style.show_offset_labels:
                primitives.append(Primitive.text(Point2d(start.x, start.y - 2 * height), f"{offset:g}", height, style=text))
        for elevation in _ticks(bottom, top, style.grid_y_interval):
            start = plot(lo, elevation)
            primitives.append(Primitive.line(start, plot(hi, elevation), grid))
            if style.show_elevation_labels:
                primitives.append(Primitive.text(Point2d(max(0, start.x - 7 * height), start.y),
                                                 f"{elevation:g}", height, style=text))

        frame = [plot(lo, bottom), plot(hi, bottom), plot(hi, top), plot(lo, top)]
        primitives.append(Primitive.polyline(frame, closed=True, style=axis))
        primitives.append(Primitive.line(plot(0, bottom), plot(0, top), axis))

        def point(p):
            return plot(p.offset, p.elevation)

        primitives.extend(Primitive.line(point(data.surface_points[a]), point(data.surface_points[b]), surface)
                          for a, b in data.surface_links)
        for link in data.links:
            a, b = point(link.start), point(link.end)
            primitives.append(Primitive.line(a, b, design))
            if label_set is None and style.show_slope_labels and abs(link.end.offset - link.start.offset) > 1e-9:
                primitives.append(Primitive.text(
                    Point2d((a.x + b.x) / 2, (a.y + b.y) / 2 + height),
                    f"{link.slope:+.1f}%", height, style=text,
                ))

        for p in data.points:
            anchor = point(p)
            for direction in (-1, 1):
                primitives.append(Primitive.line(
                    Point2d(anchor.x - 1, anchor.y - direction),
                    Point2d(anchor.x + 1, anchor.y + direction), design,
                ))
            values = []
            if label_set is None and style.show_offset_labels:
                values.append(f"OFF {p.offset:.2f}")
            if label_set is None and style.show_elevation_labels:
                values.append(f"EL {p.elevation:.2f}")
            if values:
                primitives.append(Primitive.text(Point2d(anchor.x + 1, anchor.y + 1),
                                                 " | ".join(values), height, style=text))

        primitives.extend((
            Primitive.text(Point2d(style.margin_left, style.height - 2 * height),
                           f"Section View — STA {data.station:.2f}", height * 1.2, style=text),
            Primitive.text(Point2d(style.width / 2, max(0, style.margin_bottom - 5 * height)),
                           "Offset (m)", height, style=text),
            Primitive.text(Point2d(max(0, style.margin_left - 11 * height), style.height / 2),
                           "Elevation (m)", height, math.pi / 2, text),
        ))
        scene = scene.add_layer(Layer(style.layer, color=style.axis_color)).add_all(primitives)
        if label_set is not None:
            scene = SectionLabelRenderer._render_projected(scene, data, style, label_set, plot)
        scene = replace(scene, metadata={**scene.metadata, "section_station": data.station})
        return StaggeredRenderer.apply_stagger(scene, stagger_config) if stagger_config is not None else scene
