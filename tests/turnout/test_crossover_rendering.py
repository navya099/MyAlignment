import json
import math
import re

from cadgeom import Point2d
import pytest

from myalignment.alignment import AlignmentBuilder
from myalignment.render.crossover_2d_renderer import Crossover2DRenderer
from myalignment.render.crossover_3d_renderer import Crossover3DRenderer
from myalignment.render.primitives import Primitive, PrimitiveType
from myalignment.render.primitives_3d import Point3D, PrimitiveType3D
from myalignment.render.scene import Scene
from myalignment.render.scene_3d import Scene3D
from myalignment.turnout.crossover_3d_preview import Crossover3DPreview
from myalignment.turnout.crossover_builder import CrossoverBuilder
from myalignment.turnout.crossover_calculator import CrossoverGeometryCalculator
from myalignment.turnout.crossover_preview import Crossover2DPreview
from myalignment.turnout.type import TurnoutSide, TurnoutType


def _layout(double=False, *, end=500):
    kind = TurnoutType("F12", 12, 17, 373)
    spacing = 4.3
    advance = 2 * kind.run + (spacing - 2 * kind.rise) / math.tan(kind.frog_angle)
    direction = 0.4
    cos, sin = math.cos(direction), math.sin(direction)

    def point(x, y):
        return 300000 + x * cos - y * sin, 400000 + x * sin + y * cos

    origin_a, origin_b = 1000, 1000 if double else 2000
    a = (
        AlignmentBuilder("A").with_pi_coords([point(0, 0), point(end, 0)])
        .with_start_station(origin_a).as_rail_alignment(gauge=1.52).build()
    )
    b = (
        AlignmentBuilder("B").with_pi_coords([point(0, spacing), point(end, spacing)])
        .with_start_station(origin_b).as_rail_alignment(gauge=1.52).build()
    )
    builder = (
        CrossoverBuilder("크로스오버").with_alignments("A", "B").with_turnout_type(kind)
        .at_stations(origin_a + 100, origin_b + 100 + advance)
        .with_sides(TurnoutSide.LEFT, TurnoutSide.RIGHT)
    )
    if double:
        builder.as_double()
    return a, b, builder.build(), point, advance


def test_single_crossover_uses_full_analytic_paths_and_raw_source_stations():
    a, b, crossover, point, advance = _layout(end=235)
    geometry = CrossoverGeometryCalculator.calculate(crossover, a, b, extension=80)
    assert geometry.is_valid, geometry.error_message
    assert geometry.diamond_center is None
    left, right = geometry.connecting_rails[0]
    centerline = geometry.sample_connections()[0]
    assert len(left) == len(right) == len(centerline)
    for lpt, rpt, center in zip(left, right, centerline):
        assert lpt.distance_to(rpt) == pytest.approx(1.52, abs=1e-9)
        assert ((lpt.x + rpt.x) / 2, (lpt.y + rpt.y) / 2) == pytest.approx((center.x, center.y), abs=1e-9)
    markers = {name: (location, station) for name, location, station in geometry.turnout_markers}
    for name, sta, xy in (
        ("T1-PS", 1100, point(100, 0)),
        ("T2-PS", 2100 + advance, point(100 + advance, 4.3)),
    ):
        location, station = markers[name]
        assert station == pytest.approx(sta)
        assert (location.x, location.y) == pytest.approx(xy, abs=1e-9)
    assert markers["T2-PF"][1] < markers["T2-PS"][1]
    assert geometry.main2_left_rail[-1].distance_to(b.point_at(b.end_station, -0.76)) < 1e-9
    plan = Crossover2DRenderer.render_2d(Scene(), geometry, crossover.name)
    assert all(p.style.layer != Crossover2DRenderer.DIAMOND_LAYER for p in plan.primitives)


