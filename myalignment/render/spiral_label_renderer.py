from __future__ import annotations

from typing import TYPE_CHECKING

from myalignment.alignment.label_set import AlignmentLabelSet
from myalignment.alignment.spiral_label_style import SpiralLabelStyle
from myalignment.render.alignment_label_renderer import AlignmentLabelRenderer
from myalignment.render.scene import Scene

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment


class SpiralLabelRenderer:
    """기존 장면에 완화곡선 중앙의 제원 레이블만 추가한다."""

    @classmethod
    def render(cls, scene: Scene, alignment: Alignment, style: SpiralLabelStyle | None = None) -> Scene:
        """스타일을 생략하면 표준 완화곡선 제원을 표시한다."""
        style = SpiralLabelStyle.standard() if style is None else style
        labeled = alignment.with_label_set(AlignmentLabelSet().with_style(style.label_type, style))
        return AlignmentLabelRenderer.render(scene, labeled)
