# surface/tin_surface.py
from __future__ import annotations
from dataclasses import dataclass, field
import math

from myalignment.surface.boundary import Boundary
from myalignment.surface.boundary_set import BoundarySet
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
    boundaries: BoundarySet = field(default_factory=BoundarySet)

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
            boundaries: BoundarySet | None = None
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

        # Boundary 적용: 삼각형 무게중심이 Boundary 내부인 것만 유지
        bset = boundaries or BoundarySet()
        if len(bset) > 0:
            filtered = []
            for tri in triangles:
                p1, p2, p3 = tri.vertices(tin_points)
                cx = (p1.x + p2.x + p3.x) / 3.0
                cy = (p1.y + p2.y + p3.y) / 3.0
                if bset.contains_point(cx, cy):
                    filtered.append(tri)
            triangles = filtered

        return cls(
            name=name,
            points=tin_points,
            triangles=tuple(triangles),
            boundaries=bset,
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

    # ================================================================
    # 표고 조회 (Boundary 체크)
    # ================================================================
    def elevation_at(self, x: float, y: float) -> float:
        """
        점 (x, y)의 표고.

        Boundary 밖이면 가장 가까운 유효 정점 표고 반환.
        """
        # Boundary 체크
        if len(self.boundaries) > 0 and not self.boundaries.contains_point(x, y):
            # 외부 → 가장 가까운 유효 정점
            if not self.points:
                return 0.0
            target = TinPoint(x, y, 0)
            return min(self.points, key=lambda p: p.distance_2d(target)).z

        # Boundary 내부 (또는 Boundary 없음)
        tri = self.triangle_at(x, y)
        if tri is not None:
            return tri.elevation_at(x, y, self.points)

        # 삼각형 없음 → 가장 가까운 정점
        if not self.points:
            return 0.0
        target = TinPoint(x, y, 0)
        return min(self.points, key=lambda p: p.distance_2d(target)).z

    def is_inside_boundary(self, x: float, y: float) -> bool:
        """점이 유효 영역 내부인지."""
        if len(self.boundaries) == 0:
            return True
        return self.boundaries.contains_point(x, y)


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
    # 면적 (Boundary 반영)
    # ================================================================
    @property
    def area_2d(self) -> float:
        """2D 투영 면적 (Boundary 내부 삼각형만)."""
        if len(self.boundaries) == 0:
            return sum(tri.area_2d(self.points) for tri in self.triangles)

        total = 0.0
        for tri in self.triangles:
            p1, p2, p3 = tri.vertices(self.points)
            cx = (p1.x + p2.x + p3.x) / 3.0
            cy = (p1.y + p2.y + p3.y) / 3.0
            if self.boundaries.contains_point(cx, cy):
                total += tri.area_2d(self.points)
        return total

    @property
    def area_3d(self) -> float:
        """3D 실제 면적 (m²)."""
        return sum(tri.area_3d(self.points) for tri in self.triangles)

    # ================================================================
    # 경계 추가/제거
    # ================================================================
    def with_boundary(self, boundary: Boundary) -> "TinSurface":
        """경계 추가한 새 Surface."""
        from dataclasses import replace
        new_boundaries = self.boundaries.add(boundary)

        # 삼각형 재필터링
        filtered = []
        for tri in self.triangles:
            p1, p2, p3 = tri.vertices(self.points)
            cx = (p1.x + p2.x + p3.x) / 3.0
            cy = (p1.y + p2.y + p3.y) / 3.0
            if new_boundaries.contains_point(cx, cy):
                filtered.append(tri)

        return replace(
            self,
            triangles=tuple(filtered),
            boundaries=new_boundaries,
        )

    def without_boundary(self, name: str) -> "TinSurface":
        """경계 제거한 새 Surface."""
        from dataclasses import replace
        return replace(self, boundaries=self.boundaries.remove(name))

    # ================================================================
    # 토공량 (Cut/Fill)
    # ================================================================
    def volume_between(self, other: "TinSurface") -> tuple[float, float]:
        if len(self.points) != len(other.points):
            raise ValueError("두 Surface의 점 개수가 다름")

        cut_total = 0.0
        fill_total = 0.0

        for tri in self.triangles:
            # 경계 필터
            if self.boundaries is not None:
                cx = (self.points[tri.a].x + self.points[tri.b].x + self.points[tri.c].x) / 3
                cy = (self.points[tri.a].y + self.points[tri.b].y + self.points[tri.c].y) / 3
                if not self.boundaries.contains_point(cx, cy):
                    continue

            p1 = self.points[tri.a]
            p2 = self.points[tri.b]
            p3 = self.points[tri.c]
            o1 = other.points[tri.a]
            o2 = other.points[tri.b]
            o3 = other.points[tri.c]

            d1 = p1.z - o1.z
            d2 = p2.z - o2.z
            d3 = p3.z - o3.z
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