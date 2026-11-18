# surface/boundary.py
from __future__ import annotations
from dataclasses import dataclass, field
import math

from myalignment.surface.boundary_vertex import BoundaryVertex
from myalignment.surface.boundary_type import BoundaryType


@dataclass(frozen=True, slots=True)
class Boundary:
    """
    Surface 경계 (불변).

    C3D의 SurfaceBoundary와 호환.
    - 닫힌 폴리곤.
    - 유형별 역할 (Outer/Show/Hide/DataClip).
    """
    name: str = ""
    boundary_type: BoundaryType = BoundaryType.OUTER
    vertices: tuple[BoundaryVertex, ...] = field(default_factory=tuple)

    def __post_init__(self):
        if len(self.vertices) < 3:
            raise ValueError(f"경계는 ≥ 3점 필요: {len(self.vertices)}")

    @property
    def area(self) -> float:
        """
        폴리곤 면적 (Shoelace, 절댓값).

        Returns:
            면적 (m², 항상 ≥ 0).
        """
        n = len(self.vertices)
        s = 0.0
        for i in range(n):
            v1 = self.vertices[i]
            v2 = self.vertices[(i + 1) % n]
            s += v1.x * v2.y - v2.x * v1.y
        return abs(s) / 2.0

    @property
    def perimeter(self) -> float:
        """둘레 (m)."""
        n = len(self.vertices)
        total = 0.0
        for i in range(n):
            total += self.vertices[i].distance_to(self.vertices[(i + 1) % n])
        return total

    @property
    def is_counterclockwise(self) -> bool:
        """반시계 방향 여부 (면적 부호)."""
        n = len(self.vertices)
        s = 0.0
        for i in range(n):
            v1 = self.vertices[i]
            v2 = self.vertices[(i + 1) % n]
            s += v1.x * v2.y - v2.x * v1.y
        return s > 0

    def contains_point(self, x: float, y: float) -> bool:
        """
        점 (x, y)가 폴리곤 내부에 있는지 (Ray casting).

        경계 위 점은 "내부"로 처리.
        """
        n = len(self.vertices)
        inside = False
        j = n - 1
        for i in range(n):
            vi = self.vertices[i]
            vj = self.vertices[j]
            # 점이 변 위에 있는지
            if self._on_segment(vi, vj, x, y):
                return True
            # Ray casting
            if ((vi.y > y) != (vj.y > y)):
                x_intersect = (vj.x - vi.x) * (y - vi.y) / (vj.y - vi.y) + vi.x
                if x < x_intersect:
                    inside = not inside
            j = i
        return inside

    @staticmethod
    def _on_segment(a: BoundaryVertex, b: BoundaryVertex, x: float, y: float, tol: float = 1e-9) -> bool:
        """점이 선분 위에 있는지."""
        cross = (b.x - a.x) * (y - a.y) - (b.y - a.y) * (x - a.x)
        if abs(cross) > tol:
            return False
        dot = (x - a.x) * (b.x - a.x) + (y - a.y) * (b.y - a.y)
        length_sq = (b.x - a.x) ** 2 + (b.y - a.y) ** 2
        return 0 <= dot <= length_sq

    def bbox(self) -> tuple[float, float, float, float]:
        """경계 상자 (min_x, min_y, max_x, max_y)."""
        xs = [v.x for v in self.vertices]
        ys = [v.y for v in self.vertices]
        return min(xs), min(ys), max(xs), max(ys)

    @classmethod
    def from_coords(
            cls,
            coords: list[tuple[float, float]],
            name: str = "",
            boundary_type: BoundaryType = BoundaryType.OUTER,
    ) -> "Boundary":
        """좌표 리스트로 경계 생성."""
        return cls(
            name=name,
            boundary_type=boundary_type,
            vertices=tuple(BoundaryVertex(x, y) for x, y in coords),
        )

    @classmethod
    def rectangle(
            cls,
            x_min: float, y_min: float,
            x_max: float, y_max: float,
            name: str = "",
            boundary_type: BoundaryType = BoundaryType.OUTER,
    ) -> "Boundary":
        """사각형 경계 (반시계)."""
        return cls(
            name=name,
            boundary_type=boundary_type,
            vertices=(
                BoundaryVertex(x_min, y_min),
                BoundaryVertex(x_max, y_min),
                BoundaryVertex(x_max, y_max),
                BoundaryVertex(x_min, y_max),
            ),
        )

    @classmethod
    def circle(
            cls,
            cx: float, cy: float, radius: float,
            n_segments: int = 32,
            name: str = "",
            boundary_type: BoundaryType = BoundaryType.OUTER,
    ) -> "Boundary":
        """원 경계 (n각형 근사)."""
        vertices = []
        for i in range(n_segments):
            angle = 2 * math.pi * i / n_segments
            vertices.append(
                BoundaryVertex(cx + radius * math.cos(angle), cy + radius * math.sin(angle))
            )
        return cls(name=name, boundary_type=boundary_type, vertices=tuple(vertices))

    def __repr__(self) -> str:
        return (
            f"Boundary('{self.name}', {self.boundary_type.name}, "
            f"n={len(self.vertices)}, A={self.area:.2f}m²)"
        )