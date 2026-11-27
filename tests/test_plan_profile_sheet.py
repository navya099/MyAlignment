from dataclasses import replace
import importlib.util
import math
import shutil
from xml.etree import ElementTree as ET

from cadgeom import Point2d
import pytest

from myalignment.alignment import AlignmentBuilder
from myalignment.export.sheet_exporter import SheetExporter
from myalignment.profile import ProfileBuilder
from myalignment.profile.earthwork_band_style import EarthworkBandStyle
from myalignment.render.primitives import Primitive, PrimitiveType, Style
from myalignment.render.scene import Layer, Scene
from myalignment.sheet import PlanViewportTransform, ProfileViewportTransform, SheetComposer, SheetLayout, SheetSize, Viewport


def _axis(length=220, vertical=False):
    x, y = 450000, 4180000
    end = (x, y + length) if vertical else (x + length, y)
    return (
        AlignmentBuilder("Main").with_pi_coords([(x, y), end])
        .with_start_station(1000).build()
    )


def _profiles(start=1000, end=1220):
    fg = ProfileBuilder("Design").add_tangent(start, end, 100, 104).build()
    eg = ProfileBuilder("Ground").add_tangent(start, end, 102, 103).build()
    return fg, eg


def _items(scene, layer):
    return [p for p in scene.primitives if p.style.layer == layer]


def _xy(point):
    return point.x, point.y


def test_coordinate_transforms_are_reversible_with_independent_scales():
    viewport = Viewport("paper", 10, 20, 200, 100, 500)
    center = Point2d(450000, 4180000)
    plan = PlanViewportTransform(viewport, center, math.pi / 2)
    world = Point2d(center.x + 12, center.y + 30)
    paper = plan.to_paper(world)
    assert _xy(paper) == pytest.approx((170, 46))
    assert _xy(plan.to_world(paper)) == pytest.approx(_xy(world), abs=1e-9, rel=0)

    profile = ProfileViewportTransform(viewport, Point2d(30, 40), 1200, 91, 100)
    plotted = profile.to_paper(1210, 93)
    assert _xy(plotted) == pytest.approx((50, 60))
    assert profile.to_station_elevation(plotted) == pytest.approx((1210, 93))
    assert profile.project_rendered(Point2d(1210, 465)) == plotted
    assert profile.vertical_exaggeration == 5


def test_sheet_uses_real_scales_and_raw_station_window_at_project_coordinates():
    axis = _axis(vertical=True).add_station_equation(1030, 2000)
    fg, eg = _profiles()
    layout = SheetLayout.standard_a3(plan_scale=500, profile_scale=1000)
    scene = SheetComposer.compose(
        layout, axis, fg, eg, station_start=1020, station_end=1120,
        profile_vertical_scale=100, profile_datum=98,
    )
    plan, = _items(scene, "C-ALIGN-LINE")
    p0, p1 = plan.points
    assert p1.x - p0.x == pytest.approx(200)
    assert p1.y == pytest.approx(p0.y)
    sheet_transform = scene.metadata["plan_transform"]
    assert _xy(sheet_transform.to_world(p0)) == pytest.approx(_xy(axis.point_at(1020)), abs=1e-8, rel=0)
    assert _xy(sheet_transform.to_world(p1)) == pytest.approx(_xy(axis.point_at(1120)), abs=1e-8, rel=0)
    north = next(p for p in _items(scene, "A-NORTH") if p.type is PrimitiveType.LINE)
    assert north.points[0].x < north.points[1].x and north.points[0].y == pytest.approx(north.points[1].y)

    profile_transform = scene.metadata["profile_transform"]
    design, = _items(scene, "C-PROF-FG")
    first, last = design.points[0], design.points[-1]
    assert (last.x - first.x, last.y - first.y) == pytest.approx((100, 1000 / 55))
    assert profile_transform.to_station_elevation(first) == pytest.approx((1020, fg.elevation_at(1020)))
    assert profile_transform.to_station_elevation(last) == pytest.approx((1120, fg.elevation_at(1120)))
    assert _items(scene, "C-PROF-EG")
    assert {"1020.00", "2070.00", "2090.00"} <= {p.text for p in _items(scene, "A-PROFILE-AXES")}
    assert _items(scene, EarthworkBandStyle.standard().layer)
    scale = next(p for p in _items(scene, "A-SCALE-BAR") if p.type is PrimitiveType.LINE)
    assert scale.points[1].x - scale.points[0].x == pytest.approx(40)  # 20m at 1:500.


