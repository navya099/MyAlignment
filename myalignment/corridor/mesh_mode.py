from enum import Enum


class MeshMode(Enum):
    """코리더의 횡단 샘플을 면으로 구성하는 방식."""

    LINK_BASED = "LinkBased"
    TRIANGULATED = "Triangulated"
    QUAD_STRIP = "QuadStrip"
