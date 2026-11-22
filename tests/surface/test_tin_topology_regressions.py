import pytest

from myalignment.surface.breakline import Breakline
from myalignment.surface.breakline_set import BreaklineSet
from myalignment.surface.breakline_type import BreaklineType
from myalignment.surface.tin_surface import TinSurface
from myalignment.surface.tin_surface_builder import TinSurfaceBuilder
from myalignment.surface.volume import cut_fill_between


_CORNERS = [(0, 0, 100), (10, 0, 100), (0, 10, 100), (10, 10, 100)]


def _edge_coordinates(surface):
    return {
        frozenset((surface.points[i].x, surface.points[i].y) for i in edge)
        for tri in surface.triangles
        for edge in ((tri.a, tri.b), (tri.b, tri.c), (tri.c, tri.a))
    }


def test_standard_breakline_forces_other_diagonal_into_mesh():
    original = TinSurface.from_points(_CORNERS)
    diagonals = (frozenset(((0, 0), (10, 10))), frozenset(((0, 10), (10, 0))))
    (missing,) = set(diagonals) - _edge_coordinates(original)
    line = Breakline.from_coords([(x, y, 100) for x, y in sorted(missing)], name="Diagonal")
    surface = TinSurface.from_points(_CORNERS, breaklines=BreaklineSet((line,)))
    assert missing in _edge_coordinates(surface)
    assert surface.area_2d == pytest.approx(100)


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="TinSurfaceBuilder inserts non-destructive breakline vertices")
def test_builder_non_destructive_breakline_leaves_tin_points_and_faces_intact():
    original = TinSurface.from_points(_CORNERS)
    surface = (
        TinSurfaceBuilder().add_points(_CORNERS)
        .add_breakline_coords(
            [(0, 5, 120), (10, 5, 120)], name="Reference",
            breakline_type=BreaklineType.NON_DESTRUCTIVE,
        ).build()
    )
    assert surface.points == original.points
    assert _edge_coordinates(surface) == _edge_coordinates(original)
    assert surface.elevation_at(5, 5) == pytest.approx(100)


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="CDT triangulates the input points before adding the new breakline vertices")
def test_new_breakline_vertices_participate_in_triangles_and_raise_nearby_ground():
    line = Breakline.from_coords([(0, 5, 120), (10, 5, 120)], name="Ridge")
    surface = TinSurface.from_points(_CORNERS, breaklines=BreaklineSet((line,)))
    assert frozenset(((0, 5), (10, 5))) in _edge_coordinates(surface)
    assert surface.elevation_at(5, 2.5) == pytest.approx(110)


@pytest.mark.parametrize("start", [10, 11])
def test_cut_fill_without_positive_area_overlap_is_zero(start):
    existing = TinSurface.from_points(_CORNERS)
    design = TinSurface.from_points([(start, 0, 95), (start + 10, 0, 95), (start, 10, 95)])
    assert cut_fill_between(existing, design) == (0, 0)


def test_direct_tin_preserves_topology_for_non_destructive_breakline():
    original = TinSurface.from_points(_CORNERS)
    line = Breakline.from_coords(
        [(0, 5, 120), (10, 5, 120)], name="Reference",
        breakline_type=BreaklineType.NON_DESTRUCTIVE,
    )
    surface = TinSurface.from_points(_CORNERS, breaklines=BreaklineSet((line,)))
    assert surface.points == original.points
    assert _edge_coordinates(surface) == _edge_coordinates(original)
    assert surface.elevation_at(5, 5) == pytest.approx(100)


def test_tin_slope_uses_world_elevation_plane_and_returns_zero_outside_mesh():
    surface = TinSurface.from_points([(10, 20, 100), (20, 20, 102), (10, 30, 103)])
    assert surface.slope_at(12, 22) == pytest.approx((.2, .3, 100 * (.2 ** 2 + .3 ** 2) ** .5))
    assert surface.elevation_at(12, 22) == pytest.approx(101)
    assert surface.slope_at(25, 25) == (0, 0, 0)
