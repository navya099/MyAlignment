from __future__ import annotations

from typing import TYPE_CHECKING

from myalignment.alignment.curve_label_style import CurveLabelStyle
from myalignment.alignment.label_set import AlignmentLabelSet
from myalignment.render.alignment_label_renderer import AlignmentLabelRenderer
from myalignment.render.scene import Scene

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment


class CurveLabelRenderer:
    """기존 장면에 원곡선 중앙의 제원 레이블만 추가한다."""

    @classmethod
    def render(cls, scene: Scene, alignment: Alignment, style: CurveLabelStyle | None = None) -> Scene:
        """스타일을 생략하면 표준 원곡선 제원을 표시한다."""
        style = CurveLabelStyle.standard() if style is None else style
        labeled = alignment.with_label_set(AlignmentLabelSet().with_style(style.label_type, style))
        return AlignmentLabelRenderer.render(scene, labeled)
