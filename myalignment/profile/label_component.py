from dataclasses import dataclass
import math

from myalignment.alignment.style.label_style import LabelComponentType


@dataclass(frozen=True, slots=True)
class ProfileLabelComponent:
    """종단 레이블의 텍스트 또는 도형 구성요소."""

    component_type: LabelComponentType = LabelComponentType.TEXT
    contents: str = ""
    text_height: float = 2.0
    text_color: int = 7
    rotation: float = 0.0
    offset_x: float = 0.0
    offset_y: float = 2.0
    visible: bool = True
    size: float = 1.0
    layer: str = "C-PROF-LABEL"

    def __post_init__(self):
        if self.component_type is LabelComponentType.TEXT and not self.contents:
            raise ValueError("TEXT 컴포넌트는 contents 필요")
        if not math.isfinite(self.text_height) or self.text_height <= 0:
            raise ValueError("text_height must be finite and positive")
        if not isinstance(self.text_color, int) or not 0 <= self.text_color <= 256:
            raise ValueError("text_color must be an ACI integer from 0 to 256")
        if not all(math.isfinite(value) for value in (self.rotation, self.offset_x, self.offset_y)):
            raise ValueError("rotation and offsets must be finite")
        if not math.isfinite(self.size) or self.size < 0:
            raise ValueError("size must be finite and nonnegative")
