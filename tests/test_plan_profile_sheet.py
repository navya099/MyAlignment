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
        layout, axis, fg, eg, station_start=1020, station_end=1120, plan_rotation=math.pi / 2,
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
    scene = SheetComposer.compose(layout, _axis(), *_profiles(), render_plan_labels=False)
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
