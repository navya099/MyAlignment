from enum import Enum


class ContourType(Enum):
    """등고선의 유형."""

    MAJOR = "Major"
    MINOR = "Minor"
    USER = "User"
