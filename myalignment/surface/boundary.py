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
    # bbox 캐시 (frozen이므로 __post_init__에서 object.__setattr__로 설정)
    _bbox_cache: tuple[float, float, float, float] | None = field(
        init=False, repr=False, compare=False, default=None
    )

    def __post_init__(self):
        if len(self.vertices) < 3:
            raise ValueError(f"경계는 ≥ 3점 필요: {len(self.vertices)}")
        xs = [v.x for v in self.vertices]
        ys = [v.y for v in self.vertices]
        object.__setattr__(
            self, "_bbox_cache", (min(xs), min(ys), max(xs), max(ys))
        )

    # ---- 기하 ----
    @property
    def area(self) -> float:
        n = len(self.vertices)
        s = 0.0
        for i in range(n):
            v1 = self.vertices[i]
            v2 = self.vertices[(i + 1) % n]
            s += v1.x * v2.y - v2.x * v1.y
        return abs(s) / 2.0

    @property
    def perimeter(self) -> float:
        n = len(self.vertices)
        total = 0.0
        for i in range(n):
            total += self.vertices[i].distance_to(self.vertices[(i + 1) % n])
        return total

    @property
    def is_counterclockwise(self) -> bool:
        n = len(self.vertices)
        s = 0.0
        for i in range(n):
            v1 = self.vertices[i]
            v2 = self.vertices[(i + 1) % n]
            s += v1.x * v2.y - v2.x * v1.y
        return s > 0

    def bbox(self) -> tuple[float, float, float, float]:
        """경계 상자 (min_x, min_y, max_x, max_y). 캐시 반환."""
        return self._bbox_cache  # type: ignore[return-value]

    def bbox_contains(self, x: float, y: float) -> bool:
        """bbox 사전 필터 (빠른 배제)."""
        min_x, min_y, max_x, max_y = self._bbox_cache  # type: ignore[misc]
        return min_x <= x <= max_x and min_y <= y <= max_y

    def contains_point(self, x, y):
        n = len(self.vertices)
        inside = False
        j = n - 1
        for i in range(n):
            vi = self.vertices[i]
            vj = self.vertices[j]
            if (vi.y > y) != (vj.y > y):
                x_intersect = (vj.x - vi.x) * (y - vi.y) / (vj.y - vi.y) + vi.x
                if x < x_intersect:
                    inside = not inside
            j = i
        # 경계 위 점 보정 (선택)
        if not inside:
            for i in range(n):
                vi = self.vertices[i]
                vj = self.vertices[(i + 1) % n]
                if self._on_segment(vi, vj, x, y):
                    return True
        return inside

    @staticmethod
    def _on_segment(
        a: BoundaryVertex, b: BoundaryVertex,
        x: float, y: float, tol: float = 1e-9,
    ) -> bool:
        """점이 선분 위에 있는지 (bbox 사전 체크)."""
        # bbox 사전 체크 (대부분 여기서 걸러짐)
        min_x = a.x if a.x < b.x else b.x
        max_x = a.x if a.x > b.x else b.x
        if x < min_x - tol or x > max_x + tol:
            return False
        min_y = a.y if a.y < b.y else b.y
        max_y = a.y if a.y > b.y else b.y
        if y < min_y - tol or y > max_y + tol:
            return False

        cross = (b.x - a.x) * (y - a.y) - (b.y - a.y) * (x - a.x)
        if abs(cross) > tol:
            return False
        dot = (x - a.x) * (b.x - a.x) + (y - a.y) * (b.y - a.y)
        length_sq = (b.x - a.x) ** 2 + (b.y - a.y) ** 2
        return 0 <= dot <= length_sq

    # ---- 팩토리 ----
    @classmethod
    def from_coords(
        cls,
        coords: list[tuple[float, float]],
        name: str = "",
        boundary_type: BoundaryType = BoundaryType.OUTER,
    ) -> "Boundary":
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
        vertices = []
        for i in range(n_segments):
            angle = 2 * math.pi * i / n_segments
            vertices.append(
                BoundaryVertex(
                    cx + radius * math.cos(angle),
                    cy + radius * math.sin(angle),
                )
            )
        return cls(
            name=name, boundary_type=boundary_type, vertices=tuple(vertices)
        )

    def __repr__(self) -> str:
        return (
            f"Boundary('{self.name}', {self.boundary_type.name}, "
            f"n={len(self.vertices)}, A={self.area:.2f}m²)"
        )