# surface/tin_surface.py
from __future__ import annotations
from dataclasses import dataclass, field, replace
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
        boundaries: BoundarySet | None = None,
    ) -> "TinSurface":
        """
        점들로부터 TIN 생성.

        - scipy가 있으면 scipy.spatial.Delaunay 사용 (O(N log N)).
        - 없으면 내부 Bowyer-Watson 사용 (O(N²)).
        - 규칙 격자는 TinSurfaceBuilder.add_grid 사용을 권장 (O(N)).
        """
        tin_points = tuple(
            p if isinstance(p, TinPoint) else TinPoint(*p)
            for p in points
        )
        if len(tin_points) < 3:
            raise ValueError(f"TIN은 ≥ 3점 필요: {len(tin_points)}")

        triangles = _triangulate(tin_points)

        # 경계 필터
        bset = boundaries or BoundarySet()
        if len(bset) > 0:
            filtered: list[Triangle] = []
            for tri in triangles:
                p1 = tin_points[tri.a]
                p2 = tin_points[tri.b]
                p3 = tin_points[tri.c]
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
        for tri in self.triangles:
            if tri.contains_point(x, y, self.points):
                return tri
        return None

    def elevation_at(self, x: float, y: float) -> float:
        if len(self.boundaries) > 0 and not self.boundaries.contains_point(x, y):
            return self._nearest_point_z(x, y)
        tri = self.triangle_at(x, y)
        if tri is not None:
            return tri.elevation_at(x, y, self.points)
        return self._nearest_point_z(x, y)

    def _nearest_point_z(self, x: float, y: float) -> float:
        if not self.points:
            return 0.0
        target = TinPoint(x, y, 0)
        return min(self.points, key=lambda p: p.distance_2d(target)).z

    def is_inside_boundary(self, x: float, y: float) -> bool:
        if len(self.boundaries) == 0:
            return True
        return self.boundaries.contains_point(x, y)

    def slope_at(self, x: float, y: float) -> tuple[float, float, float]:
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
        if len(self.boundaries) == 0:
            return sum(tri.area_2d(self.points) for tri in self.triangles)
        total = 0.0
        for tri in self.triangles:
            p1 = self.points[tri.a]
            p2 = self.points[tri.b]
            p3 = self.points[tri.c]
            cx = (p1.x + p2.x + p3.x) / 3.0
            cy = (p1.y + p2.y + p3.y) / 3.0
            if self.boundaries.contains_point(cx, cy):
                total += tri.area_2d(self.points)
        return total

    @property
    def area_3d(self) -> float:
        if len(self.boundaries) == 0:
            return sum(tri.area_3d(self.points) for tri in self.triangles)
        total = 0.0
        for tri in self.triangles:
            p1 = self.points[tri.a]
            p2 = self.points[tri.b]
            p3 = self.points[tri.c]
            cx = (p1.x + p2.x + p3.x) / 3.0
            cy = (p1.y + p2.y + p3.y) / 3.0
            if self.boundaries.contains_point(cx, cy):
                total += tri.area_3d(self.points)
        return total

    # ================================================================
    # 경계 추가/제거
    # ================================================================
    def with_boundary(self, boundary: Boundary) -> "TinSurface":
        new_boundaries = self.boundaries.add(boundary)
        filtered: list[Triangle] = []
        for tri in self.triangles:
            p1 = self.points[tri.a]
            p2 = self.points[tri.b]
            p3 = self.points[tri.c]
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
        return replace(self, boundaries=self.boundaries.remove(name))

    # ================================================================
    # 토공량 (Cut/Fill)
    # ================================================================
    def volume_between(self, other: "TinSurface") -> tuple[float, float]:
        """
        두 Surface 사이의 Cut/Fill.

        전제: 두 Surface가 같은 점 집합(같은 순서)을 가진다.
        → 정점 인덱스로 직접 매칭 (O(T)).
        """
        if len(self.points) != len(other.points):
            raise ValueError("두 Surface의 점 개수가 다름")

        cut_total = 0.0
        fill_total = 0.0
        use_boundary = len(self.boundaries) > 0
        pts = self.points
        opts = other.points

        for tri in self.triangles:
            if use_boundary:
                p1 = pts[tri.a]
                p2 = pts[tri.b]
                p3 = pts[tri.c]
                cx = (p1.x + p2.x + p3.x) / 3.0
                cy = (p1.y + p2.y + p3.y) / 3.0
                if not self.boundaries.contains_point(cx, cy):
                    continue

            d1 = pts[tri.a].z - opts[tri.a].z
            d2 = pts[tri.b].z - opts[tri.b].z
            d3 = pts[tri.c].z - opts[tri.c].z
            avg_diff = (d1 + d2 + d3) / 3.0
            area = tri.area_2d(pts)
            vol = avg_diff * area

            if vol > 0:
                cut_total += vol
            else:
                fill_total += -vol

        return cut_total, fill_total

    def volume_above_elevation(
        self, target_elevation: float
    ) -> tuple[float, float]:
        cut_total = 0.0
        fill_total = 0.0
        use_boundary = len(self.boundaries) > 0
        pts = self.points

        for tri in self.triangles:
            if use_boundary:
                p1 = pts[tri.a]
                p2 = pts[tri.b]
                p3 = pts[tri.c]
                cx = (p1.x + p2.x + p3.x) / 3.0
                cy = (p1.y + p2.y + p3.y) / 3.0
                if not self.boundaries.contains_point(cx, cy):
                    continue

            d1 = pts[tri.a].z - target_elevation
            d2 = pts[tri.b].z - target_elevation
            d3 = pts[tri.c].z - target_elevation
            avg_diff = (d1 + d2 + d3) / 3.0
            area = tri.area_2d(pts)
            vol = avg_diff * area

            if vol > 0:
                cut_total += vol
            else:
                fill_total += -vol

        return cut_total, fill_total

    # ================================================================
    # 경계/집계
    # ================================================================
    @property
    def boundary_edges(self) -> list[tuple[int, int]]:
        edge_count: dict[tuple[int, int], int] = {}
        for tri in self.triangles:
            for a, b in [(tri.a, tri.b), (tri.b, tri.c), (tri.c, tri.a)]:
                edge = (min(a, b), max(a, b))
                edge_count[edge] = edge_count.get(edge, 0) + 1
        return [e for e, c in edge_count.items() if c == 1]

    @property
    def bbox(self) -> tuple[float, float, float, float] | None:
        if not self.points:
            return None
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        return min(xs), min(ys), max(xs), max(ys)

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


# ================================================================
# 삼각분할 전략 (scipy 우선, 폴백 Bowyer-Watson)
# ================================================================
try:
    from scipy.spatial import Delaunay as _SciPyDelaunay
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


def _triangulate(points: tuple[TinPoint, ...]) -> list[Triangle]:
    """점 집합 → 삼각형 리스트."""
    if _HAS_SCIPY and len(points) >= 4:
        coords = [(p.x, p.y) for p in points]
        try:
            tri = _SciPyDelaunay(coords)
            return [
                Triangle(*sorted(map(int, simplex)))
                for simplex in tri.simplices
            ]
        except Exception:
            # Qhull 실패 시 폴백
            pass
    return DelaunayTriangulator.triangulate(list(points))