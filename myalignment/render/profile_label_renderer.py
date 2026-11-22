from __future__ import annotations

import math
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.profile.label_component import LabelComponentType
from myalignment.profile.label_type import ProfileLabelType
from myalignment.profile.profileentitytype import ProfileEntityType
from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene
from myalignment.render.viewport import Viewport, ViewportType

if TYPE_CHECKING:
    from myalignment.profile.label_style import ProfileLabelStyle
    from myalignment.profile.profile import Profile


def _anchors(profile: Profile):
    kind = ProfileLabelType
    previous = None
    for entity in profile.entities:
        grade_in, grade_out = entity.start_grade, entity.end_grade
        station = (entity.start_station + entity.end_station) / 2
        elevation = entity.elevation_at(station)
        fields = {
            "Length": f"{entity.length:.2f}",
            "Grade In": f"{grade_in:.2%}",
            "Grade Out": f"{grade_out:.2%}",
        }
        if entity.entity_type is ProfileEntityType.Tangent:
            yield kind.LINE, station, elevation, {**fields, "Grade": f"{grade_in:.2%}"}
            if previous is not None and previous.entity_type is ProfileEntityType.Tangent and not math.isclose(
                previous.end_grade, grade_in, rel_tol=0.0, abs_tol=1e-9
            ):
                junction = {"Grade In": f"{previous.end_grade:.2%}", "Grade Out": f"{grade_in:.2%}"}
                for label_type in (kind.GRADIENT_BREAK, kind.PVI):
                    yield label_type, entity.start_station, entity.start_elevation, junction
        elif entity.entity_type in (ProfileEntityType.ParabolaSymmetric, ProfileEntityType.ParabolaAsymmetric):
            fields.update({"Curve Length": f"{entity.length:.2f}", "K Value": f"{abs(entity.k_value) / 100:.2f}"})
            yield kind.CURVE, station, elevation, fields
            yield kind.PVI, entity.pvi_station, entity.pvi_elevation, fields

            extremum = entity.extremum_station()
            if extremum is not None:
                crest = grade_in > grade_out
                name = "High Point" if crest else "Low Point"
                elevation = entity.elevation_at(extremum)
                yield (kind.CREST_CURVE if crest else kind.SAG_CURVE), extremum, elevation, {
                    **fields, f"{name} Station": f"{extremum:.2f}", f"{name} Elevation": f"{elevation:.3f}",
                }
        previous = entity


class ProfileLabelRenderer:
    """종단 기하를 분석해 선택한 유형의 레이블을 Scene에 추가한다."""

    @classmethod
    def render(cls, scene: Scene, profile: Profile, vertical_exaggeration: float = 10.0) -> Scene:
        viewport = Viewport(ViewportType.PROFILE, vertical_exaggeration)
        last_station = {}
        primitives = []
        for kind, station, elevation, fields in sorted(_anchors(profile), key=lambda item: item[1]):
            style = profile.label_set.get_style(kind)
            if style is None or station - last_station.get(kind, -math.inf) < style.min_spacing:
                continue
            values = {**fields, "Station Value": f"{station:.2f}", "Elevation Value": f"{elevation:.3f}"}
            anchor = viewport.project(station, elevation)
            items = list(cls._components(style, anchor, values, vertical_exaggeration))
            if items:
                last_station[kind] = station
                primitives.extend(items)
        if not primitives:
            return scene
        layers = {}
        for primitive in primitives:
            style = primitive.style
            layers.setdefault(style.layer, Layer(style.layer, color=style.color))
        for layer in layers.values():
            scene = scene.add_layer(layer)
        return scene.add_all(primitives)

    @staticmethod
    def _components(style: ProfileLabelStyle, anchor: Point2d, fields: dict[str, str], exaggeration: float):
        scale = exaggeration if style.obey_vertical_exaggeration else 1.0
        for component in style.components:
            if not component.visible:
                continue
            dx, dy = component.offset_x, component.offset_y
            if style.placement == "below":
                dy = -dy
            elif style.placement == "left":
                dx, dy = -dy, dx
            elif style.placement == "right":
                dx, dy = dy, dx
            x, y = anchor.x + dx, anchor.y + dy * scale
            primitive_style = Style(color=component.text_color, layer=component.layer)

            if component.component_type is LabelComponentType.TEXT:
                text = component.contents
                for key, value in fields.items():
                    text = text.replace(f"<[{key}]>", value)
                height = component.text_height * scale
                for index, row in enumerate(text.replace("\\P", "\n").splitlines()):
                    if row:
                        yield Primitive.text(
                            Point2d(x, y - index * height), row, height, component.rotation, primitive_style
                        )
            elif component.component_type in (LabelComponentType.LINE, LabelComponentType.TICK):
                radius = component.size * scale
                half_x = radius * math.cos(component.rotation)
                half_y = radius * math.sin(component.rotation)
                yield Primitive.line(
                    Point2d(x - half_x, y - half_y), Point2d(x + half_x, y + half_y), primitive_style
                )
