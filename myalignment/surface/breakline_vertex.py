# surface/breakline_vertex.py
from __future__ import annotations
from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class BreaklineVertex:
    """
    Breakline 정점 (3D, 불변).

    - Standard/Proximity: z 사용
    - Wall: 좌/우 표고 별도 (z_left, z_right)
    """
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __post_init__(self):
        if not (math.isfinite(self.x) and math.isfinite(self.y) and math.isfinite(self.z)):
            raise ValueError(f"좌표가 유한하지 않음: ({self.x}, {self.y}, {self.z})")

    def to_2d(self) -> tuple[float, float]:
        return self.x, self.y

    def __repr__(self) -> str:
        return f"BLVertex({self.x:.3f}, {self.y:.3f}, {self.z:.3f})"