from __future__ import annotations

from collections.abc import Sequence
import re
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.profile.label_component import LabelComponentType
from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene
from myalignment.render.viewport import Viewport, ViewportType

if TYPE_CHECKING:
    from myalignment.profile.depth_label import DepthLabel
    from myalignment.profile.profile import Profile


_FIELD = re.compile(r"<\[([^\[\]]+)\]>")


class DepthLabelRenderer:
    """종단 뷰에 두 측점의 연결선, 끝점 마커와 텍스트를 추가한다."""

    LAYER = "C-PROF-DEPTH"

    @classmethod
    def render(
        cls,
        scene: Scene,
        label: DepthLabel,
        profiles: Sequence[Profile],
        vertical_exaggeration: float = 10.0,
    ) -> Scene:
        """단일 레이블을 추가한다. 두 표고를 조회할 수 없으면 기존 Scene을 반환한다."""
        return cls.render_multiple(scene, (label,), profiles, vertical_exaggeration)

    @classmethod
    def render_multiple(
        cls,
        scene: Scene,
        labels: Sequence[DepthLabel],
        profiles: Sequence[Profile],
        vertical_exaggeration: float = 10.0,
    ) -> Scene:
        """같은 수직 과장을 사용하여 여러 레이블을 추가한다."""
        viewport = Viewport(ViewportType.PROFILE, vertical_exaggeration)
        primitives = [
            primitive
            for label in labels
            for primitive in cls._primitives(label, profiles, viewport)
        ]
        if not primitives:
            return scene
        return scene.add_layer(Layer(cls.LAYER, color=7)).add_all(primitives)

    @classmethod
    def _primitives(cls, label: DepthLabel, profiles: Sequence[Profile], viewport: Viewport):
        values = label.summary(profiles)
        if not values:
            return

        start = viewport.project(label.start_station, values["start_elevation"])
        end = viewport.project(label.end_station, values["end_elevation"])
        anchor_x = start.x / 2 + end.x / 2
        anchor_y = start.y / 2 + end.y / 2
        style = label.label_style
        if style.show_arrow:
            connector = Style(color=6, layer=cls.LAYER, lineweight=0.3)
            yield Primitive.line(start, end, connector)
            for point in (start, end):
                yield Primitive.line(Point2d(point.x - 1, point.y), Point2d(point.x + 1, point.y), connector)

        fields = label._format_fields(values)
        shown = {
            "Start Station": style.show_stations,
            "End Station": style.show_stations,
            "Elevation Difference": style.show_elevation_diff,
            "Grade": style.show_grade,
            "Distance": style.show_distance,
        }
        scale = viewport.vertical_exaggeration
        for component in style.components:
            if not component.visible or component.component_type is not LabelComponentType.TEXT:
                continue

            height = component.text_height * scale
            x = anchor_x + component.offset_x
            y = anchor_y + component.offset_y * scale
            text_style = Style(color=component.text_color, layer=cls.LAYER)
            for row in component.contents.replace("\\P", "\n").splitlines():
                if not row or not all(shown.get(field, True) for field in _FIELD.findall(row)):
                    continue
                text = _FIELD.sub(lambda match: fields.get(match[1], match[0]), row)
                yield Primitive.text(Point2d(x, y), text, height, component.rotation, text_style)
                y -= height
