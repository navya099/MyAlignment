# surface/breakline.py
from __future__ import annotations
from dataclasses import dataclass, field
import math

from myalignment.surface.breakline_vertex import BreaklineVertex
from myalignment.surface.breakline_type import BreaklineType


@dataclass(frozen=True, slots=True)
class Breakline:
    """
    Breakline (불변).

    C3D의 SurfaceBreakline과 호환.
    - 열린 선 (닫힌 선도 가능).
    - 삼각분할 강제.
    - Wall 타입은 좌/우 표고 별도.
    """
    name: str = ""
    breakline_type: BreaklineType = BreaklineType.STANDARD
    vertices: tuple[BreaklineVertex, ...] = field(default_factory=tuple)
    # Wall 타입용: 각 정점의 우측 표고 (없으면 z 사용)
    right_elevations: tuple[float, ...] = field(default_factory=tuple)

    def __post_init__(self):
        if len(self.vertices) < 2:
            raise ValueError(f"Breakline은 ≥ 2점 필요: {len(self.vertices)}")

        # Wall 타입: right_elevations 검증
        if self.breakline_type == BreaklineType.WALL:
            if self.right_elevations:
                if len(self.right_elevations) != len(self.vertices):
                    raise ValueError(
                        f"Wall right_elevations 개수 불일치: "
                        f"{len(self.right_elevations)} vs {len(self.vertices)}"
                    )

    @property
    def length(self) -> float:
        """3D 길이 (m)."""
        total = 0.0
        for i in range(len(self.vertices) - 1):
            a, b = self.vertices[i], self.vertices[i + 1]
            total += math.sqrt(
                (b.x - a.x) ** 2 + (b.y - a.y) ** 2 + (b.z - a.z) ** 2
            )
        return total

    @property
    def length_2d(self) -> float:
        """2D 길이 (m)."""
        total = 0.0
        for i in range(len(self.vertices) - 1):
            a, b = self.vertices[i], self.vertices[i + 1]
            total += math.hypot(b.x - a.x, b.y - a.y)
        return total

    def segments(self) -> list[tuple[BreaklineVertex, BreaklineVertex]]:
        """세그먼트 리스트."""
        return [
            (self.vertices[i], self.vertices[i + 1])
            for i in range(len(self.vertices) - 1)
        ]

    def elevation_at_x_y(self, x: float, y: float, tol: float = 1e-6) -> float | None:
        """
        점 (x, y)가 Breakline 위에 있으면 그 표고 반환 (선형 보간).

        Breakline 위가 아니면 None.
        """
        for i in range(len(self.vertices) - 1):
            a, b = self.vertices[i], self.vertices[i + 1]
            t = self._project_param(a, b, x, y)
            if t is not None:
                return a.z + t * (b.z - a.z)
        return None

    @staticmethod
    def _project_param(
            a: BreaklineVertex, b: BreaklineVertex,
            x: float, y: float, tol: float = 1e-6,
    ) -> float | None:
        """점 (x, y)의 선분 위 파라미터 t (0~1). 선분 위가 아니면 None."""
        dx = b.x - a.x
        dy = b.y - a.y
        length_sq = dx * dx + dy * dy
        if length_sq < tol * tol:
            return None

        t = ((x - a.x) * dx + (y - a.y) * dy) / length_sq
        if t < -tol or t > 1 + tol:
            return None

        # 수직 거리 확인
        px = a.x + t * dx
        py = a.y + t * dy
        dist = math.hypot(x - px, y - py)
        if dist > tol:
            return None

        return max(0.0, min(1.0, t))

    def bbox(self) -> tuple[float, float, float, float]:
        """경계 상자 (min_x, min_y, max_x, max_y)."""
        xs = [v.x for v in self.vertices]
        ys = [v.y for v in self.vertices]
        return min(xs), min(ys), max(xs), max(ys)

    @classmethod
    def from_coords(
            cls,
            coords: list[tuple[float, float, float]],
            name: str = "",
            breakline_type: BreaklineType = BreaklineType.STANDARD,
    ) -> "Breakline":
        """좌표 리스트로 Breakline 생성."""
        return cls(
            name=name,
            breakline_type=breakline_type,
            vertices=tuple(BreaklineVertex(x, y, z) for x, y, z in coords),
        )

    def __repr__(self) -> str:
        return (
            f"Breakline('{self.name}', {self.breakline_type.name}, "
            f"n={len(self.vertices)}, L={self.length_2d:.2f}m)"
        )