# quantity/shape.py
from __future__ import annotations
from dataclasses import dataclass, field
import math

from myalignment.assembly.codes import ShapeCode
from myalignment.assembly.point import AssemblyPoint


@dataclass(frozen=True, slots=True)
class Shape:
    """
    형상 — 링크로 둘러싸인 면적 (불변).

    C3D의 Shape와 호환.
    - 재료 물량 산출의 기본 단위.
    - 로컬 좌표계의 정점들로 정의.
    """
    code: ShapeCode = ShapeCode.PAVEMENT
    material_name: str = ""
    points: tuple[AssemblyPoint, ...] = field(default_factory=tuple)

    def __post_init__(self):
        if len(self.points) < 3:
            raise ValueError(f"Shape는 ≥ 3점 필요: {len(self.points)}")

    @property
    def area(self) -> float:
        """
        폴리곤 면적 (Shoelace formula).

        Returns:
            면적 (m², 항상 ≥ 0).
        """
        n = len(self.points)
        if n < 3:
            return 0.0
        # Shoelace
        s = 0.0
        for i in range(n):
            x1, z1 = self.points[i].x, self.points[i].z
            x2, z2 = self.points[(i + 1) % n].x, self.points[(i + 1) % n].z
            s += x1 * z2 - x2 * z1
        return abs(s) / 2.0

    @property
    def centroid(self) -> tuple[float, float]:
        """폴리곤 무게중심 (x, z)."""
        n = len(self.points)
        if n < 3:
            return 0.0, 0.0
        cx, cz, a = 0.0, 0.0, 0.0
        for i in range(n):
            x1, z1 = self.points[i].x, self.points[i].z
            x2, z2 = self.points[(i + 1) % n].x, self.points[(i + 1) % n].z
            cross = x1 * z2 - x2 * z1
            cx += (x1 + x2) * cross
            cz += (z1 + z2) * cross
            a += cross
        if abs(a) < 1e-12:
            return 0.0, 0.0
        return cx / (3 * a), cz / (3 * a)

    @property
    def perimeter(self) -> float:
        """폴리곤 둘레."""
        n = len(self.points)
        if n < 2:
            return 0.0
        total = 0.0
        for i in range(n):
            p1, p2 = self.points[i], self.points[(i + 1) % n]
            total += math.hypot(p2.x - p1.x, p2.z - p1.z)
        return total

    def with_material(self, material_name: str) -> "Shape":
        """재료 지정한 새 Shape."""
        return Shape(
            code=self.code,
            material_name=material_name,
            points=self.points,
        )

    def __repr__(self) -> str:
        return f"Shape({self.code.name}, mat='{self.material_name}', A={self.area:.3f}m²)"