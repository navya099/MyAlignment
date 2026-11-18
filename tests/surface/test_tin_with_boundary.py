# tests/surface/test_tin_with_boundary.py
from myalignment.surface.tin_surface import TinSurface
from myalignment.surface.tin_surface_builder import TinSurfaceBuilder
from myalignment.surface.boundary import Boundary
from myalignment.surface.boundary_type import BoundaryType
import math

def test_tin_with_outer_boundary():
    """격자 10×10 점 → Outer Boundary(사각형)"""
    surface = (
        TinSurfaceBuilder("경계지형")
        .add_grid(0, 10, 0, 10, nx=11, ny=11, elevation_func=lambda x, y: 100)
        .add_outer_boundary(Boundary.rectangle(0, 0, 10, 10, name="외곽"))
        .build()
    )

    # 경계 내부
    assert surface.is_inside_boundary(5, 5)
    assert math.isclose(surface.elevation_at(5, 5), 100.0)

    # 경계 외부
    assert not surface.is_inside_boundary(20, 20)


def test_tin_with_hole():
    """사각형 Surface + 원형 구멍."""
    surface = (
        TinSurfaceBuilder("구멍지형")
        .add_grid(0, 10, 0, 10, nx=11, ny=11, elevation_func=lambda x, y: 100)
        .add_outer_boundary(Boundary.rectangle(0, 0, 10, 10, name="외곽"))
        .add_hide_boundary(Boundary.circle(5, 5, 2, name="구멍"))
        .build()
    )

    # 구멍 내부
    assert not surface.is_inside_boundary(5, 5)

    # 구멍 밖
    assert surface.is_inside_boundary(1, 1)


def test_tin_area_with_hole():
    """구멍이 면적에서 차감되는지."""
    surface = (
        TinSurfaceBuilder()
        .add_grid(0, 10, 0, 10, nx=21, ny=21, elevation_func=lambda x, y: 100)
        .add_outer_boundary(Boundary.rectangle(0, 0, 10, 10, name="외곽"))
        .add_hide_boundary(Boundary.circle(5, 5, 2, n_segments=64, name="구멍"))
        .build()
    )

    # 유효 면적 ≈ 100 - π·4 ≈ 87.43
    assert abs(surface.area_2d - (100.0 - math.pi * 4.0)) < 2.0


def test_tin_with_multiple_holes():
    """여러 구멍."""
    surface = (
        TinSurfaceBuilder()
        .add_grid(0, 10, 0, 10, nx=21, ny=21, elevation_func=lambda x, y: 100)
        .add_outer_boundary(Boundary.rectangle(0, 0, 10, 10))
        .add_hide_boundary(Boundary.rectangle(1, 1, 3, 3, name="구멍1"))
        .add_hide_boundary(Boundary.rectangle(6, 6, 9, 9, name="구멍2"))
        .build()
    )

    assert not surface.is_inside_boundary(2, 2)
    assert not surface.is_inside_boundary(7, 7)
    assert surface.is_inside_boundary(5, 5)


def test_volume_with_boundary():
    """Boundary 내부의 토공량만 산출."""
    # 10×10 사각형, Boundary = 5×5 중앙
    existing = (
        TinSurfaceBuilder()
        .add_grid(0, 10, 0, 10, nx=21, ny=21, elevation_func=lambda x, y: 10)
        .add_outer_boundary(Boundary.rectangle(2.5, 2.5, 7.5, 7.5))
        .build()
    )
    design = (
        TinSurfaceBuilder()
        .add_grid(0, 10, 0, 10, nx=21, ny=21, elevation_func=lambda x, y: 5)
        .add_outer_boundary(Boundary.rectangle(2.5, 2.5, 7.5, 7.5))
        .build()
    )

    cut, fill = existing.volume_between(design)
    # 유효 면적 25m² × 높이 5m = 125m³
    assert math.isclose(cut, 125.0, abs_tol=5.0)