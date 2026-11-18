# featureline/vertex.py
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import math


class FeatureLinePointType(Enum):
    """C3D FeatureLine 점 유형."""
    PI = "PI"  # 수평 경로 변경점
    ELEVATION = "Elevation"  # 종단 구배 변경점
    ALL = "All"


@dataclass(frozen=True, slots=True)
class FeatureLineVertex:
    """
    FeatureLine 정점 (3D, 불변).

    C3D의 FeatureLine Point와 호환.
    - PI: 수평 경로가 바뀌는 점
    - Elevation: 표고 구배가 바뀌는 점
    """
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    point_type: FeatureLinePointType = FeatureLinePointType.PI

    def __post_init__(self):
        if not (math.isfinite(self.x) and math.isfinite(self.y) and math.isfinite(self.z)):
            raise ValueError(f"좌표가 유한하지 않음: ({self.x}, {self.y}, {self.z})")

    @property
    def point_2d(self) -> tuple[float, float]:
        return self.x, self.y

    def to_3d_tuple(self) -> tuple[float, float, float]:
        return self.x, self.y, self.z

    def __repr__(self) -> str:
        return f"FLVertex({self.x:.3f}, {self.y:.3f}, {self.z:.3f}, {self.point_type.name})"