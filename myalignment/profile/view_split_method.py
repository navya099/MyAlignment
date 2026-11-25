from enum import Enum


class ProfileViewSplitMethod(Enum):
    """종단 뷰의 원시 측점 범위를 나누는 방식."""

    STATION_RANGE = "StationRange"
    PVI_COUNT = "PVICount"
    MANUAL = "Manual"
    NONE = "None"
