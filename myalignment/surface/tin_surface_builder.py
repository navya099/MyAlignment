# surface/tin_surface_builder.py
from __future__ import annotations
from dataclasses import replace

from myalignment.featureline.feature_line import FeatureLine
from myalignment.surface.boundary import Boundary
from myalignment.surface.boundary_set import BoundarySet
from myalignment.surface.boundary_type import BoundaryType
from myalignment.surface.breakline import Breakline
from myalignment.surface.breakline_set import BreaklineSet
from myalignment.surface.breakline_type import BreaklineType
from myalignment.surface.constrained_delaunay import ConstrainedDelaunayTriangulator
from myalignment.surface.delaunay import DelaunayTriangulator
from myalignment.surface.tin_point import TinPoint
from myalignment.surface.tin_surface import TinSurface, _triangulate
from myalignment.surface.triangle import Triangle


class TinSurfaceBuilder:
    """TinSurface 선언적 빌더."""

    def __init__(self, name: str = "Surface1"):
        self._name = name
        self._points: list[TinPoint] = []
        self._outer_boundaries: list[Boundary] = []
        self._hide_boundaries: list[Boundary] = []
        self._grid_info: tuple[int, int] | None = None
        self._breaklines: list[Breakline] = []

    # ---- 점 ----
    def add_point(self, x: float, y: float, z: float) -> "TinSurfaceBuilder":
        self._points.append(TinPoint(x, y, z))
        self._grid_info = None
        return self

    def add_points(
        self, points: list[tuple[float, float, float]]
    ) -> "TinSurfaceBuilder":
        for x, y, z in points:
            self._points.append(TinPoint(x, y, z))
        self._grid_info = None
        return self

    def add_grid(
        self,
        x_min: float, x_max: float,
        y_min: float, y_max: float,
        nx: int, ny: int,
        elevation_func,
    ) -> "TinSurfaceBuilder":
        if nx < 2 or ny < 2:
            raise ValueError(f"격자 크기 ≥ 2 필요: nx={nx}, ny={ny}")
        for i in range(nx):
            for j in range(ny):
                x = x_min + (x_max - x_min) * i / (nx - 1)
                y = y_min + (y_max - y_min) * j / (ny - 1)
                z = elevation_func(x, y)
                self._points.append(TinPoint(x, y, z))
        self._grid_info = (nx, ny)
        return self

    # ---- 경계 (타입 강제) ----
    def add_outer_boundary(self, boundary: Boundary) -> "TinSurfaceBuilder":
        self._outer_boundaries.append(
            replace(boundary, boundary_type=BoundaryType.OUTER)
        )
        return self

    def add_hide_boundary(self, boundary: Boundary) -> "TinSurfaceBuilder":
        self._hide_boundaries.append(
            replace(boundary, boundary_type=BoundaryType.HIDE)
        )
        return self

    # ---- Breakline ----
    def add_breakline(self, breakline: Breakline) -> "TinSurfaceBuilder":
        self._breaklines.append(breakline)
        self._grid_info = None   # Breakline 추가 시 격자 정형 분할 무효
        return self

    def add_breakline_coords(
        self,
        coords: list[tuple[float, float, float]],
        name: str = "",
        breakline_type: BreaklineType = BreaklineType.STANDARD,
    ) -> "TinSurfaceBuilder":
        self._breaklines.append(
            Breakline.from_coords(
                coords, name=name, breakline_type=breakline_type
            )
        )
        self._grid_info = None
        return self

    # ---- 빌드 ----
    def build(self) -> TinSurface:
        if len(self._points) < 3:
            raise ValueError(f"TIN은 ≥ 3점 필요: {len(self._points)}")

        all_boundaries = (
            tuple(self._outer_boundaries) + tuple(self._hide_boundaries)
        )
        boundaries = BoundarySet(boundaries=all_boundaries)
        blset = (
            BreaklineSet(breaklines=tuple(self._breaklines))
            if self._breaklines
            else BreaklineSet()
        )

        # 삼각분할 우선순위:
        #   1) Breakline 있음 → ConstrainedDelaunay (강제)
        #   2) 격자 → 정형 분할 (O(N))
        #   3) 그 외 → scipy.Delaunay / 폴백
        if len(blset) > 0:
            # Breakline 정점을 점 집합에 병합
            all_points = list(self._points)
            for bl in blset.breaklines:
                for v in bl.vertices:
                    all_points.append(TinPoint(v.x, v.y, v.z))
            # 중복 제거
            seen = set()
            unique = []
            for p in all_points:
                key = (round(p.x, 6), round(p.y, 6))
                if key not in seen:
                    seen.add(key)
                    unique.append(p)
            triangles_list = _triangulate(tuple(unique))
            points = tuple(unique)
        elif self._grid_info is not None:
            nx, ny = self._grid_info
            if len(self._points) != nx * ny:
                triangles_list = _triangulate(tuple(self._points))
            else:
                triangles_list = self._build_grid_triangles(nx, ny)
            points = tuple(self._points)
        else:
            triangles_list = _triangulate(tuple(self._points))
            points = tuple(self._points)

        # Boundary 필터 (bbox 사전 필터 + contains_point)
        if len(boundaries) > 0:
            filtered: list[Triangle] = []
            bset = boundaries
            for tri in triangles_list:
                p1 = points[tri.a]
                p2 = points[tri.b]
                p3 = points[tri.c]
                cx = (p1.x + p2.x + p3.x) / 3.0
                cy = (p1.y + p2.y + p3.y) / 3.0
                if bset.contains_point(cx, cy):
                    filtered.append(tri)
            triangles_list = filtered

        return TinSurface(
            name=self._name,
            points=points,
            triangles=tuple(triangles_list),
            boundaries=boundaries,
            breaklines=blset,
        )

    def _build_grid_triangles(self, nx: int, ny: int) -> list[Triangle]:
        """격자 (nx × ny)를 각 셀당 2개 삼각형으로 정형 분할 (O(N))."""
        triangles: list[Triangle] = []
        for j in range(ny - 1):
            base_j = j * nx
            base_j1 = (j + 1) * nx
            for i in range(nx - 1):
                a = base_j + i
                b = base_j + (i + 1)
                c = base_j1 + (i + 1)
                d = base_j1 + i
                triangles.append(Triangle(*sorted((a, b, c))))
                triangles.append(Triangle(*sorted((a, c, d))))
        return triangles

    def add_feature_line_as_breakline(
            self,
            fl: FeatureLine,
            breakline_type: BreaklineType = BreaklineType.STANDARD,
    ) -> "TinSurfaceBuilder":
        """FeatureLine을 Breakline으로 추가."""
        self._breaklines.append(fl.to_breakline(breakline_type))
        return self