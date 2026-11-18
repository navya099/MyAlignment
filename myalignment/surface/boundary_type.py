# surface/boundary_type.py
from enum import Enum


class BoundaryType(Enum):
    """C3D Boundary 유형."""
    OUTER = "outer"        # 외곽 경계
    SHOW = "show"          # 표시 영역 (내부)
    HIDE = "hide"          # 구멍 (내부)
    DATA_CLIP = "data_clip"  # 데이터 클립