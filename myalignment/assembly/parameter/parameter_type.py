from enum import Enum


class ParameterType(Enum):
    """서브어셈블리 파라미터의 역할."""

    INPUT = "Input"
    OUTPUT = "Output"
    ENUM = "Enum"
    TARGET = "Target"
    COMPUTED = "Computed"
