from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
import math
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.render.cant_diagram_renderer import CantDiagramRenderer
from myalignment.render.cant_diagram_style import CantDiagramStyle
from myalignment.render.label_box import LabelBox
from myalignment.render.primitives import PrimitiveType
from myalignment.render.profile_view_renderer import ProfileViewRenderer
from myalignment.render.scene import Scene

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.profile.profile import Profile
    from myalignment.profile.view_style import ProfileViewStyle


class CantDiagramComposer:
    """독립 다이어그램을 만들거나 종단 뷰 아래에 배치한다."""

    @classmethod
    def separate(cls, alignment: Alignment, style: CantDiagramStyle | None = None) -> Scene:
        return CantDiagramRenderer.render(Scene(), alignment, style)

    @classmethod
    def below_profile_view(
        cls, alignment: Alignment, profiles: Sequence[Profile], profile_view_style: ProfileViewStyle,
        diagram_style: CantDiagramStyle | None = None, offset_y: float = -200.0,
    ) -> Scene:
        """offset_y는 도면 Y 이동량이며, 뷰가 겹치면 더 아래로 이동한다."""
        if not math.isfinite(offset_y):
            raise ValueError("offset_y must be finite")
        scene = ProfileViewRenderer.render(profiles, alignment.name, profile_view_style, alignment=alignment)
        style = diagram_style or CantDiagramStyle()
        diagram = cls.separate(alignment, style)
        if not diagram.primitives:
            return scene
        if not scene.primitives:
            return diagram

        profile_bottom = min(_y_extent(p)[0] for p in scene.primitives if p.points)
        diagram_top = max(_y_extent(p)[1] for p in diagram.primitives if p.points)
        shift = min(offset_y, profile_bottom - diagram_top - style.text_height)
        for layer in diagram.layers:
            scene = scene.add_layer(layer)
        return scene.add_all(
            replace(p, points=tuple(Point2d(pt.x, pt.y + shift) for pt in p.points))
            for p in diagram.primitives
        )


def _y_extent(primitive):
    if primitive.type is PrimitiveType.TEXT:
        anchor = primitive.points[0]
        box = LabelBox.from_text(
            anchor.x, anchor.y, primitive.text, primitive.text_height, rotation=primitive.rotation,
        )
        return box.y_min, box.y_max
    return min(p.y for p in primitive.points), max(p.y for p in primitive.points)
