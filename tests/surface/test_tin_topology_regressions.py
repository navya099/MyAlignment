import pytest

from myalignment.surface import tin_surface
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


def test_builder_forces_edges_and_interpolates_standard_breakline_at_existing_vertices():
    points = _CORNERS + [(5, 5, 100)]
    line = Breakline.from_coords([(0, 0, 110), (10, 10, 130)], name="Grade")
    direct = TinSurface.from_points(points, breaklines=BreaklineSet((line,)))
    built = TinSurfaceBuilder().add_points(points).add_breakline(line).build()

    assert built.points == direct.points
    assert built.triangles == direct.triangles
    assert built.points[4].z == pytest.approx(120)
    assert frozenset(((0, 0), (5, 5))) in _edge_coordinates(built)
    assert frozenset(((5, 5), (10, 10))) in _edge_coordinates(built)

    removed = built.without_breakline("Grade")
    assert removed.points == TinSurface.from_points(points).points
    assert removed.elevation_at(5, 5) == pytest.approx(100)


def test_proximity_breakline_new_vertices_use_existing_elevation():
    points = [(x, y, 100 + x + y) for x, y, _ in _CORNERS]
    surface = (
        TinSurfaceBuilder().add_points(points)
        .add_breakline_coords(
            [(0, 5, 900), (10, 5, 900)], breakline_type=BreaklineType.PROXIMITY,
        )
        .build()
    )
    assert frozenset(((0, 5), (10, 5))) in _edge_coordinates(surface)
    assert surface.elevation_at(5, 2.5) == pytest.approx(107.5)


def test_non_destructive_breakline_keeps_rectangular_grid_mesh():
    builder = TinSurfaceBuilder().add_grid(0, 10, 0, 20, 3, 5, lambda x, y: x + y)
    original = builder.build()
    line = Breakline.from_coords(
        [(0, 5, 999), (10, 5, 999)], name="Reference",
        breakline_type=BreaklineType.NON_DESTRUCTIVE,
    )

    assert original.area_2d == pytest.approx(200)
    for surface in (builder.add_breakline(line).build(), original.with_breakline(line)):
        assert surface.points == original.points
        assert surface.triangles == original.triangles
        assert surface.elevation_at(4, 9) == pytest.approx(13)
        assert surface.without_breakline("Reference").triangles == original.triangles


def test_fallback_triangulation_keeps_hull_edge_near_an_interior_vertex(monkeypatch):
    monkeypatch.setattr(tin_surface, "_HAS_SCIPY", False)
    points = [(0, 0, 0), (10, 0, 0), (5, .001, 0), (5, 10, 0)]
    line = Breakline.from_coords(points[:2])
    surface = TinSurface.from_points(points, breaklines=BreaklineSet((line,)))
    assert frozenset(((0, 0), (10, 0))) in _edge_coordinates(surface)
    assert surface.area_2d == pytest.approx(50)


def test_fallback_mesh_keeps_interior_vertex_at_small_coordinate_scale(monkeypatch):
    monkeypatch.setattr(tin_surface, "_HAS_SCIPY", False)
    step = 0.001
    points = [(0, 0, 0), (step, 0, 0), (0, step, 0), (step, step, 0), (step / 2, step / 2, 1)]
    surface = TinSurface.from_points(points)
    assert len(surface.triangles) == 4
    assert all(4 in (tri.a, tri.b, tri.c) for tri in surface.triangles)


def test_crossing_breaklines_require_a_shared_mesh_vertex():
    lines = BreaklineSet((
        Breakline.from_coords([_CORNERS[0], _CORNERS[3]]),
        Breakline.from_coords([_CORNERS[1], _CORNERS[2]]),
    ))
    with pytest.raises(ValueError, match="공유 정점"):
        TinSurface.from_points(_CORNERS, breaklines=lines)

    surface = TinSurface.from_points(_CORNERS + [(5, 5, 100)], breaklines=lines)
    assert all(frozenset(((x, y), (5, 5))) in _edge_coordinates(surface) for x, y, _ in _CORNERS)
    assert surface.area_2d == pytest.approx(100)
