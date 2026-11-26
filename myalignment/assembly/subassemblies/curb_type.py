from enum import Enum


class CurbType(Enum):
    """연석 전면 형상의 기본 유형."""

    VERTICAL = "Vertical"
    SLOPED = "Sloped"
    MOUNTABLE = "Mountable"
    BARRIER = "Barrier"
