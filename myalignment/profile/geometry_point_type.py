from enum import Enum


class GeometryPointType(Enum):
    """수평 선형의 전이점과 접선 교점."""

    TS = "TS"
    SC = "SC"
    CS = "CS"
    ST = "ST"
    BC = "BC"
    EC = "EC"
    PI = "PI"
    NONE = "NONE"
