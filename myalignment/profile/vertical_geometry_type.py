from enum import Enum


class VerticalGeometryPointType(Enum):
    """종단의 교점, 종곡선 경계, 극점과 구배 변경점."""

    PVI = "PVI"
    VPC = "VPC"
    VPT = "VPT"
    HIGH_POINT = "HP"
    LOW_POINT = "LP"
    GRADE_BREAK = "GB"
    NONE = "NONE"
