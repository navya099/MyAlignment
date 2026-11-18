import math
import pytest
from myalignment.surface.tin_point import TinPoint
from myalignment.surface.triangle import Triangle
from myalignment.surface.tin_surface import TinSurface
from myalignment.surface.tin_surface_builder import TinSurfaceBuilder


def test_triangle_elevation_at():
    """삼각형 내 선형 보간."""
    points = (
        TinPoint(0, 0, 10),
        TinPoint(10, 0, 20),
        TinPoint(0, 10, 30),
    )
    tri = Triangle(0, 1, 2)
    # 평면 z = 10 + x + 2y
    # (5, 5) → 10 + 5 + 10 = 25
    z = tri.elevation_at(5, 5, points)
    assert math.isclose(z, 25.0, abs_tol=1e-6)


def test_triangle_contains_point():
    points = (
        TinPoint(0, 0, 0),
        TinPoint(10, 0, 0),
        TinPoint(0, 10, 0),
    )
    tri = Triangle(0, 1, 2)
    assert tri.contains_point(2, 2, points)
    assert not tri.contains_point(8, 8, points)   # 빗변 밖


def test_triangle_area():
    points = (
        TinPoint(0, 0, 0),
        TinPoint(10, 0, 0),
        TinPoint(0, 10, 0),
    )
    tri = Triangle(0, 1, 2)
    assert math.isclose(tri.area_2d(points), 50.0)


def test_tin_surface_from_points():
    """평면 (z=10) 4점 → TIN 생성."""
    surface = TinSurface.from_points([
        (0, 0, 10),
        (10, 0, 10),
        (10, 10, 10),
        (0, 10, 10),
    ])
    assert len(surface.triangles) == 2   # 사각형 → 2 삼각형
    assert math.isclose(surface.area_2d, 100.0, abs_tol=1e-6)


def test_tin_surface_elevation_at():
    """평면 내부 조회."""
    surface = TinSurface.from_points([
        (0, 0, 10),
        (10, 0, 10),
        (10, 10, 10),
        (0, 10, 10),
    ])
    assert math.isclose(surface.elevation_at(5, 5), 10.0, abs_tol=1e-6)
    assert math.isclose(surface.elevation_at(0, 0), 10.0, abs_tol=1e-6)


def test_tin_surface_slope():
    """경사면 (z = x) 조회."""
    surface = TinSurface.from_points([
        (0, 0, 0),
        (10, 0, 10),
        (10, 10, 10),
        (0, 10, 0),
    ])
    A, B, slope_pct = surface.slope_at(5, 5)
    # z = x → A = 1, B = 0
    assert math.isclose(A, 1.0, abs_tol=1e-6)
    assert math.isclose(B, 0.0, abs_tol=1e-6)
    assert math.isclose(slope_pct, 100.0, abs_tol=1e-6)


def test_volume_between():
    """평면 → 평면 Cut/Fill."""
    flat_10 = TinSurface.from_points([
        (0, 0, 10),
        (10, 0, 10),
        (10, 10, 10),
        (0, 10, 10),
    ])
    flat_5 = TinSurface.from_points([
        (0, 0, 5),
        (10, 0, 5),
        (10, 10, 5),
        (0, 10, 5),
    ])

    cut, fill = flat_10.volume_between(flat_5)
    # 100m² × 5m = 500m³ cut
    assert math.isclose(cut, 500.0, abs_tol=1e-6)
    assert math.isclose(fill, 0.0, abs_tol=1e-6)


def test_volume_above_elevation():
    """특정 표고 기준 Cut/Fill."""
    surface = TinSurface.from_points([
        (0, 0, 15),
        (10, 0, 15),
        (10, 10, 15),
        (0, 10, 15),
    ])
    cut, fill = surface.volume_above_elevation(10.0)
    # 100m² × 5m = 500m³ cut
    assert math.isclose(cut, 500.0, abs_tol=1e-6)
    assert math.isclose(fill, 0.0, abs_tol=1e-6)


def test_boundary_edges():
    """사각형 TIN 경계 = 4변."""
    surface = TinSurface.from_points([
        (0, 0, 0),
        (10, 0, 0),
        (10, 10, 0),
        (0, 10, 0),
    ])
    boundary = surface.boundary_edges
    assert len(boundary) == 4


def test_builder_grid():
    """격자점으로 TIN 생성."""
    surface = (
        TinSurfaceBuilder("격자지형")
        .add_grid(0, 10, 0, 10, nx=3, ny=3, elevation_func=lambda x, y: 10 + x * 0.1)
        .build()
    )
    assert len(surface.points) == 9
    assert len(surface.triangles) > 0