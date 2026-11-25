from __future__ import annotations

import math
from typing import TYPE_CHECKING

from myalignment.profile.profiletype import ProfileType
from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene
from myalignment.render.viewport import Viewport, ViewportType

if TYPE_CHECKING:
    from myalignment.profile.profile import Profile


def _entity_ranges(profile: Profile, station_range: tuple[float, float]):
    start, end = station_range
    for entity in profile.entities:
        left, right = max(start, entity.start_station), min(end, entity.end_station)
        if left < right:
            yield entity, left, right


class ProfileRenderer:
    FG_LAYER = "C-PROF-FG"
    EG_LAYER = "C-PROF-EG"

    @classmethod
    def render(
        cls, profile: Profile, scene: Scene | None = None, sample_step: float = 5.0,
        vertical_exaggeration: float = 10.0,
        *, station_range: tuple[float, float] | None = None,
    ) -> Scene:
        if not math.isfinite(sample_step) or sample_step <= 0:
            raise ValueError("sample_step must be finite and positive")
        viewport = Viewport(ViewportType.PROFILE, vertical_exaggeration)
        scene = Scene() if scene is None else scene
        if not profile.is_valid:
            return scene
        is_design = profile.profile_type is ProfileType.FG
        layer = Layer(cls.FG_LAYER if is_design else cls.EG_LAYER, color=1 if is_design else 3)
        ranges = tuple(_entity_ranges(profile, station_range or (profile.start_station, profile.end_station)))
        if not ranges:
            return scene
        points = []
        for entity, start, end in ranges:
            length = end - start
            count = max(1, math.ceil(length / sample_step))
            for i in range(count):
                station = start + length * i / count
                points.append(viewport.project(station, entity.elevation_at(station)))
        last, _, end = ranges[-1]
        points.append(viewport.project(end, last.elevation_at(end)))
        style = Style(color=layer.color, layer=layer.name)
        return scene.add_layer(layer).add(Primitive.polyline(points, style=style))
