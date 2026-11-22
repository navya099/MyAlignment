# surface/triangle.py
from __future__ import annotations
from dataclasses import dataclass
import math

from myalignment.surface.tin_point import TinPoint


@dataclass(frozen=True, slots=True)
class Triangle:
    """
    TIN 삼각형 (불변).

    - 정점 인덱스 3개 (a < b < c 순).
    - 평면 방정식 캐시.
    """
    a: int = 0
    b: int = 1
    c: int = 2
    # 평면 방정식 계수: z = A*x + B*y + C
    _coeff: tuple[float, float, float] | None = None

    def __post_init__(self):
        if len({self.a, self.b, self.c}) != 3:
            raise ValueError(f"삼각형 정점 중복: {self.a}, {self.b}, {self.c}")

    def vertices(self, points: tuple[TinPoint, ...]) -> tuple[TinPoint, TinPoint, TinPoint]:
        """정점 좌표 반환."""
        return points[self.a], points[self.b], points[self.c]

    def compute_coefficients(self, points: tuple[TinPoint, ...]) -> tuple[float, float, float]:
        """
        평면 방정식 z = A*x + B*y + C 계산.

        세 점 (x1,y1,z1), (x2,y2,z2), (x3,y3,z3)로부터.
        """
        if self._coeff is not None:
            return self._coeff

        p1, p2, p3 = self.vertices(points)
        x1, y1, z1 = p1.x, p1.y, p1.z
        x2, y2, z2 = p2.x, p2.y, p2.z
        x3, y3, z3 = p3.x, p3.y, p3.z

        # 행렬식
        det = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
        if abs(det) < 1e-12:
            raise ValueError("삼각형이 퇴화됨 (일직선)")

        A = ((z2 - z1) * (y3 - y1) - (z3 - z1) * (y2 - y1)) / det
        B = ((z3 - z1) * (x2 - x1) - (z2 - z1) * (x3 - x1)) / det
        C = z1 - A * x1 - B * y1

        return A, B, C

    def area_2d(self, points: tuple[TinPoint, ...]) -> float:
        """2D 투영 면적 (Shoelace)."""
        p1, p2, p3 = self.vertices(points)
        return abs(
            (p2.x - p1.x) * (p3.y - p1.y) - (p3.x - p1.x) * (p2.y - p1.y)
        ) / 2.0

    def area_3d(self, points: tuple[TinPoint, ...]) -> float:
        """3D 실제 면적."""
        p1, p2, p3 = self.vertices(points)
        ux, uy, uz = p2.x - p1.x, p2.y - p1.y, p2.z - p1.z
        vx, vy, vz = p3.x - p1.x, p3.y - p1.y, p3.z - p1.z
        # 외적 크기 / 2
        cx = uy * vz - uz * vy
        cy = uz * vx - ux * vz
        cz = ux * vy - uy * vx
        return math.sqrt(cx * cx + cy * cy + cz * cz) / 2.0

    def contains_point(self, x: float, y: float, points: tuple[TinPoint, ...]) -> bool:
        """
        점이 삼각형 내부에 있는지 (2D 투영 기준).

        반평면 테스트 (Barycentric).
        """
        p1, p2, p3 = self.vertices(points)

        det = (p2.x - p1.x) * (p3.y - p1.y) - (p3.x - p1.x) * (p2.y - p1.y)
        if abs(det) < 1e-12:
            return False

        d1 = (x - p2.x) * (p1.y - p2.y) - (p1.x - p2.x) * (y - p2.y)
        d2 = (x - p3.x) * (p2.y - p3.y) - (p2.x - p3.x) * (y - p3.y)
        d3 = (x - p1.x) * (p3.y - p1.y) - (p3.x - p1.x) * (y - p1.y)

        has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
        has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
        return not (has_neg and has_pos)

    def elevation_at(self, x: float, y: float, points: tuple[TinPoint, ...]) -> float:
        """평면 방정식으로 표고 계산 (내부 가정)."""
        A, B, C = self.compute_coefficients(points)
        return A * x + B * y + C

    def __repr__(self) -> str:
        return f"Triangle({self.a}, {self.b}, {self.c})"