def test_double_crossover_draws_four_rails_and_real_diamond():
    a, b, crossover, point, advance = _layout(double=True)
    geometry = CrossoverGeometryCalculator.calculate(crossover, a, b)
    assert geometry.is_valid, geometry.error_message
    assert len(geometry.connecting_rails) == 2
    assert len(geometry.turnout_markers) == 12
    assert geometry.diamond_center.distance_to(Point2d(*point(100 + advance / 2, 2.15))) < 1e-8
    assert (geometry.diamond_diagonal1, geometry.diamond_diagonal2) == tuple(
        connection.length for connection in geometry.connections
    )

    unannotated = Crossover2DRenderer.render_2d(
        Scene(), geometry, show_labels=False, show_markers=False, show_diamond=False,
    )
    assert len(unannotated.primitives) == 8
    assert {primitive.type for primitive in unannotated.primitives} == {PrimitiveType.POLYLINE}
    diamond = Crossover2DRenderer.render_2d(Scene(), geometry, show_labels=False, show_markers=False)
    symbol = [
        primitive for primitive in diamond.primitives
        if primitive.type is PrimitiveType.CIRCLE and primitive.style.layer == Crossover2DRenderer.DIAMOND_LAYER
    ]
    assert len(symbol) == 1
    assert symbol[0].points == (geometry.diamond_center,)


def test_preview_exports_dxf_and_appends_to_scene(tmp_path):
    a, b, crossover, _, _ = _layout(double=True)
    primitive = Primitive.line(Point2d(0, 0), Point2d(1, 1))
    original = Scene().add(primitive)
    output = tmp_path / "cross.dxf"
    plan = Crossover2DPreview.preview(a, b, crossover, output, scene=original)
    assert original.primitives == (primitive,)
    assert plan.primitives[0] is primitive
    content = output.read_text(encoding="cp949")
    for expected in (crossover.name, "DIAMOND", "T4-PS", Crossover2DRenderer.CONNECT_LAYER):
        assert expected in content
    assert content.rstrip().endswith("EOF")


def test_preview_surfaces_layout_errors():
    a, b, crossover, _, _ = _layout()
    with pytest.raises(ValueError, match="source alignments"):
        Crossover2DPreview.preview(b, a, crossover)
    invalid = (
        CrossoverBuilder("Bad").with_alignments("A", "B").with_turnout_type(crossover.turnout1.turnout_type)
        .at_stations(1100, 2100).with_sides(TurnoutSide.LEFT, TurnoutSide.RIGHT).build()
    )
    geometry = CrossoverGeometryCalculator.calculate(invalid, a, b)
    assert not geometry.is_valid
    with pytest.raises(ValueError, match="배치 불일치"):
        Crossover2DPreview.preview(a, b, invalid)


@pytest.mark.parametrize("double, rail_count", [(False, 6), (True, 8)])
def test_3d_rails_preserve_plan_coordinates_and_turnout_markers(double, rail_count):
    a, b, crossover, _, _ = _layout(double=double)
    geometry = CrossoverGeometryCalculator.calculate(crossover, a, b)
    assert geometry.gauge == 1.52
    plan = Crossover2DRenderer.render_2d(
        Scene(), geometry, show_labels=False, show_markers=False, show_diamond=False,
    )
    spatial = Crossover3DRenderer.render_3d(
        Scene3D(), geometry, elevation=55, gauge=1.52, show_ties=False,
    )

    rails = [item for item in spatial.primitives if item.type is PrimitiveType3D.POLYLINE]
    assert len(rails) == len(plan.primitives) == rail_count
    for rail, flat in zip(rails, plan.primitives):
        assert rail.points == tuple(Point3D(point.x, point.y, 55.15) for point in flat.points)

    def vertical_markers(layer):
        return [
            item.points for item in spatial.primitives
            if item.style.layer == layer and item.points[0].z != item.points[1].z
        ]

    assert vertical_markers(Crossover3DRenderer.MARKER_LAYER) == [
        (Point3D(point.x, point.y, 55), Point3D(point.x, point.y, 58))
        for _, point, station in geometry.turnout_markers if station is not None
    ]
    if double:
        center = geometry.diamond_center
        assert vertical_markers(Crossover3DRenderer.DIAMOND_LAYER) == [
            (Point3D(center.x, center.y, 55), Point3D(center.x, center.y, 58)),
        ]
    else:
        assert not any(item.style.layer == Crossover3DRenderer.DIAMOND_LAYER for item in spatial.primitives)


