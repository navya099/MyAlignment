from __future__ import annotations

from dataclasses import replace
import math
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.profile.cant_band_extractor import CantBandSegmentExtractor
from myalignment.render.cant_diagram_style import CantDiagramStyle
from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene
from myalignment.superelevation.critical_station import TransitionRegionType

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment


class CantDiagramRenderer:
    """측점과 캔트 크기를 독립 도면 좌표에 그린다."""

    @classmethod
    def render(cls, scene: Scene, alignment: Alignment, style: CantDiagramStyle | None = None) -> Scene:
        style = style or CantDiagramStyle()
        curves = getattr(alignment, "cant_curves", ())
        segments = CantBandSegmentExtractor.extract(curves)
        if not segments:
            return scene
        gauge = alignment.gauge
        if style.unit == "%" and (not math.isfinite(gauge) or gauge <= 0):
            raise ValueError("gauge must be finite and positive for percent cant")

        start = segments[0].start_station
        end = max(segment.end_station for segment in segments)
        peak = max(max(segment.start_cant, segment.end_cant) for segment in segments)
        ceiling = (peak or 100.0) * 1.1

        def x(station):
            return style.station_to_x(station, start, end)

        def y(cant):
            return style.cant_to_y(cant, ceiling)

        left, right = x(start), x(end)
        bottom, top = y(0), y(ceiling)
        grid = Style(color=style.grid_color, layer=style.layer, lineweight=0.15)
        axis = Style(color=style.axis_color, layer=style.layer, lineweight=style.axis_lineweight)
        text = Style(color=style.text_color, layer=style.layer)
        marker = Style(color=style.cant_line_color, layer=style.layer, lineweight=0.2)
        guide = replace(marker, linetype="DASHED")
        height = style.text_height
        primitives = []
        first_tick = math.ceil(math.nextafter(start / style.grid_x_interval, -math.inf))
        last_tick = math.floor(math.nextafter(end / style.grid_x_interval, math.inf))
        for index in range(first_tick, last_tick + 1):
            station = min(end, max(start, index * style.grid_x_interval))
            pos = x(station)
            primitives.append(Primitive.line(Point2d(pos, bottom), Point2d(pos, top), grid))
            primitives.append(Primitive.text(Point2d(pos, bottom - 5 * height),
                                             f"{station:g}", height * .8, style=text))
        for index in range(math.floor(ceiling / style.grid_y_interval) + 1):
            cant = index * style.grid_y_interval
            pos = y(cant)
            label = f"{cant:g} mm" if style.unit == "mm" else f"{cant / (10 * gauge):.2f}%"
            primitives.append(Primitive.line(Point2d(left, pos), Point2d(right, pos), grid))
            primitives.append(Primitive.text(Point2d(max(0, left - 7 * height), pos),
                                             label, height * .8, style=text))

        primitives.extend((
            Primitive.line(Point2d(left, bottom), Point2d(right, bottom), axis),
            Primitive.line(Point2d(left, bottom), Point2d(left, top), axis),
        ))
        region = TransitionRegionType
        region_styles = {
            region.NORMAL: (style.normal_color, "N"),
            region.TRANSITION_IN: (style.transition_color, "TI"),
            region.TRANSITION_OUT: (style.transition_color, "TO"),
            region.FULL_SUPERELEVATION: (style.full_cant_color, "FC"),
        }
        for segment in segments:
            color, symbol = region_styles[segment.region_type]
            a = Point2d(x(segment.start_station), y(segment.start_cant))
            b = Point2d(x(segment.end_station), y(segment.end_cant))
            line_style = Style(color=color, layer=style.layer, lineweight=style.cant_lineweight)
            primitives.append(Primitive.line(a, b, line_style))
            primitives.append(Primitive.text(
                Point2d((a.x + b.x) / 2, (a.y + b.y) / 2 + height),
                symbol, height * .8, style=text,
            ))

        marks = {
            (point.station, abs(point.cant_value) * 1000)
            for curve in curves for point in curve.critical_stations
            if start <= point.station <= end
            and (curve.end_station <= curve.start_station or curve.start_station <= point.station <= curve.end_station)
        }
        for station, cant in sorted(marks):
            px, py = x(station), y(cant)
            radius = height / 2
            if py > bottom:
                primitives.append(Primitive.line(Point2d(px, bottom), Point2d(px, py), guide))
            primitives.extend((
                Primitive.line(Point2d(px - radius, py), Point2d(px + radius, py), marker),
                Primitive.line(Point2d(px, py - radius), Point2d(px, py + radius), marker),
                Primitive.text(Point2d(px, bottom - 2 * height), f"{station:g}", height * .8, style=text),
            ))
        primitives.extend((
            Primitive.text(Point2d(max(0, left - 12 * height), (bottom + top) / 2),
                           f"Cant ({style.unit})", height, math.pi / 2, text),
            Primitive.text(Point2d((left + right) / 2, bottom - 10 * height), "Station (m)", height, style=text),
            Primitive.text(Point2d(left, style.height - 3 * height),
                           f"Cant Diagram — {alignment.name}", height * 1.2, style=text),
        ))
        return scene.add_layer(Layer(style.layer, color=style.axis_color)).add_all(primitives)
