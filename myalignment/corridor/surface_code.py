from enum import Enum


class CorridorSurfaceCode(Enum):
    """코리더 표면 추출 코드."""

    TOP = "Top"
    PAVEMENT = "Pavement"
    SUBBASE = "Subbase"
    DATUM = "Datum"
    SLOPE = "Slope"
    SHOULDER = "Shoulder"
    RAIL_TOP = "RailTop"
    BALLAST = "Ballast"
    CUSTOM = "Custom"
