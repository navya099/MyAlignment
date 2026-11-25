from enum import Enum


class SlopePatternType(Enum):
    """코리더 사면의 표시 패턴."""

    HATCH = "Hatch"
    GRID = "Grid"
    STEPS = "Steps"
    STAKES = "Stakes"
    BERMS = "Berms"
    NONE = "None"
