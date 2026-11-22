# surface/tin_surface.py
from __future__ import annotations
from dataclasses import dataclass, field, replace
import math

from myalignment.surface.boundary import Boundary
from myalignment.surface.boundary_clipping import clip_mesh
from myalignment.surface.boundary_set import BoundarySet
from myalignment.surface.breakline import Breakline
from myalignment.surface.breakline_set import BreaklineSet
from myalignment.surface.breakline_type import BreaklineType
from myalignment.surface.constrained_delaunay import ConstrainedDelaunayTriangulator
from myalignment.surface.tin_point import TinPoint
from myalignment.surface.triangle import Triangle
from myalignment.surface.delaunay import DelaunayTriangulator

import logging
logger = logging.getLogger(__name__)

@dataclass(frozen=True, slots=True)
class TinSurface:
    """
    TIN 지표면 (불변).

    C3D의 TINSurface와 호환.
    - 점 + 삼각형 + 경계 + Breakline.
    - 임의 점의 표고/경사 계산.
    """
    name: str = "Surface1"
    points: tuple[TinPoint, ...] = field(default_factory=tuple)
    triangles: tuple[Triangle, ...] = field(default_factory=tuple)
    boundaries: BoundarySet = field(default_factory=BoundarySet)
    breaklines: BreaklineSet = field(default_factory=BreaklineSet)

    # 제약선을 편집할 때 삽입점과 덮어쓴 표고를 원본에 누적하지 않는다.
    _source_points: tuple[TinPoint, ...] | None = field(
        default=None, repr=False, compare=False, kw_only=True,
    )

    _boundary_source: tuple[tuple[TinPoint, ...], tuple[Triangle, ...]] | None = field(
        default=None, repr=False, compare=False, kw_only=True,
    )

    def __post_init__(self):
        n = len(self.points)
        for tri in self.triangles:
            for v in (tri.a, tri.b, tri.c):
                if v < 0 or v >= n:
                    raise ValueError(f"삼각형 인덱스 범위 초과: {v} (n={n})")

        if len(self.boundaries) and self._boundary_source is None:
            source = (self.points, self.triangles)
            points, faces = clip_mesh(*source, self.boundaries)
            object.__setattr__(self, "_boundary_source", source)
            object.__setattr__(self, "points", points)
            object.__setattr__(self, "triangles", faces)

    # ================================================================
    # 생성
    # ================================================================
    @classmethod
    def from_points(
        cls,
        points: list[TinPoint] | list[tuple[float, float, float]],
        name: str = "Surface1",
        boundaries: BoundarySet | None = None,
        breaklines: BreaklineSet | None = None,
    ) -> "TinSurface":
        """
        점들로부터 TIN 생성.

        우선순위:
            1. Breakline 있음 → ConstrainedDelaunay (강제 삼각분할)
            2. 없음 → scipy.Delaunay → 폴백 Bowyer-Watson
        """
        tin_points = tuple(
            p if isinstance(p, TinPoint) else TinPoint(*p)
            for p in points
        )
        if len(tin_points) < 3:
            raise ValueError(f"TIN은 ≥ 3점 필요: {len(tin_points)}")

        bset = boundaries or BoundarySet()
        blset = breaklines or BreaklineSet()

        if any(line.breakline_type != BreaklineType.NON_DESTRUCTIVE for line in blset):
            triangles, all_points = ConstrainedDelaunayTriangulator.triangulate(
                list(tin_points), list(blset)
            )
            return cls._from_mesh(
                tuple(all_points), triangles, name, bset, blset, source_points=tin_points,
            )

        return cls._from_mesh(tin_points, _triangulate(tin_points), name, bset, blset)

    @classmethod
    def _from_mesh(
        cls,
        points: tuple[TinPoint, ...],
        triangles: list[Triangle],
        name: str,
        boundaries: BoundarySet,
        breaklines: BreaklineSet,
        *,
        source_points: tuple[TinPoint, ...] | None = None,
    ) -> "TinSurface":
        return cls(
            name=name,
            points=points,
            triangles=tuple(triangles),
            boundaries=boundaries,
            breaklines=breaklines,
            _source_points=source_points,
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
        """점의 표고. 벽 선상에서는 방향 기준 좌측 표고를 반환한다."""
        tri = self.triangle_at(x, y)
        if tri is None:
            return self._nearest_point_z(x, y)

        for bl in self.breaklines:
            if bl.breakline_type in (BreaklineType.STANDARD, BreaklineType.WALL):
                z = bl.elevation_at_x_y(x, y)
                if z is not None:
                    return z
        return tri.elevation_at(x, y, self.points)

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
        return sum(tri.area_2d(self.points) for tri in self.triangles)

    @property
    def area_3d(self) -> float:
        return sum(tri.area_3d(self.points) for tri in self.triangles)

    # ================================================================
    # 경계/Breakline 추가/제거
    # ================================================================
    def with_boundary(self, boundary: Boundary) -> "TinSurface":
        return self._with_boundaries(self.boundaries.add(boundary))

    def without_boundary(self, name: str) -> "TinSurface":
        return self._with_boundaries(self.boundaries.remove(name))

    def _with_boundaries(self, boundaries: BoundarySet) -> "TinSurface":
        points, faces = self._boundary_source or (self.points, self.triangles)
        return replace(self, boundaries=boundaries, points=points, triangles=faces, _boundary_source=None)

    def _breakline_base_points(self) -> tuple[TinPoint, ...]:
        if self._source_points is not None:
            return self._source_points
        if self._boundary_source is not None:
            return self._boundary_source[0]
        return self.points

    def with_breakline(self, breakline: Breakline) -> "TinSurface":
        """Breakline 추가한 새 Surface (재삼각분할)."""
        new_blset = self.breaklines.add(breakline)
        if breakline.breakline_type == BreaklineType.NON_DESTRUCTIVE:
            return replace(self, breaklines=new_blset)
        return TinSurface.from_points(
            list(self._breakline_base_points()),
            name=self.name,
            boundaries=self.boundaries,
            breaklines=new_blset,
        )

    def without_breakline(self, name: str) -> "TinSurface":
        """Breakline 제거한 새 Surface (재삼각분할)."""
        new_blset = self.breaklines.remove(name)
        if all(
            line.name != name or line.breakline_type == BreaklineType.NON_DESTRUCTIVE
            for line in self.breaklines
        ):
            return replace(self, breaklines=new_blset)
        return TinSurface.from_points(
            list(self._breakline_base_points()),
            name=self.name,
            boundaries=self.boundaries,
            breaklines=new_blset,
        )

    # ================================================================
    # 토공량 (Cut/Fill)
    # ================================================================
    def volume_between(self, other: "TinSurface") -> tuple[float, float]:
        """공통 삼각망에서 절·성토량을 산출한다. self는 원지형이다."""
        from myalignment.surface.volume import cut_fill_between

        return cut_fill_between(self, other)

    def volume_above_elevation(
        self, target_elevation: float
    ) -> tuple[float, float]:
        """기준 표고 위 절토량과 아래 성토량을 반환한다."""
        from myalignment.surface.volume import cut_fill_at_elevation

        if not math.isfinite(target_elevation):
            raise ValueError("기준 표고는 유한해야 합니다.")
        return cut_fill_at_elevation(self, target_elevation)

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
            f"breaklines={len(self.breaklines)}, "
            f"area={self.area_2d:,.1f}m²)"
        )


# ================================================================
# 삼각분할 전략 (scipy 우선, 폴백 Bowyer-Watson)
# ================================================================
try:
    from scipy.spatial import Delaunay as _SciPyDelaunay
    _HAS_SCIPY = True
    logger.debug("scipy.Delaunay 사용 가능")
except ImportError:
    _HAS_SCIPY = False
    logger.warning(
        "scipy 미설치 → Bowyer-Watson 폴백 (대규모 점에서 매우 느림). "
        "`pip install scipy` 권장."
    )

def _triangulate(points: tuple[TinPoint, ...]) -> list[Triangle]:
    """점 집합 → 삼각형 리스트. scipy 우선, 폴백 Bowyer-Watson."""
    if _HAS_SCIPY and len(points) >= 4:
        coords = [(p.x, p.y) for p in points]
        try:
            tri = _SciPyDelaunay(coords)
            return [
                Triangle(*sorted(map(int, simplex)))
                for simplex in tri.simplices
            ]
        except Exception as e:
            import warnings
            warnings.warn(f"scipy Delaunay 실패, 폴백: {e}")
    return DelaunayTriangulator.triangulate(list(points))
