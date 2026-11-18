# surface/breakline_type.py
from enum import Enum


class BreaklineType(Enum):
    """C3D Breakline 유형."""
    STANDARD = "standard"              # 표준 (표고 보간)
    PROXIMITY = "proximity"            # 근접 (표고 무시)
    WALL = "wall"                      # 수직 벽
    NON_DESTRUCTIVE = "non_destructive"  # 비파괴