from enum import Enum


class ConditionType(Enum):
    """조건 평가에 사용하는 값의 종류."""

    CUT_FILL = "CutFill"
    SURFACE_ELEVATION = "SurfaceElevation"
    OFFSET_RANGE = "OffsetRange"
    GRADE_THRESHOLD = "GradeThreshold"
    TARGET_REACHED = "TargetReached"
    CUSTOM = "Custom"
