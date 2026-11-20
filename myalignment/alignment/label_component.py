from dataclasses import dataclass
from enum import Enum
import math

from myalignment.alignment.style.label_style import LabelComponentType as AlignmentLabelComponentType


class ReferenceObjectType(Enum):
    NONE = "None"
    SURFACE = "Surface"
    PROFILE = "Profile"
    ALIGNMENT = "Alignment"


@dataclass(frozen=True, slots=True)
class AlignmentLabelComponent:
    """평면 레이블의 표시와 참조 필드 설정."""

    component_type: AlignmentLabelComponentType = AlignmentLabelComponentType.TEXT
    contents: str = ""
    text_height: float = 2.0
    text_color: int = 7
    rotation: float = 0.0
    offset_x: float = 0.0
    offset_y: float = 2.0
    visible: bool = True
    layer: str = "C-ALIGN-LABEL"
    reference_type: ReferenceObjectType = ReferenceObjectType.NONE
    reference_field: str = ""

    def __post_init__(self):
        if self.component_type is AlignmentLabelComponentType.TEXT and not self.contents:
            raise ValueError("TEXT 컴포넌트는 contents 필요")
        if not math.isfinite(self.text_height) or self.text_height <= 0:
            raise ValueError("text_height must be finite and positive")
        if not isinstance(self.text_color, int) or not 0 <= self.text_color <= 256:
            raise ValueError("text_color must be an ACI integer from 0 to 256")
        if not all(math.isfinite(value) for value in (self.rotation, self.offset_x, self.offset_y)):
            raise ValueError("rotation and offsets must be finite")