def test_plan_clips_crossing_drawings_arcs_fills_and_excludes_outside_text():
    axis = _axis()
    center = axis.point_at(1050)
    layout = SheetLayout.custom(SheetSize.A4, profile_ratio=0, plan_scale=1000)
    x, y = center.x, center.y
    line_style = Style(color=2, layer="Supplemental")
    overlay = Scene(layers=(Layer("Supplemental", color=2, linetype="DASHED"),)).add_all((
        Primitive.line(Point2d(x - 1000, y), Point2d(x + 1000, y), line_style),
        Primitive.circle(Point2d(x + layout.plan_viewport.width_mm / 2, y), 6, line_style),
        Primitive.arc(Point2d(x, y), 4, 10, 85, line_style),
        Primitive.polygon(
            (Point2d(x - 600, y - 5), Point2d(x + 600, y - 5), Point2d(x, y + 20)), line_style,
        ),
        Primitive.text(Point2d(x + 600, y), "Outside", 2, style=line_style),
        Primitive.text(Point2d(x, y + 10), "Inside", 2, style=line_style),
    ))
    scene = SheetComposer.compose(
        layout, axis, station_end=1100, plan_center=center, plan_scene=overlay,
        render_plan_labels=False,
    )
    left, bottom, right, top = layout.plan_viewport.bounds
    items = _items(scene, "Supplemental")
    assert all(left <= p.x <= right and bottom <= p.y <= top for prim in items for p in prim.points)
    assert items[0].points[0].x == pytest.approx(left)
    assert items[0].points[1].x == pytest.approx(right)
    assert any(p.type is PrimitiveType.POLYLINE for p in items)
    arc = next(p for p in items if p.type is PrimitiveType.ARC)
    assert (arc.radius, arc.start_angle, arc.end_angle) == (4, 10, 85)
    assert any(p.type is PrimitiveType.POLYGON for p in items)
    assert [p.text for p in items if p.type is PrimitiveType.TEXT] == ["Inside"]
    assert next(layer for layer in scene.layers if layer.name == "Supplemental").linetype == "DASHED"


def test_profile_clips_to_elevation_plot_instead_of_overprinting_bands():
    axis = _axis(length=100)
    fg = ProfileBuilder("Design").add_tangent(1000, 1100, 0, 200).build()
    eg = ProfileBuilder("Ground").add_tangent(1000, 1100, 1, 201).build()
    layout = SheetLayout.standard_a3(profile_scale=1000)
    scene = SheetComposer.compose(layout, axis, fg, eg, profile_datum=90, profile_vertical_scale=100)
    transform = scene.metadata["profile_transform"]
    points = [point for p in _items(scene, "C-PROF-FG") for point in p.points]
    low, high = transform.to_station_elevation(points[0]), transform.to_station_elevation(points[-1])
    assert low == pytest.approx((1045, 90))
    assert high[0] < 1100 and high[1] < 110
    assert min(point.y for point in points) >= transform.paper_origin.y
    earthwork = _items(scene, EarthworkBandStyle.standard().layer)
    assert max(point.y for p in earthwork for point in p.points) < transform.paper_origin.y


def test_series_covers_entire_alignment_without_changing_scale():
    axis = _axis(length=1000)
    fg, eg = _profiles(end=2000)
    layout = SheetLayout.standard_a3(drawing_number="R-01")
    single = SheetComposer.compose(layout, axis, fg, eg)
    scenes = SheetComposer.compose_series(layout, axis, fg, eg)
    ranges = [scene.metadata["station_range"] for scene in scenes]
    assert single.metadata["station_range"] == ranges[0]
    assert [(start, end) for start, end in ranges] == [(1000, 1383), (1383, 1766), (1766, 2000)]
    assert [scene.metadata["sheet_index"] for scene in scenes] == [1, 2, 3]
    assert all(scene.metadata["profile_transform"].viewport.scale == 1000 for scene in scenes)
    assert "R-01-02" in [item.text for item in _items(scenes[1], "A-TITLE-BLOCK")]
    with pytest.raises(ValueError, match="exceeds the profile viewport"):
        SheetComposer.compose(layout, axis, fg, eg, station_end=2000)


@pytest.mark.parametrize(("end", "expected"), [
    (2600, ((1200, 1900), (1900, 2600))),
    (2700, ((1200, 1900), (1900, 2600), (2600, 2700))),
])
def test_series_honors_requested_700_m_span_at_fixed_scales(end, expected):
    axis = _axis(length=2000).add_station_equation(1500, 3000)
    layout = SheetLayout.standard_a1(plan_scale=1000, profile_scale=1000)
    fg, eg = _profiles(end=3000)
    scenes = SheetComposer.compose_series(
        layout, axis, fg, eg, station_start=1200, station_end=end, station_span=700,
        plan_tangent="start", render_plan_labels=False,
    )
    assert tuple(scene.metadata["station_range"] for scene in scenes) == expected
    assert [scene.metadata["sheet_count"] for scene in scenes] == [len(expected)] * len(expected)
    for scene, (left, right) in zip(scenes, expected, strict=True):
        plan, = _items(scene, "C-ALIGN-LINE")
        assert plan.points[1].x - plan.points[0].x == pytest.approx(right - left)
        profile = scene.metadata["profile_transform"]
        assert profile.start_station == left and profile.viewport.scale == 1000


