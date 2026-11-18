# surface/tin_surface_builder.py
from __future__ import annotations
from myalignment.surface.tin_surface import TinSurface
from myalignment.surface.tin_point import TinPoint


class TinSurfaceBuilder:
    """TinSurface 선언적 빌더."""
    def __init__(self, name: str = "Surface1"):
        self._name = name
        self._points: list[TinPoint] = []

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

    def build(self) -> TinSurface:
        if len(self._points) < 3:
            raise ValueError(f"TIN은 ≥ 3점 필요: {len(self._points)}")
        return TinSurface.from_points(self._points, name=self._name)