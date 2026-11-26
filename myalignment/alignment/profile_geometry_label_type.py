from enum import Enum


class ProfileGeometryPointLabelType(Enum):
    """평면 선형에 표시할 종단 기하점 유형."""

    PVI = "PVI"
    VPC = "VPC"
    VPT = "VPT"
    HIGH_POINT = "HighPoint"
    LOW_POINT = "LowPoint"
    GRADE_BREAK = "GradeBreak"
    PROFILE_START = "ProfileStart"
    PROFILE_END = "ProfileEnd"
