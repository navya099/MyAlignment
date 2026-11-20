from dataclasses import dataclass
from enum import Enum


class ViewType(Enum):
    PLAN = "Plan"
    MODEL = "Model"
    PROFILE = "Profile"


class AlignmentComponent(Enum):
    LINE = "Line"
    CURVE = "Curve"
    SPIRAL = "Spiral"
    ARROW = "Arrow"
    MARKER = "Marker"


@dataclass(frozen=True, slots=True)
class DisplayRule:
    """선형 구성요소의 뷰별 표시 규칙."""

    component: AlignmentComponent
    view: ViewType
    visible: bool = True
    color: int = 256
    linetype: str = "ByLayer"
    lineweight: float = 0.0

    def __post_init__(self):
        if not isinstance(self.color, int) or not 0 <= self.color <= 256:
            raise ValueError(f"ACI 색상은 0~256 사이의 정수여야 합니다: {self.color}")