def test_series_rejects_span_larger_than_viewport_capacity_but_accepts_a_short_run():
    axis = _axis(length=1000)
    layout = SheetLayout.standard_a3()
    with pytest.raises(ValueError, match="requires 700 m per sheet.*capacity is 383 m"):
        SheetComposer.compose_series(layout, axis, station_span=700)
    scene, = SheetComposer.compose_series(layout, axis, station_end=1220, station_span=700)
    assert scene.metadata["station_range"] == (1000, 1220)


@pytest.mark.parametrize("span", [0, -1, math.inf, math.nan])
def test_series_rejects_invalid_station_span(span):
    with pytest.raises(ValueError, match="station_span"):
        SheetComposer.compose_series(SheetLayout.standard_a3(), _axis(), station_span=span)


@pytest.mark.parametrize("plan_tangent", ["midpoint", "start"])
def test_plan_series_uses_the_selected_tangent_of_each_sheet(plan_tangent):
    axis = (
        AlignmentBuilder("Curve").with_pi_coords([(0, 0), (0, 150), (350, 150)])
        .with_radii([None, 60, None]).with_start_station(1000).build()
    )
    layout = SheetLayout.custom(SheetSize.A4, profile_ratio=0, plan_scale=1000)
    first, second = SheetComposer.compose_series(
        layout, axis, plan_tangent=plan_tangent, render_plan_labels=False,
    )
    for scene in (first, second):
        start, end = scene.metadata["station_range"]
        middle = (start + end) / 2
        transform = scene.metadata["plan_transform"]
        reference = middle if plan_tangent == "midpoint" else start
        assert transform.rotation == pytest.approx(axis.tangent_at(reference))
        p0, p1 = (transform.to_paper(axis.point_at(station)) for station in (middle - 1, middle + 1))
        assert p1.x > p0.x
        if plan_tangent == "midpoint":
            assert p1.y == pytest.approx(p0.y, abs=1e-8)
    first_rotation = first.metadata["plan_transform"].rotation
    if plan_tangent == "start":
        assert first_rotation == pytest.approx(math.pi / 2)
    else:
        assert 0 < first_rotation < math.pi / 2
    assert second.metadata["plan_transform"].rotation == pytest.approx(0)


@pytest.mark.parametrize(("rotation", "delta"), [(None, (50, 0)), (0, (0, 50))])
def test_start_tangent_uses_outgoing_element_and_respects_manual_rotation(rotation, delta):
    axis = AlignmentBuilder("Corner").with_pi_coords([(0, 0), (100, 0), (100, 100)]).build()
    layout = SheetLayout.standard_a3()
    scene = SheetComposer.compose(
        layout, axis, station_start=100, station_end=150, plan_tangent="start",
        plan_rotation=rotation, render_plan_labels=False,
    )
    line, = _items(scene, "C-ALIGN-LINE")
    start, end = line.points
    assert (end.x - start.x, end.y - start.y) == pytest.approx(delta)


@pytest.mark.parametrize(("rotation", "expected"), [(None, math.pi / 2), (0, 0), (math.pi / 4, math.pi / 4)])
def test_plan_center_and_explicit_rotation_apply_to_world_geometry_and_text(rotation, expected):
    axis = _axis(length=60, vertical=True)
    layout = SheetLayout.standard_a3()
    center = axis.point_at(1030)
    style = Style(layer="Supplemental")
    overlay = Scene().add_all((
        Primitive.text(center, "World text", 2, rotation=math.pi / 4, style=style),
        Primitive.arc(center, 4, 10, 85, style),
    ))
    scene = SheetComposer.compose(
        layout, axis, plan_center=center, plan_rotation=rotation, plan_scene=overlay,
        render_plan_labels=False,
    )
    transform = scene.metadata["plan_transform"]
    p0, p1 = _items(scene, "C-ALIGN-LINE")[0].points
    assert (p1.x - p0.x, p1.y - p0.y) == pytest.approx((60 * math.sin(expected), 60 * math.cos(expected)))
    text, arc = _items(scene, "Supplemental")
    assert text.points == arc.points == (transform.sheet_center,)
    assert text.rotation == pytest.approx(math.pi / 4 - expected)
    assert arc.start_angle == pytest.approx(10 - math.degrees(expected))
    assert arc.end_angle == pytest.approx(85 - math.degrees(expected))


