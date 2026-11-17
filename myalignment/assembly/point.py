# assembly/point.py
from __future__ import annotations
from dataclasses import dataclass, field
import math

from myalignment.assembly.codes import PointCode


@dataclass(frozen=True, slots=True)
class AssemblyPoint:
    """
    서브어셈블리 접점 (불변).

    로컬 좌표계 (x: 횡방향, y: 종방향=0, z: 표고).
    - x: 기준점에서 우측(+)/좌측(-)
    - z: 기준점 표고 대비
    """
    code: PointCode = PointCode.EDGE
    x: float = 0.0  # 횡방향 (m)
    z: float = 0.0  # 표고차 (m)
    is_parametric: bool = False

    def __post_init__(self):
        if not (math.isfinite(self.x) and math.isfinite(self.z)):
            raise ValueError(f"x/z가 유한하지 않음: x={self.x}, z={self.z}")

    @property
    def distance_from_origin(self) -> float:
        return math.hypot(self.x, self.z)

    def offset_by(self, dx: float, dz: float) -> "AssemblyPoint":
        return AssemblyPoint(
            code=self.code, x=self.x + dx, z=self.z + dz,
            is_parametric=self.is_parametric,
        )

    def __repr__(self) -> str:
        return f"Point({self.code.name}, x={self.x:.3f}, z={self.z:.3f})"