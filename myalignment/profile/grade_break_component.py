from dataclasses import dataclass
from enum import Enum
import math


class GradeBreakComponentType(Enum):
    TEXT = "Text"
    LINE = "Line"
    TICK = "Tick"
    ARROW = "Arrow"


@dataclass(frozen=True, slots=True)
class GradeBreakLabelComponent:
    """구배 변경점 텍스트, 틱, 선과 방향 화살표."""

    component_type: GradeBreakComponentType = GradeBreakComponentType.TEXT
    contents: str = ""
    text_height: float = 1.8
    text_color: int = 7
    rotation: float = 0.0
    offset_x: float = 0.0
    offset_y: float = 2.0
    visible: bool = True
    layer: str = "C-PROF-GRADEBREAK"
    size: float = 1.0
    placement: str = "above"

    def __post_init__(self):
        if self.component_type is GradeBreakComponentType.TEXT and not self.contents:
            raise ValueError("TEXT 컴포넌트는 contents 필요")
        if self.placement not in ("above", "below"):
            raise ValueError("placement must be above or below")
        if not math.isfinite(self.text_height) or self.text_height <= 0:
            raise ValueError("text_height must be finite and positive")
        if not math.isfinite(self.size) or self.size < 0:
            raise ValueError("size must be finite and nonnegative")
        if not all(math.isfinite(value) for value in (self.rotation, self.offset_x, self.offset_y)):
            raise ValueError("rotation and offsets must be finite")
        if not isinstance(self.text_color, int) or not 0 <= self.text_color <= 256:
            raise ValueError("text_color must be an ACI integer from 0 to 256")
