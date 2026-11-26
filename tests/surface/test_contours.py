from dataclasses import replace
import json
import re

from cadgeom import Point2d
import pytest

from myalignment.export.dxf_writer import DxfWriter
from myalignment.render.contour_3d_renderer import Contour3DPreview
from myalignment.render.contour_renderer import ContourRenderer
from myalignment.render.primitives import PrimitiveType
from myalignment.render.scene import Scene
from myalignment.surface.boundary import Boundary
from myalignment.surface.boundary_type import BoundaryType
from myalignment.surface.contour_line import ContourLine, ContourSet
from myalignment.surface.contour_style import ContourStyle
from myalignment.surface.contour_type import ContourType
from myalignment.surface.tin_point import TinPoint
from myalignment.surface.tin_surface import TinSurface
from myalignment.surface.triangle import Triangle


def _ramp(x0=0, x1=10):
    return TinSurface.from_points([(x0, 0, x0), (x1, 0, x1), (x1, 10, x1), (x0, 10, x0)])


def _only(*levels):
    return ContourStyle(show_major=False, show_minor=False, user_contours=levels)


def test_major_minor_and_user_precedence_and_negative_levels():
    style = ContourStyle(major_interval=2, minor_interval=1, user_contours=(-1, 0, 0, 25))
    result = _ramp(-3, 5).generate_contours(style)
    assert [line.elevation for line in result] == list(range(-3, 6))
    assert [line.elevation for line in result.major_contours()] == [-2, 2, 4]
    assert [line.elevation for line in result.minor_contours()] == [-3, 1, 3, 5]
    for line in result:
        assert not line.closed and line.length == pytest.approx(10)
        assert all(p.x == pytest.approx(line.elevation) for p in line.points)
    assert result.by_elevation(0, tol=0)[0].contour_type is ContourType.USER


def test_decimal_spacing_and_flat_plateau_boundary_without_diagonal():
    vertices = [(0, 0, 0.1 + 0.2), (2, 0, 0.1 + 0.2), (2, 2, 0.1 + 0.2), (0, 2, 0.1 + 0.2)]
    surface = TinSurface.from_points(vertices)
    style = ContourStyle(major_interval=0.3, minor_interval=0.1)
    line, = surface.generate_contours(style)
    assert line.elevation == 0.3 and line.contour_type is ContourType.MAJOR
    assert line.closed and line.point_count == 4 and line.length == pytest.approx(8)


def test_hill_has_closed_ring_and_saddle_keeps_branches_separate():
    hill = TinSurface.from_points([(0, 0, 0), (4, 0, 0), (4, 4, 0), (0, 4, 0), (2, 2, 4)])
    ring, = hill.generate_contours(_only(2))
    assert ring.closed
    assert {(p.x, p.y) for p in ring.points} == {(1, 1), (3, 1), (3, 3), (1, 3)}
    assert ring.length == pytest.approx(8)
    saddle = TinSurface(
        points=tuple(TinPoint(*p) for p in [(0, 0, 0), (2, 0, 1), (0, 2, -1), (-2, 0, 1), (0, -2, -1)]),
        triangles=(Triangle(0, 1, 2), Triangle(0, 2, 3), Triangle(0, 3, 4), Triangle(0, 4, 1)),
    )
    paths = saddle.generate_contours(_only(0))
    assert len(paths) == 4
    assert all(not line.closed and line.point_count == 2 and Point2d(0, 0) in line.points for line in paths)


def test_hidden_boundary_keeps_gap_open():
    hole = Boundary.from_coords([(4, 4), (6, 4), (6, 6), (4, 6)], "Hole", BoundaryType.HIDE)
    surface = _ramp().with_boundary(hole)
    sections = surface.generate_contours(_only(5))
    assert sorted((min(p.y for p in line.points), max(p.y for p in line.points)) for line in sections) == [
        (0, 4), (6, 10),
    ]
    assert sections.total_length() == pytest.approx(8)


def test_horizontal_shared_edge_appears_once_and_isolated_vertices_are_skipped():
    surface = TinSurface(
        points=tuple(TinPoint(*p) for p in [(0, 0, 1), (2, 0, 1), (1, 1, 2), (1, -1, 0)]),
        triangles=(Triangle(0, 1, 2), Triangle(0, 1, 3)),
    )
    line, = surface.generate_contours(_only(0, 1, 2))
    assert line.elevation == 1 and not line.closed and line.length == pytest.approx(2)
    assert not len(TinSurface().generate_contours())


def test_labels_use_path_distance_and_outputs_share_appearance(tmp_path):
    line = ContourLine(5, ContourType.MAJOR, (Point2d(0, 0), Point2d(1, 0), Point2d(250, 0)))
    assert line.midpoint() == Point2d(125, 0)
    style = ContourStyle(label_interval_distance=100, elevation_colors=((5, 3),))
    contours = ContourSet((line,))
    scene = ContourRenderer.render(Scene(), contours, style)
    geometry, *labels = scene.primitives
    assert geometry.type is PrimitiveType.POLYLINE and geometry.style.color == 3
    assert [p.points[0].x for p in labels] == pytest.approx([75, 175])
    assert [p.text for p in labels] == ["5.00", "5.00"]
    assert not ContourRenderer.render(Scene(), contours, replace(style, show_major=False)).primitives

    plan = tmp_path / "plan.dxf"
    DxfWriter(scene).write(plan)
    assert "C-TOPO-CONT-TEXT" in plan.read_text("cp949")
    view, dxf = tmp_path / "view.html", tmp_path / "view.dxf"
    world = Contour3DPreview.preview(contours, view, dxf, style, z_scale=2)
    assert {p.z for p in world.primitives[0].points} == {10}
    assert world.primitives[0].style.color == 3
    html = view.read_text(encoding="utf-8")
    payload = json.loads(re.search(r'id="scene-data">([^<]+)</script>', html).group(1))
    assert payload["primitives"][0]["points"][0][2] == 10
    data = dxf.read_text("cp949").splitlines()
    assert ("30", "10") in set(zip(data[::2], data[1::2]))


def test_invalid_contour_styles_are_rejected():
    with pytest.raises(ValueError, match="minor_interval"):
        ContourStyle(minor_interval=0)
    with pytest.raises(ValueError, match="finite"):
        ContourStyle(user_contours=(float("nan"),))
    with pytest.raises(ValueError, match="ACI"):
        ContourStyle(elevation_colors=((5, 300),))


def test_disconnected_elevation_ranges_do_not_create_levels_in_between():
    surface = TinSurface(
        points=tuple(TinPoint(*p) for p in [
            (0, 0, 0), (2, 0, 0), (0, 2, 1),
            (10, 0, 1_000_000), (12, 0, 1_000_000), (10, 2, 1_000_001),
        ]),
        triangles=(Triangle(0, 1, 2), Triangle(3, 4, 5)),
    )
    lines = surface.generate_contours(ContourStyle(major_interval=2, minor_interval=0.5))
    assert [line.elevation for line in lines] == [0, 0.5, 1_000_000, 1_000_000.5]
