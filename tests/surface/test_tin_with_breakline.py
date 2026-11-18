# tests/surface/test_tin_with_breakline.py
from myalignment.surface.breakline_type import BreaklineType
from myalignment.surface.tin_surface import TinSurface
from myalignment.surface.tin_surface_builder import TinSurfaceBuilder
import math


def test_tin_with_breakline():
    """Breakline을 따라 표고가 정확히 반영."""
    surface = (
        TinSurfaceBuilder("능선지형")
        .add_points([
            (0, 0, 100), (10, 0, 100), (20, 0, 100),
            (0, 10, 100), (10, 10, 100), (20, 10, 100),
        ])
        # 중앙선을 능선 (z=110)으로 강제
        .add_breakline_coords(
            [(0, 5, 110), (20, 5, 110)],
            name="능선",
            breakline_type=BreaklineType.STANDARD,
        )
        .build()
    )

    # Breakline 위 표고 = 110
    assert math.isclose(surface.elevation_at(10, 5), 110.0, abs_tol=1e-6)
    # Breakline 밖 표고 = 100 (근사)
    z_outside = surface.elevation_at(5, 2)
    assert z_outside < 110.0   # 능선보다 낮음


def test_tin_breakline_affects_triangulation():
    """Breakline이 삼각분할을 제어."""
    # Breakline 없이
    surface_no_bl = (
        TinSurfaceBuilder("NoBL")
        .add_points([
            (0, 0, 100), (10, 0, 100),
            (0, 10, 100), (10, 10, 100),
        ])
        .build()
    )
    # Breakline 포함 (능선 z=120)
    surface_with_bl = (
        TinSurfaceBuilder("WithBL")
        .add_points([
            (0, 0, 100), (10, 0, 100),
            (0, 10, 100), (10, 10, 100),
        ])
        .add_breakline_coords(
            [(0, 5, 120), (10, 5, 120)],
            breakline_type=BreaklineType.STANDARD,
        )
        .build()
    )

    # Breakline 위 표고가 다름
    z_no_bl = surface_no_bl.elevation_at(5, 5)
    z_with_bl = surface_with_bl.elevation_at(5, 5)
    assert not math.isclose(z_no_bl, z_with_bl, abs_tol=1.0)


def test_breakline_proximity_no_elevation_effect():
    """Proximity Breakline은 표고 무시."""
    surface = (
        TinSurfaceBuilder()
        .add_grid(0, 10, 0, 10, nx=3, ny=3, elevation_func=lambda x, y: 100)
        .add_breakline_coords(
            [(0, 5, 200), (10, 5, 200)],   # 표고 200이지만 무시됨
            breakline_type=BreaklineType.PROXIMITY,
        )
        .build()
    )
    # 표고는 주변에서 보간 (100)
    assert math.isclose(surface.elevation_at(5, 5), 100.0, abs_tol=5.0)