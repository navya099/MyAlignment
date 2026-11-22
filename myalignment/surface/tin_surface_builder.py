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
from myalignment.surface.tin_point import TinPoint
from myalignment.surface.tin_surface import TinSurface
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
        return self

    def add_breakline_coords(
        self,
        coords: list[tuple[float, float, float]],
        name: str = "",
        breakline_type: BreaklineType = BreaklineType.STANDARD,
    ) -> "TinSurfaceBuilder":
        return self.add_breakline(
            Breakline.from_coords(coords, name=name, breakline_type=breakline_type)
        )

    # ---- 빌드 ----
    def build(self) -> TinSurface:
        boundaries = BoundarySet(tuple(self._outer_boundaries + self._hide_boundaries))
        breaklines = BreaklineSet(tuple(self._breaklines))
        if self._grid_info is not None:
            nx, ny = self._grid_info
            if len(self._points) == nx * ny and all(
                line.breakline_type == BreaklineType.NON_DESTRUCTIVE for line in breaklines
            ):
                return TinSurface._from_mesh(
                    tuple(self._points), self._build_grid_triangles(nx, ny),
                    self._name, boundaries, breaklines,
                )
        return TinSurface.from_points(
            self._points, name=self._name, boundaries=boundaries, breaklines=breaklines,
        )

    def _build_grid_triangles(self, nx: int, ny: int) -> list[Triangle]:
        """격자 (nx × ny)를 각 셀당 2개 삼각형으로 정형 분할 (O(N))."""
        triangles: list[Triangle] = []
        for i in range(nx - 1):
            for j in range(ny - 1):
                a = i * ny + j
                b = (i + 1) * ny + j
                c = b + 1
                d = a + 1
                triangles.append(Triangle(*sorted((a, b, c))))
                triangles.append(Triangle(*sorted((a, c, d))))
        return triangles

    def add_feature_line_as_breakline(
            self,
            fl: FeatureLine,
            breakline_type: BreaklineType = BreaklineType.STANDARD,
    ) -> "TinSurfaceBuilder":
        """FeatureLine을 Breakline으로 추가."""
        return self.add_breakline(fl.to_breakline(breakline_type))