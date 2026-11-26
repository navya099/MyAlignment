from enum import Enum


class CameraDirectionMode(Enum):
    """주행 중 카메라의 주시 방향."""

    FORWARD = "Forward"
    BACKWARD = "Backward"
    FIXED = "Fixed"
    LOOK_AHEAD = "LookAhead"
    FREE = "Free"
