from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.profile.grade_break_component import GradeBreakComponentType
from myalignment.profile.grade_break_style import GradeBreakLabelStyle
from myalignment.profile.vertical_geometry_extractor import VerticalGeometryExtractor
from myalignment.profile.vertical_geometry_type import VerticalGeometryPointType
from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene
from myalignment.render.viewport import Viewport, ViewportType

if TYPE_CHECKING:
    from myalignment.profile.profile import Profile


_FIELD = re.compile(r"<\[([^\[\]]+)\]>")


def _arrows(x, y, point, size, exaggeration, style):
    for step, grade in ((-1, point.grade_in), (1, point.grade_out)):
        dx, dy = size, grade * exaggeration * size
        if step < 0:
            start, tip = Point2d(x - dx, y - dy), Point2d(x, y)
        else:
            start, tip = Point2d(x, y), Point2d(x + dx, y + dy)
        yield Primitive.line(start, tip, style)
        length = math.hypot(dx, dy)
        ux, uy = dx / length, dy / length
        head = length * .25
        for side in (-1, 1):
            yield Primitive.line(tip, Point2d(
                tip.x - head * ux - side * head * .5 * uy,
                tip.y - head * uy + side * head * .5 * ux,
            ), style)


class GradeBreakLabelRenderer:
    """실제 접선 구배 변경점과 종곡선의 PVI/VPC/VPT를 표시한다."""

    @classmethod
    def render(
        cls, scene: Scene, profile: Profile, style: GradeBreakLabelStyle | None = None,
        vertical_exaggeration: float = 10.0,
    ) -> Scene:
        style = style or GradeBreakLabelStyle.standard()
        viewport = Viewport(ViewportType.PROFILE, vertical_exaggeration)
        points = VerticalGeometryExtractor.extract(profile)
        kind = VerticalGeometryPointType
        primitives = []
        for point in points:
            if point.point_type is not kind.GRADE_BREAK and not (
                point.curve_length and point.point_type in (kind.PVI, kind.VPC, kind.VPT)
            ):
                continue
            primitives.extend(cls._label(viewport, point, style))
        if not primitives:
            return scene
        layers = {}
        for primitive in primitives:
            rendered_style = primitive.style
            layers.setdefault(rendered_style.layer, Layer(rendered_style.layer, color=rendered_style.color))
        for layer in layers.values():
            scene = scene.add_layer(layer)
        return scene.add_all(primitives)

    @staticmethod
    def _label(viewport, point, style):
        number_format = "+.2%" if style.use_sign else ".2%"
        fields = {"Point Type": point.label_text}
        for key, visible, value in (
            ("Station Value", style.show_station, f"{point.station:.2f}"),
            ("Elevation Value", style.show_elevation, f"{point.elevation:.3f}"),
            ("Grade In", style.show_grade_in, format(point.grade_in, number_format)),
            ("Grade Out", style.show_grade_out, format(point.grade_out, number_format)),
            ("Grade Change", style.show_grade_change, format(point.grade_change, number_format)),
        ):
            if visible:
                fields[key] = value
        if point.curve_length:
            fields["Curve Length"] = f"{point.curve_length:.2f}"
            if style.show_k_value:
                fields["K Value"] = f"{point.curve_length / (100 * point.grade_change):.2f}"

        scale = viewport.vertical_exaggeration
        anchor = viewport.project(point.station, point.elevation)
        for component in style.components:
            if not component.visible:
                continue
            x = anchor.x + component.offset_x
            direction = -1 if component.placement == "below" else 1
            y = anchor.y + direction * component.offset_y * scale
            appearance = Style(color=component.text_color, layer=component.layer)
            kind = component.component_type
            if kind is GradeBreakComponentType.TEXT:
                if any(key not in fields for key in _FIELD.findall(component.contents)):
                    continue
                text = _FIELD.sub(lambda match: fields[match[1]], component.contents)
                height = component.text_height * scale
                for index, row in enumerate(text.replace("\\P", "\n").splitlines()):
                    if row:
                        yield Primitive.text(Point2d(x, y - index * height), row, height, component.rotation, appearance)
            elif kind is GradeBreakComponentType.ARROW:
                if style.show_arrows and component.size:
                    yield from _arrows(x, y, point, component.size * scale, scale, appearance)
            elif component.size:
                size = component.size * scale
                dx, dy = size * math.cos(component.rotation), size * math.sin(component.rotation)
                yield Primitive.line(Point2d(x - dx, y - dy), Point2d(x + dx, y + dy), appearance)
