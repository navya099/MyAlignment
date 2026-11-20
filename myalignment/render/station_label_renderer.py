from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene
from myalignment.render.viewport import Viewport, ViewportType

if TYPE_CHECKING:
    from myalignment.profile.profile import Profile
    from myalignment.profile.station_label import StationElevationLabel


class StationLabelRenderer:
    """종단선 위에 측점·표고 레이블의 마커와 텍스트를 배치한다."""

    LAYER = "C-PROF-LABEL"

    @classmethod
    def render(
        cls,
        scene: Scene,
        label: StationElevationLabel,
        profiles: Sequence[Profile],
        vertical_exaggeration: float = 10.0,
    ) -> Scene:
        profile = label.primary_profile(profiles)
        if profile is None:
            return scene
        try:
            elevation = profile.elevation_at(label.station)
        except ValueError:
            return scene

        anchor = Viewport(ViewportType.PROFILE, vertical_exaggeration).project(label.station, elevation)
        label_style = label.label_style
        style = Style(color=label_style.text_color, layer=cls.LAYER)
        primitives = []
        if label_style.show_marker and label_style.marker_size > 0:
            size = label_style.marker_size * vertical_exaggeration
            for direction in (-1, 1):
                primitives.append(Primitive.line(
                    Point2d(anchor.x - size, anchor.y - direction * size),
                    Point2d(anchor.x + size, anchor.y + direction * size),
                    style,
                ))

        evaluated = label.evaluate(profiles)
        lines = [
            line for template in label_style.fields
            for line in evaluated[template].splitlines()
        ]
        height = label_style.text_height * vertical_exaggeration
        x = anchor.x + label_style.offset_x * vertical_exaggeration
        y = anchor.y + label_style.offset_y * vertical_exaggeration
        # DXF R12 TEXT에는 줄바꿈이 없으므로 행마다 도형을 생성한다.
        for index, line in enumerate(lines):
            if line:
                primitives.append(Primitive.text(Point2d(x, y - index * height), line, height, style=style))

        if not primitives:
            return scene
        return scene.add_layer(Layer(cls.LAYER, color=style.color)).add_all(primitives)
