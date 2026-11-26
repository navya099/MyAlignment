from enum import Enum


class HatchPattern(Enum):
    """종단 해치의 표시 패턴."""

    SOLID = "Solid"
    DIAGONAL = "Diagonal"
    CROSS = "Cross"
    HORIZONTAL = "Horizontal"
    VERTICAL = "Vertical"
    DOTS = "Dots"
