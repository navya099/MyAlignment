from __future__ import annotations

import math
from typing import TYPE_CHECKING

from myalignment.profile.profiletype import ProfileType
from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene
from myalignment.render.viewport import Viewport, ViewportType

if TYPE_CHECKING:
    from myalignment.profile.profile import Profile


class ProfileRenderer:
    FG_LAYER = "C-PROF-FG"
    EG_LAYER = "C-PROF-EG"

    @classmethod
    def render(
        cls, profile: Profile, scene: Scene | None = None, sample_step: float = 5.0,
        vertical_exaggeration: float = 10.0,
    ) -> Scene:
        if not math.isfinite(sample_step) or sample_step <= 0:
            raise ValueError("sample_step must be finite and positive")
        viewport = Viewport(ViewportType.PROFILE, vertical_exaggeration)
        scene = Scene() if scene is None else scene
        if not profile.is_valid:
            return scene
        is_design = profile.profile_type is ProfileType.FG
        layer = Layer(cls.FG_LAYER if is_design else cls.EG_LAYER, color=1 if is_design else 3)
        points = []
        for entity in profile.entities.entities:
            count = max(1, math.ceil(entity.length / sample_step))
            for i in range(count):
                station = entity.start_station + entity.length * i / count
                points.append(viewport.project(station, entity.elevation_at(station)))
        points.append(viewport.project(profile.end_station, profile.elevation_at(profile.end_station)))
        style = Style(color=layer.color, layer=layer.name)
        return scene.add_layer(layer).add(Primitive.polyline(points, style=style))
