from enum import Enum


class AlignmentTableType(Enum):
    """선형 제원표에 포함할 기하 요소."""

    LINE = "Line"
    CURVE = "Curve"
    SPIRAL = "Spiral"
    SEGMENT = "Segment"
