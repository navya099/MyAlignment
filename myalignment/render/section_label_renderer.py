from __future__ import annotations

import math
import re

from cadgeom import Point2d

from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene
from myalignment.section.label_component import SectionLabelComponentType
from myalignment.section.label_set import SectionLabelSet
from myalignment.section.label_type import SectionLabelType
from myalignment.section.section_view_data import SectionViewData
from myalignment.section.section_view_style import SectionViewStyle, section_projection


_FIELD = re.compile(r"<\[([^\[\]]+)\]>")


def _anchors(data, label_type):
    kind = SectionLabelType
    station_field = {"Station": f"{data.station:.2f}"}
    if label_type in (kind.OFFSET_ELEVATION, kind.GRADE_BREAK):
        slopes = {}
        for link in data.links:
            left, right = sorted((link.start, link.end), key=lambda point: point.offset)
            if right.offset - left.offset > 1e-9:
                slopes.setdefault(left, (set(), set()))[1].add(round(link.slope, 9))
                slopes.setdefault(right, (set(), set()))[0].add(round(link.slope, 9))
        for point in data.points:
            incoming, outgoing = slopes.get(point, ((), ()))
            values = sorted(set(incoming) | set(outgoing))
            fields = {
                **station_field, "Offset": f"{point.offset:+.2f}", "Elevation": f"{point.elevation:.3f}",
                "Slope": " / ".join(f"{value:+.1f}%" for value in values) or "???",
            }
            if label_type is kind.GRADE_BREAK:
                if len(incoming) != 1 or len(outgoing) != 1:
                    continue
                before, after = next(iter(incoming)), next(iter(outgoing))
                if math.isclose(before, after, rel_tol=0, abs_tol=1e-8):
                    continue
                fields.update({"Slope In": f"{before:+.1f}%", "Slope Out": f"{after:+.1f}%"})
            yield point.offset, point.elevation, fields
    elif label_type in (kind.SLOPE, kind.DISTANCE):
        for link in data.links:
            a, b = link.start, link.end
            horizontal = b.offset - a.offset
            if label_type is kind.SLOPE and abs(horizontal) <= 1e-9:
                continue
            x, z = (a.offset + b.offset) / 2, (a.elevation + b.elevation) / 2
            yield x, z, {
                **station_field, "Offset": f"{x:+.2f}", "Elevation": f"{z:.3f}",
                "Slope": f"{link.slope:+.1f}%" if abs(horizontal) > 1e-9 else "???",
                "Distance": f"{math.hypot(horizontal, b.elevation - a.elevation):.2f}",
                "Code": link.code,
            }
    elif label_type is kind.SECTION_SEGMENT and data.points:
        lo, hi = min(p.offset for p in data.points), max(p.offset for p in data.points)
        length = sum(math.hypot(link.end.offset - link.start.offset, link.end.elevation - link.start.elevation)
                     for link in data.links)
        yield (lo + hi) / 2, max(p.elevation for p in data.points), {
            **station_field, "Width": f"{hi - lo:.2f}", "Distance": f"{length:.2f}",
            "Link Count": str(len(data.links)),
        }


def _components(label_style, anchor, fields, exaggeration):
    scale = exaggeration if label_style.obey_vertical_exaggeration else 1.0
    for component in label_style.components:
        if not component.visible:
            continue
        dx, dy = component.offset_x, component.offset_y
        if label_style.placement == "below":
            dy = -dy
        elif label_style.placement == "left":
            dx, dy = -dy, dx
        elif label_style.placement == "right":
            dx, dy = dy, dx
        x, y = anchor.x + dx, anchor.y + dy * scale
        style = Style(color=component.text_color, layer=component.layer)
        if component.component_type is SectionLabelComponentType.TEXT:
            text = _FIELD.sub(lambda match: fields.get(match[1], "???"), component.contents)
            height = component.text_height * scale
            for index, line in enumerate(text.replace("\\P", "\n").splitlines()):
                if line:
                    yield Primitive.text(Point2d(x, y - index * height * 1.2), line,
                                         height, component.rotation, style)
        elif component.size:
            angle = component.rotation
            if component.component_type is SectionLabelComponentType.TICK:
                angle += math.pi / 2
            dx = component.size * math.cos(angle)
            dy = component.size * math.sin(angle) * scale
            yield Primitive.line(Point2d(x - dx, y - dy), Point2d(x + dx, y + dy), style)


class SectionLabelRenderer:
    """횡단점, 링크와 전체 단면에 유형별 레이블을 적용한다."""

    @classmethod
    def render(
        cls, scene: Scene, data: SectionViewData, view_style: SectionViewStyle,
        label_set: SectionLabelSet, min_elev: float | None = None, max_elev: float | None = None,
    ) -> Scene:
        if not label_set.styles or not data.points:
            return scene
        *_, plot = section_projection(data, view_style, min_elev, max_elev)
        return cls._render_projected(scene, data, view_style, label_set, plot)

    @staticmethod
    def _render_projected(scene, data, view_style, label_set, plot):
        primitives = []
        layers = {}
        for kind, style in label_set.styles.items():
            anchors = []
            for offset, elevation, fields in _anchors(data, kind):
                anchor = plot(offset, elevation)
                if any(math.hypot(anchor.x - p.x, anchor.y - p.y) < style.min_spacing for p in anchors):
                    continue
                items = list(_components(style, anchor, fields, view_style.vertical_exaggeration))
                if items:
                    anchors.append(anchor)
                    primitives.extend(items)
                    for item in items:
                        layers.setdefault(item.style.layer, Layer(item.style.layer, color=item.style.color))
        if not primitives:
            return scene
        for layer in layers.values():
            scene = scene.add_layer(layer)
        return scene.add_all(primitives)
