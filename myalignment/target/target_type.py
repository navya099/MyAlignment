# target/target_type.py
from enum import Enum


class TargetType(Enum):
    """C3D Target 유형."""
    OFFSET = "offset"        # 폭/간격띄우기
    ELEVATION = "elevation"  # 표고
    SURFACE = "surface"      # 지표면
    PIPE_NETWORK = "pipe"    # 관망