def test_3d_ties_follow_both_main_tracks_and_both_diagonals():
    a, b, crossover, _, _ = _layout(double=True)
    geometry = CrossoverGeometryCalculator.calculate(crossover, a, b, sample_step=3, extension=10)
    scene = Crossover3DRenderer.render_3d(
        Scene3D(), geometry, elevation=-10, rail_elevation=0.2, tie_spacing=0.8,
        show_markers=False, show_diamond=False,
    )
    ties = [item for item in scene.primitives if item.style.layer == Crossover3DRenderer.TIE_LAYER]
    main = (
        (geometry.main1_left_rail, geometry.main1_right_rail),
        (geometry.main2_left_rail, geometry.main2_right_rail),
    )
    midpoints = [(p.x / 2 + q.x / 2, p.y / 2 + q.y / 2) for p, q in (item.points for item in ties)]
    for left, right in (*main, *geometry.connecting_rails):
        start = (left[0].x / 2 + right[0].x / 2, left[0].y / 2 + right[0].y / 2)
        index = next(i for i, point in enumerate(midpoints) if math.dist(point, start) < 1e-8)
        p, q = ties[index].points
        assert p.distance_to(q) == pytest.approx(2.12)
        assert p.z == q.z == pytest.approx(-9.9)
        assert math.dist(midpoints[index], midpoints[index + 1]) == pytest.approx(0.8, abs=1e-8)
    assert {item.style.layer for item in scene.primitives} == {
        Crossover3DRenderer.MAIN1_LAYER, Crossover3DRenderer.MAIN2_LAYER,
        Crossover3DRenderer.CONNECT_LAYER, Crossover3DRenderer.TIE_LAYER,
    }


def test_3d_preview_exports_and_composes(tmp_path):
    a, b, crossover, _, _ = _layout(double=True)
    dxf, html = tmp_path / "crossover.dxf", tmp_path / "crossover.html"
    original = Crossover3DPreview.preview_full(a, b, crossover, dxf, html, elevation=50)
    composed = Crossover3DPreview.preview(a, b, crossover, 60, scene=original)
    assert composed.primitives[:len(original.primitives)] == original.primitives
    assert len(composed.primitives) == 2 * len(original.primitives)
    dxf_content = dxf.read_text(encoding="cp949")
    assert all(layer in dxf_content for layer in (Crossover3DRenderer.TIE_LAYER, Crossover3DRenderer.DIAMOND_LAYER))
    assert dxf_content.rstrip().endswith("EOF")
    html_content = html.read_text(encoding="utf-8")
    payload = re.search(r'id="scene-data">(.*?)</script>', html_content)
    assert crossover.name in html_content
    assert payload is not None
    exported = json.loads(payload[1])["primitives"]
    assert len(exported) == len(original.primitives)
    assert exported[0]["points"][0][2] == 50.15


def test_3d_renderer_rejects_mismatched_gauge_and_missing_plan_rails():
    a, b, crossover, _, _ = _layout()
    geometry = CrossoverGeometryCalculator.calculate(crossover, a, b)
    with pytest.raises(ValueError, match="gauge must match"):
        Crossover3DRenderer.render_3d(Scene3D(), geometry, gauge=1.435)
    with pytest.raises(ValueError, match="CrossoverGeometryCalculator"):
        Crossover3DRenderer.render_3d(Scene3D(), crossover.compute_geometry(a, b))
