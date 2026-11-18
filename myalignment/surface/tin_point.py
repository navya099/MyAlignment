# surface/tin_point.py
from __future__ import annotations
from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True, order=True)
class TinPoint:
    """
    TIN 정점 (불변).

    (x, y, z) 좌표.
    - order=True → 정렬 가능 (x → y → z 순).
    """
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __post_init__(self):
        if not (math.isfinite(self.x) and math.isfinite(self.y) and math.isfinite(self.z)):
            raise ValueError(f"좌표가 유한하지 않음: ({self.x}, {self.y}, {self.z})")

    def distance_2d(self, other: "TinPoint") -> float:
        """2D 거리 (x, y만)."""
        return math.hypot(self.x - other.x, self.y - other.y)

    def distance_3d(self, other: "TinPoint") -> float:
        """3D 거리."""
        return math.sqrt(
            (self.x - other.x) ** 2
            + (self.y - other.y) ** 2
            + (self.z - other.z) ** 2
        )

    def __repr__(self) -> str:
        return f"TinPoint({self.x:.3f}, {self.y:.3f}, {self.z:.3f})"