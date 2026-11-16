# alignment/alignment_side.py
from enum import Enum


class AlignmentSide(Enum):
    """C3D AlignmentSide 호환."""
    LEFT = 0
    RIGHT = 1
    BOTH = 2