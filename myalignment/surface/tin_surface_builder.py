# surface/tin_surface_builder.py
from __future__ import annotations

from myalignment.surface.boundary import Boundary
from myalignment.surface.boundary_set import BoundarySet
from myalignment.surface.boundary_type import BoundaryType
from myalignment.surface.tin_surface import TinSurface
from myalignment.surface.tin_point import TinPoint


class TinSurfaceBuilder:
    """TinSurface 선언적 빌더."""
    def __init__(self, name: str = "Surface1"):
        self._name = name
        self._points: list[TinPoint] = []
        self._boundaries: list[Boundary] = []

    def add_point(self, x: float, y: float, z: float) -> "TinSurfaceBuilder":
        self._points.append(TinPoint(x, y, z))
        return self

    def add_points(self, points: list[tuple[float, float, float]]) -> "TinSurfaceBuilder":
        for x, y, z in points:
            self._points.append(TinPoint(x, y, z))
        return self

    def add_grid(
        self,
        x_min: float, x_max: float,
        y_min: float, y_max: float,
        nx: int, ny: int,
        elevation_func,
    ) -> "TinSurfaceBuilder":
        """격자점 생성 (elevation_func(x, y) → z)."""
        for i in range(nx):
            for j in range(ny):
                x = x_min + (x_max - x_min) * i / (nx - 1)
                y = y_min + (y_max - y_min) * j / (ny - 1)
                z = elevation_func(x, y)
                self._points.append(TinPoint(x, y, z))
        return self

    # ---- Boundary 추가 ----
    def add_outer_boundary(self, boundary: Boundary) -> "TinSurfaceBuilder":
        """외곽 경계 추가."""
        from dataclasses import replace
        self._boundaries.append(
            Boundary(
                name=boundary.name,
                boundary_type=BoundaryType.OUTER,
                vertices=boundary.vertices,
            )
        )
        return self

    def add_hide_boundary(self, boundary: Boundary) -> "TinSurfaceBuilder":
        """구멍 추가."""
        self._boundaries.append(
            Boundary(
                name=boundary.name,
                boundary_type=BoundaryType.HIDE,
                vertices=boundary.vertices,
            )
        )
        return self

    def add_show_boundary(self, boundary: Boundary) -> "TinSurfaceBuilder":
        """표시 영역 추가."""
        self._boundaries.append(
            Boundary(
                name=boundary.name,
                boundary_type=BoundaryType.SHOW,
                vertices=boundary.vertices,
            )
        )
        return self

    def build(self) -> TinSurface:
        if len(self._points) < 3:
            raise ValueError(f"TIN은 ≥ 3점 필요: {len(self._points)}")
        bset = BoundarySet(boundaries=tuple(self._boundaries)) if self._boundaries else None
        return TinSurface.from_points(
            self._points,
            name=self._name,
            boundaries=bset,
        )