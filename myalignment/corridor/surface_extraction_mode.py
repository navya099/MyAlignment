from enum import Enum


class SurfaceExtractionMode(Enum):
    """코리더 링크와 점의 표면 추출 방식."""

    SINGLE_LINK = "SingleLink"
    MULTI_LINK = "MultiLink"
    ALL_LINKS = "AllLinks"
    POINT_BASED = "PointBased"
