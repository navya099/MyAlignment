# surface/boundary_vertex.py
from __future__ import annotations
from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class BoundaryVertex:
    """
    경계 정점 (2D, 불변).

    Boundary는 평면 폴리곤 (표고 무시).
    """
    x: float = 0.0
    y: float = 0.0

    def __post_init__(self):
        if not (math.isfinite(self.x) and math.isfinite(self.y)):
            raise ValueError(f"좌표가 유한하지 않음: ({self.x}, {self.y})")

    def distance_to(self, other: "BoundaryVertex") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def __repr__(self) -> str:
        return f"BoundaryVertex({self.x:.3f}, {self.y:.3f})"