def test_invalid_frames_and_scale_are_rejected():
    with pytest.raises(ValueError, match="must not overlap"):
        layout = SheetLayout.standard_a1()
        replace(layout, profile_viewport=layout.plan_viewport)
    with pytest.raises(ValueError, match="fit inside"):
        replace(layout, plan_viewport=replace(layout.plan_viewport, y_mm=0))
    with pytest.raises(ValueError, match="scale"):
        Viewport("bad", 0, 0, 10, 10, scale=0)


def test_export_retains_paper_origin_dimensions_and_dxf_geometry(tmp_path):
    layout = SheetLayout.standard_a3()
    scene = SheetComposer.compose(layout, _axis(vertical=True), *_profiles(), render_plan_labels=False)
    svg, dxf = tmp_path / "Sheet.svg", tmp_path / "Sheet.dxf"
    SheetExporter.export_svg(scene, svg)
    SheetExporter.export_dxf(scene, dxf)
    root = ET.parse(svg).getroot()
    assert (root.get("width"), root.get("height"), root.get("viewBox")) == ("420mm", "297mm", "0 0 420 297")
    ns = {"s": "http://www.w3.org/2000/svg"}
    model_line, = _items(scene, "C-ALIGN-LINE")
    svg_line, = root.findall("s:g[@data-layer='C-ALIGN-LINE']/s:line", ns)
    assert float(svg_line.get("x1")) == pytest.approx(model_line.points[0].x)
    assert float(svg_line.get("y1")) == pytest.approx(297 - model_line.points[0].y)
    assert float(svg_line.get("x2")) - float(svg_line.get("x1")) == pytest.approx(220)
    assert float(svg_line.get("y2")) == pytest.approx(float(svg_line.get("y1")))
    assert "C-ALIGN-LINE" in dxf.read_text("cp949")


@pytest.mark.skipif(importlib.util.find_spec("cairosvg") is None and shutil.which("inkscape") is None,
                    reason="PDF backend is optional")
def test_export_pdf(tmp_path):
    scene = SheetComposer.compose(SheetLayout.standard_a3(), _axis(), *_profiles())
    pdf = tmp_path / "Sheet.pdf"
    SheetExporter.export_pdf(scene, pdf)
    assert pdf.read_bytes().startswith(b"%PDF")


def test_curved_plan_uses_exact_station_limits_and_renders_corridor_and_terrain():
    from myalignment.assembly import AssemblyBuilder
    from myalignment.assembly.subassemblies.basic_lane import BasicLane
    from myalignment.corridor.corridor_builder import CorridorBuilder
    from myalignment.surface.tin_surface import TinSurface

    axis = (
        AlignmentBuilder("Curve")
        .with_pi_coords([(0, 0), (100, 0), (100, 100)])
        .with_radii([None, 50, None]).build()
    )
    corridor = (
        CorridorBuilder().add_baseline_from_alignment(axis)
        .add_region("Right lane", axis.start_station, axis.end_station, AssemblyBuilder().add_right(BasicLane()).build())
        .build().extract_feature_lines(alignments={axis.name: axis})
    )
    terrain = TinSurface.from_points([(-20, -50, 0), (200, -50, 10), (200, 150, 10), (-20, 150, 0)])
    layout = SheetLayout.custom(SheetSize.A3, profile_ratio=0)
    scene = SheetComposer.compose(
        layout, axis, surface=terrain, corridor=corridor, station_start=65, station_end=105,
        plan_center=axis.point_at(85), render_plan_labels=False,
    )
    curve, = _items(scene, "C-ALIGN-CURVE")
    transform = scene.metadata["plan_transform"]
    assert _xy(transform.to_world(curve.points[0])) == pytest.approx(_xy(axis.point_at(65)))
    assert _xy(transform.to_world(curve.points[-1])) == pytest.approx(_xy(axis.point_at(105)))
    assert _items(scene, "C-TOPO-MAJOR-CONT")
    assert _items(scene, "C-CORRIDOR-FL")


def test_short_straight_plan_and_profile_align_horizontally_at_equal_scale():
    axis = _axis(length=100)
    layout = SheetLayout.standard_a3()
    scene = SheetComposer.compose(layout, axis, *_profiles(end=1100), render_plan_labels=False)
    plan = scene.metadata["plan_transform"]
    profile = scene.metadata["profile_transform"]
    for station in (1000, 1050, 1100):
        assert plan.to_paper(axis.point_at(station)).x == pytest.approx(profile.to_paper(station, 103).x)
