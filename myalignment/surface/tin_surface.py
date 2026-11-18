# surface/tin_surface.py
from __future__ import annotations
from dataclasses import dataclass, field
import math

from myalignment.surface.tin_point import TinPoint
from myalignment.surface.triangle import Triangle
from myalignment.surface.delaunay import DelaunayTriangulator


@dataclass(frozen=True, slots=True)
class TinSurface:
    """
    TIN 지표면 (불변).

    C3D의 TINSurface와 호환.
    - 점 + 삼각형 + 경계.
    - 임의 점의 표고/경사 계산.
    """
    name: str = "Surface1"
    points: tuple[TinPoint, ...] = field(default_factory=tuple)
    triangles: tuple[Triangle, ...] = field(default_factory=tuple)

    def __post_init__(self):
        # 삼각형 인덱스 유효성
        n = len(self.points)
        for tri in self.triangles:
            for v in (tri.a, tri.b, tri.c):
                if v < 0 or v >= n:
                    raise ValueError(f"삼각형 인덱스 범위 초과: {v} (n={n})")

    # ================================================================
    # 생성
    # ================================================================
    @classmethod
    def from_points(
            cls,
            points: list[TinPoint] | list[tuple[float, float, float]],
            name: str = "Surface1",
    ) -> "TinSurface":
        """
        점들로부터 TIN 생성 (들로네 삼각분할).
        """
        # tuple → TinPoint
        tin_points = tuple(
            p if isinstance(p, TinPoint) else TinPoint(*p)
            for p in points
        )
        if len(tin_points) < 3:
            raise ValueError(f"TIN은 ≥ 3점 필요: {len(tin_points)}")

        # 들로네 삼각분할
        triangles = DelaunayTriangulator.triangulate(list(tin_points))

        return cls(
            name=name,
            points=tin_points,
            triangles=tuple(triangles),
        )

    # ================================================================
    # 표고/경사 조회
    # ================================================================
    def triangle_at(self, x: float, y: float) -> Triangle | None:
        """점 (x, y)가 속한 삼각형."""
        for tri in self.triangles:
            if tri.contains_point(x, y, self.points):
                return tri
        return None

    def elevation_at(self, x: float, y: float) -> float:
        """
        점 (x, y)의 표고 (삼각형 내 선형 보간).

        표면 밖이면 가장 가까운 정점의 표고 반환.
        """
        tri = self.triangle_at(x, y)
        if tri is not None:
            return tri.elevation_at(x, y, self.points)

        # 표면 밖 → 가장 가까운 정점
        if not self.points:
            return 0.0
        target = TinPoint(x, y, 0)
        return min(self.points, key=lambda p: p.distance_2d(target)).z

    def slope_at(self, x: float, y: float) -> tuple[float, float, float]:
        """
        점 (x, y)의 경사.

        Returns:
            (A, B, slope_percent)
            - A: ∂z/∂x
            - B: ∂z/∂y
            - slope_percent: √(A² + B²) × 100 (%)
        """
        tri = self.triangle_at(x, y)
        if tri is None:
            return 0.0, 0.0, 0.0

        A, B, _ = tri.compute_coefficients(self.points)
        slope_pct = math.hypot(A, B) * 100.0
        return A, B, slope_pct

    # ================================================================
    # 면적
    # ================================================================
    @property
    def area_2d(self) -> float:
        """2D 투영 면적 (m²)."""
        return sum(tri.area_2d(self.points) for tri in self.triangles)

    @property
    def area_3d(self) -> float:
        """3D 실제 면적 (m²)."""
        return sum(tri.area_3d(self.points) for tri in self.triangles)

    # ================================================================
    # 토공량 (Cut/Fill)
    # ================================================================
    def volume_between(self, other: "TinSurface") -> tuple[float, float]:
        """
        두 Surface 사이의 토공량.

        Returns:
            (cut_volume, fill_volume)
            - cut: self > other (깎기)
            - fill: self < other (쌓기)
        """
        # 두 Surface의 삼각형이 일치한다고 가정 (같은 점 집합)
        if len(self.points) != len(other.points):
            raise ValueError("두 Surface의 점 개수가 다름")

        cut_total = 0.0
        fill_total = 0.0

        for tri in self.triangles:
            p1, p2, p3 = tri.vertices(self.points)
            # 상대 Surface의 동일 정점 표고
            z1_o = other.elevation_at(p1.x, p1.y)
            z2_o = other.elevation_at(p2.x, p2.y)
            z3_o = other.elevation_at(p3.x, p3.y)

            # 높이 차이 (self - other)
            d1 = p1.z - z1_o
            d2 = p2.z - z2_o
            d3 = p3.z - z3_o

            # 평균 높이 차 × 2D 면적
            avg_diff = (d1 + d2 + d3) / 3.0
            area = tri.area_2d(self.points)

            vol = avg_diff * area
            if vol > 0:
                cut_total += vol
            else:
                fill_total += -vol

        return cut_total, fill_total

    def volume_above_elevation(self, target_elevation: float) -> tuple[float, float]:
        """
        특정 표고 기준 Cut/Fill.

        Returns:
            (cut_volume, fill_volume)
            - cut: self > target (제거)
            - fill: self < target (채움)
        """
        cut_total = 0.0
        fill_total = 0.0

        for tri in self.triangles:
            p1, p2, p3 = tri.vertices(self.points)
            d1 = p1.z - target_elevation
            d2 = p2.z - target_elevation
            d3 = p3.z - target_elevation

            avg_diff = (d1 + d2 + d3) / 3.0
            area = tri.area_2d(self.points)
            vol = avg_diff * area

            if vol > 0:
                cut_total += vol
            else:
                fill_total += -vol

        return cut_total, fill_total

    # ================================================================
    # 경계
    # ================================================================
    @property
    def boundary_edges(self) -> list[tuple[int, int]]:
        """
        경계 변 리스트 (한 번만 등장하는 변).
        """
        edge_count = {}
        for tri in self.triangles:
            for a, b in [(tri.a, tri.b), (tri.b, tri.c), (tri.c, tri.a)]:
                edge = (min(a, b), max(a, b))
                edge_count[edge] = edge_count.get(edge, 0) + 1

        return [e for e, c in edge_count.items() if c == 1]

    @property
    def bbox(self) -> tuple[float, float, float, float] | None:
        """경계 상자 (min_x, min_y, max_x, max_y)."""
        if not self.points:
            return None
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        return min(xs), min(ys), max(xs), max(ys)

    # ================================================================
    # 집계
    # ================================================================
    @property
    def min_elevation(self) -> float:
        return min((p.z for p in self.points), default=0.0)

    @property
    def max_elevation(self) -> float:
        return max((p.z for p in self.points), default=0.0)

    def __repr__(self) -> str:
        return (
            f"TinSurface('{self.name}', "
            f"points={len(self.points)}, "
            f"triangles={len(self.triangles)}, "
            f"area={self.area_2d:,.1f}m²)"
        )