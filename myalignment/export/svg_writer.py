from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
import math
from pathlib import Path
import re
import unicodedata
from xml.etree import ElementTree as ET

from myalignment.export.aci_color_map import AciColorMap
from myalignment.export.dxf_writer import _LINETYPE_PATTERNS, _linetype
from myalignment.export.svg_style import SvgStyle
from myalignment.render.primitives import Primitive, PrimitiveType
from myalignment.render.scene import Layer, Scene


_SVG = "http://www.w3.org/2000/svg"
_XML_INVALID = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")
_CAP_HEIGHT_MARGIN = 1.25


def _number(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError("SVG coordinates and dimensions must be finite")
    return "0" if value == 0 else format(value, ".15g")


def _dark_background(color):
    color = color.strip().lower()
    if color in ("black", "navy", "darkblue"):
        return True
    if re.fullmatch(r"#[\da-f]{3}", color):
        color = "#" + "".join(char * 2 for char in color[1:])
    if re.fullmatch(r"#[\da-f]{6}", color):
        r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b < 128
    return False


def _arc_angles(primitive):
    start, end = primitive.start_angle, primitive.end_angle
    if not (math.isfinite(start) and math.isfinite(end)):
        raise ValueError("arc angles must be finite")
    sweep = (end % 360 - start % 360) % 360
    return start % 360, 360.0 if sweep == 0 and start != end else sweep


def _arc_point(center, radius, degrees):
    angle = math.radians(degrees % 360)
    return center.x + radius * math.cos(angle), center.y + radius * math.sin(angle)


def _text_lines(text):
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _points_for_fit(primitive: Primitive, style: SvgStyle):
    kind = primitive.type
    if kind is PrimitiveType.TEXT:
        x, y = primitive.points[0].x, primitive.points[0].y
        height = primitive.text_height * style.font_size_scale
        if not math.isfinite(height) or height <= 0 or not math.isfinite(primitive.rotation):
            raise ValueError("SVG text requires positive height and finite rotation")
        lines = _text_lines(primitive.contents)
        # Font metrics are estimated in drawing units, including wide glyphs and overhang.
        width = max(sum(
            1.25 if unicodedata.east_asian_width(char) in ("W", "F") else 1.1
            for char in line
        ) for line in lines) * height
        cos_angle, sin_angle = math.cos(primitive.rotation), math.sin(primitive.rotation)
        for dx in (-0.2 * height, width + 0.2 * height):
            for dy in (-(len(lines) - 1) * 1.25 * height - 0.35 * height, _CAP_HEIGHT_MARGIN * height):
                yield x + dx * cos_angle - dy * sin_angle, y + dx * sin_angle + dy * cos_angle
    elif kind in (PrimitiveType.ARC, PrimitiveType.CIRCLE):
        radius = primitive.radius
        if not math.isfinite(radius) or radius <= 0:
            raise ValueError("SVG radius must be finite and positive")
        if kind is PrimitiveType.CIRCLE:
            angles = (0, 90, 180, 270)
        else:
            start, sweep = _arc_angles(primitive)
            angles = (start, start + sweep, *(angle for angle in (0, 90, 180, 270)
                                             if (angle - start) % 360 <= sweep))
        for angle in angles:
            yield _arc_point(primitive.points[0], radius, angle)
    else:
        yield from ((point.x, point.y) for point in primitive.points)


@dataclass(frozen=True, slots=True)
class _Viewport:
    world_x: float
    world_y: float
    page_x: float
    page_y: float
    scale: float

    def xy(self, x: float, y: float) -> tuple[float, float]:
        return self.page_x + (x - self.world_x) * self.scale, self.page_y - (y - self.world_y) * self.scale

    def point(self, point) -> tuple[str, str]:
        return tuple(map(_number, self.xy(point.x, point.y)))


def _stroke_width(primitive, layer, style):
    width = primitive.style.lineweight or layer.lineweight or 0.25
    if not math.isfinite(width) or width < 0:
        raise ValueError("SVG lineweight must be finite and nonnegative")
    return width * style.stroke_width_scale


def _viewport(items: Iterable[tuple[Primitive, Layer]], style: SvgStyle) -> _Viewport:
    page_width, page_height, margin = style.page_width_mm, style.page_height_mm, style.margin_mm
    if not style.auto_fit_viewport:
        return _Viewport(0, 0, margin, page_height - margin, 1)
    left = bottom = math.inf
    right = top = -math.inf
    stroke = 0.0
    for primitive, layer in items:
        if not layer.visible:
            continue
        for x, y in _points_for_fit(primitive, style):
            if not (math.isfinite(x) and math.isfinite(y)):
                raise ValueError("SVG coordinates must be finite")
            left, right, bottom, top = min(left, x), max(right, x), min(bottom, y), max(top, y)
        if primitive.type is not PrimitiveType.TEXT:
            stroke = max(stroke, _stroke_width(primitive, layer, style))
    if left == math.inf:
        return _Viewport(0, 0, page_width / 2, page_height / 2, 1)
    available_x = page_width - 2 * margin - stroke
    available_y = page_height - 2 * margin - stroke
    if min(available_x, available_y) <= 0:
        raise ValueError("stroke width exceeds the available drawing area")
    width, height = right - left, top - bottom
    factors = [available / span for available, span in ((available_x, width), (available_y, height)) if span > 0]
    return _Viewport(left + width / 2, bottom + height / 2, page_width / 2, page_height / 2,
                     min(factors, default=1))


def _validate_shape(primitive):
    count = len(primitive.points)
    if primitive.type is PrimitiveType.POLYLINE:
        if count < 2:
            raise ValueError("SVG polyline requires at least two points")
    elif count != (2 if primitive.type is PrimitiveType.LINE else 1):
        raise ValueError(f"Invalid point count for {primitive.type.value}")


class SvgWriter:
    """2D Scene을 페이지 단위, 레이어 및 스타일을 갖춘 SVG로 작성한다."""

    def __init__(self, scene: Scene, style: SvgStyle | None = None):
        self.scene = scene
        self.style = style or SvgStyle()

    def write(self, path: str | Path) -> None:
        Path(path).write_text(self.to_string(), encoding="utf-8")

    def to_string(self) -> str:
        """독립적으로 열 수 있는 SVG 문서를 반환한다."""
        style = self.style
        layers = {layer.name.casefold(): layer for layer in self.scene.layers}
        grouped = defaultdict(list)
        for primitive in self.scene.primitives:
            _validate_shape(primitive)
            name = primitive.style.layer or "0"
            key = name.casefold()
            layers.setdefault(key, Layer(name))
            grouped[key].append(primitive)
        viewport = _viewport(((p, layers[key]) for key, group in grouped.items() for p in group), style)
        width, height = _number(style.page_width_mm), _number(style.page_height_mm)
        svg = ET.Element("svg", {
            "xmlns": _SVG, "viewBox": f"0 0 {width} {height}",
            "width": f"{width}mm", "height": f"{height}mm", "preserveAspectRatio": "xMidYMid meet",
        })
        ET.SubElement(svg, "rect", {"width": width, "height": height, "fill": style.background_color})
        used_ids = set()
        dark = _dark_background(style.background_color)
        for key, layer in layers.items():
            if key not in grouped:
                continue
            stem = "layer-" + re.sub(r"[^\w.-]", "-", layer.name)
            layer_id = stem
            index = 2
            while layer_id in used_ids:
                layer_id = f"{stem}-{index}"
                index += 1
            used_ids.add(layer_id)
            group = ET.SubElement(svg, "g", {"id": layer_id, "data-layer": layer.name})
            if not layer.visible:
                group.set("display", "none")
            for primitive in grouped[key]:
                self._add_primitive(group, primitive, layer, viewport, dark)
        document = ET.tostring(svg, encoding="unicode", xml_declaration=True)
        if _XML_INVALID.search(document):
            raise ValueError("SVG contains invalid XML characters")
        return document + "\n"

    def _add_primitive(self, group, primitive, layer, viewport, dark):
        style, kind, points = self.style, primitive.type, primitive.points
        aci = primitive.style.color
        color = AciColorMap.to_css(layer.color if aci == 256 else aci, dark) if style.use_aci_colors else (
            "#FFFFFF" if dark else "#000000"
        )
        if kind is PrimitiveType.TEXT:
            self._add_text(group, primitive, viewport, color)
            return
        attrs = {
            "stroke": color, "stroke-width": _number(_stroke_width(primitive, layer, style)),
            "fill": "none", "stroke-linecap": "round", "stroke-linejoin": "round",
        }
        linetype = _linetype(primitive.style.linetype)
        if linetype in ("BYLAYER", "BYBLOCK"):
            linetype = _linetype(layer.linetype)
        pattern = _LINETYPE_PATTERNS.get(linetype)
        if pattern:
            attrs["stroke-dasharray"] = " ".join(_number(abs(value) * viewport.scale) for value in pattern)
        if kind is PrimitiveType.LINE:
            x1, y1 = viewport.point(points[0])
            x2, y2 = viewport.point(points[1])
            ET.SubElement(group, "line", dict(attrs, x1=x1, y1=y1, x2=x2, y2=y2))
        elif kind is PrimitiveType.POLYLINE:
            closed = primitive.closed or (len(points) > 2 and points[0] == points[-1])
            vertices = points[:-1] if closed and points[0] == points[-1] and len(points) > 2 else points
            coords = " ".join(",".join(viewport.point(p)) for p in vertices)
            ET.SubElement(group, "polygon" if closed else "polyline", dict(attrs, points=coords))
        else:
            if not math.isfinite(primitive.radius) or primitive.radius <= 0:
                raise ValueError("SVG radius must be finite and positive")
            radius = _number(primitive.radius * viewport.scale)
            if kind is PrimitiveType.CIRCLE:
                x, y = viewport.point(points[0])
                ET.SubElement(group, "circle", dict(attrs, cx=x, cy=y, r=radius))
            elif kind is PrimitiveType.ARC:
                start, sweep = _arc_angles(primitive)
                if sweep > 0:
                    def xy(angle):
                        return " ".join(map(_number, viewport.xy(*_arc_point(points[0], primitive.radius, angle))))

                    path = f"M {xy(start)}"
                    if sweep == 360:
                        path += f" A {radius} {radius} 0 0 0 {xy(start + 180)} A {radius} {radius} 0 0 0 {xy(start)}"
                    else:
                        path += f" A {radius} {radius} 0 {int(sweep > 180)} 0 {xy(start + sweep)}"
                    ET.SubElement(group, "path", dict(attrs, d=path))

    def _add_text(self, group, primitive, viewport, color):
        x, y = viewport.point(primitive.points[0])
        size = primitive.text_height * self.style.font_size_scale * viewport.scale
        if not math.isfinite(size) or size <= 0:
            raise ValueError("SVG text height must be finite and positive")
        attrs = {"x": x, "y": y, "fill": color, "font-family": self.style.font_family, "font-size": _number(size),
                 "xml:space": "preserve"}
        if primitive.rotation:
            attrs["transform"] = f"rotate({_number(-math.degrees(primitive.rotation))} {x} {y})"
        text = ET.SubElement(group, "text", attrs)
        lines = _text_lines(primitive.contents)
        if len(lines) == 1:
            text.text = lines[0]
        else:
            for index, line in enumerate(lines):
                ET.SubElement(text, "tspan", {"x": x, "dy": "0" if index == 0 else "1.25em"}).text = line
