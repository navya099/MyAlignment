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

def test_boundary_clips_faces_and_preserves_their_elevation_plane():
    import pytest

    original = TinSurface.from_points([(x, y, 10 + x + 2 * y) for x in (0, 10) for y in (0, 10)])
    bounded = original.with_boundary(Boundary.rectangle(0, 0, 2, 2, name="Small"))
    assert bounded.area_2d == pytest.approx(4)
    assert bounded.area_3d == pytest.approx(4 * math.sqrt(6))
    assert bounded.bbox == pytest.approx((0, 0, 2, 2))
    assert bounded.elevation_at(1, 1) == pytest.approx(13)
    assert bounded.triangle_at(3, 1) is None
    assert bounded.volume_above_elevation(5) == pytest.approx((32, 0))

    design = TinSurface.from_points([(-1, -1, 5), (3, -1, 5), (-1, 3, 5), (3, 3, 5), (1, 1, 5)])
    assert bounded.volume_between(design) == pytest.approx((32, 0))
    assert bounded.without_boundary("Small") == original


def test_boundary_subtracts_overlapping_holes_from_concave_show_region():
    import pytest

    surface = TinSurface.from_points([(x, y, 10) for x in (0, 10) for y in (0, 10)])
    show = Boundary.from_coords(
        [(0, 0), (8, 0), (8, 3), (3, 3), (3, 8), (0, 8)],
        "L", BoundaryType.SHOW,
    )
    hole1 = Boundary.rectangle(0.5, 0.5, 1.5, 1.5, "H1", BoundaryType.HIDE)
    hole2 = Boundary.rectangle(1, 1, 2, 2, "H2", BoundaryType.HIDE)
    clipped = surface.with_boundary(show).with_boundary(hole1).with_boundary(hole2)
    assert clipped.area_2d == pytest.approx(39 - 1.75)
    assert clipped.triangle_at(1.2, 1.2) is None
    assert clipped.triangle_at(5, 5) is None
    assert clipped.elevation_at(5, 2) == pytest.approx(10)
    assert clipped.without_boundary("H1").area_2d == pytest.approx(38)


def test_boundary_clips_vertical_wall_faces_with_the_adjacent_ground():
    from dataclasses import replace

    import pytest

    from myalignment.surface.breakline import Breakline
    from myalignment.surface.breakline_set import BreaklineSet
    from myalignment.surface.breakline_type import BreaklineType

    points = [(x, y, 90 if y == 0 else 100) for x in (0, 10) for y in (0, 10)]
    wall = Breakline.from_coords([(0, 5, 100), (10, 5, 100)], breakline_type=BreaklineType.WALL)
    original = TinSurface.from_points(points, breaklines=BreaklineSet((replace(wall, right_elevations=(90, 90)),)))
    clipped = original.with_boundary(Boundary.rectangle(3, 4, 7, 6))
    assert clipped.area_2d == pytest.approx(8)
    assert clipped.area_3d == pytest.approx(48)
    assert clipped.elevation_at(5, 4.5) == pytest.approx(90)
    assert clipped.elevation_at(5, 5.5) == pytest.approx(100)
    assert clipped.volume_above_elevation(95) == pytest.approx((20, 20))


def test_hide_boundary_touching_a_shared_edge_keeps_internal_edges_joined():
    from myalignment.surface.tin_point import TinPoint
    from myalignment.surface.triangle import Triangle

    surface = TinSurface(
        points=tuple(TinPoint(x, y, 0) for x, y in ((0, 0), (10, 0), (10, 10), (0, 10))),
        triangles=(Triangle(0, 1, 2), Triangle(0, 2, 3)),
    )
    hole = Boundary.from_coords([(5, 5), (6, 4), (7, 4)], boundary_type=BoundaryType.HIDE)
    clipped = surface.with_boundary(hole)

    assert clipped.area_2d == 99.5
    for i, j in clipped.boundary_edges:
        a, b = clipped.points[i], clipped.points[j]
        assert not (a.x == a.y and b.x == b.y)
