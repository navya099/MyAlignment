from dataclasses import replace
import math

import pytest

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.assembly.subassemblies.side_slope import SideSlope
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.corridor.slope_pattern_generator import SlopePatternGenerator
from myalignment.corridor.slope_pattern_style import SlopePatternStyle
from myalignment.corridor.slope_pattern_type import SlopePatternType
from myalignment.export.dxf_writer import DxfWriter
from myalignment.profile.profile import ProfileBuilder
from myalignment.render.primitives import PrimitiveType
from myalignment.render.scene import Scene
from myalignment.render.section_view_renderer import SectionViewRenderer
from myalignment.render.slope_pattern_2d_renderer import SlopePattern2DRenderer
from myalignment.render.slope_pattern_3d_renderer import SlopePattern3DPreview
from myalignment.render.slope_pattern_section_renderer import SlopePatternSectionRenderer
from myalignment.section.section_view_builder import SectionViewBuilder
from myalignment.section.section_view_style import SectionViewStyle, section_projection


def _assembly(height=6):
    return (AssemblyBuilder().add_both(lambda side: BasicLane(width=4, slope=0, side=side))
            .add_both(lambda side: SideSlope(height=height, side=side)).build())


def _fixture():
    grade = ProfileBuilder("Grade").add_tangent(100, 140, 20, 24).build()
    axis = (AlignmentBuilder("Axis").with_pi_coords([(-100, 50), (-100, 90)])
            .with_start_station(100).with_profile(grade).build())
    corridor = (CorridorBuilder().add_baseline_from_alignment(axis, grade)
                .add_region("First", 100, 110, _assembly(), frequency=5)
                .add_region("Second", 120, 140, _assembly(), frequency=10).build())
    return axis, corridor


def test_hatch_uses_world_coordinates_and_longitudinal_grade():
    axis, corridor = _fixture()
    style = replace(SlopePatternStyle.hatch_style(), spacing_horizontal=2, spacing_vertical=1, pattern_size=2)
    collection = corridor.generate_slope_patterns(style, alignments={axis.name: axis})
    left, right = collection.at_station(100)
    assert {left.side, right.side} == {"left", "right"}
    right = next(pattern for pattern in (left, right) if pattern.side == "right")
    assert (right.start_offset, right.end_offset) == (4, 13)
    assert tuple((p.x, p.y, p.z) for p in (right.start_point, right.end_point)) == (
        (-96, 50, 20), (-87, 50, 14),
    )
    assert right.slope_percent == pytest.approx(-100 / 1.5)
    a, b = right.elements[0].points
    assert (a.x, a.y, a.z) == pytest.approx((-96, 50, 20))
    assert (b.x, b.y, b.z) == pytest.approx((-95, 52, 20.2 - 6 / 9))
    assert len(collection.by_region("First")) == 6
    assert not collection.at_station(115)
    assert all(p.y <= 60 for pattern in collection.by_region("First")
               for element in pattern.elements for p in element.points)


def test_grid_marks_exact_elevation_increments_and_preserves_region_gap():
    axis, corridor = _fixture()
    style = replace(SlopePatternStyle.grid_style(), spacing_horizontal=4, spacing_vertical=2)
    collection = SlopePatternGenerator.generate_for_corridor(corridor, style, alignments={axis.name: axis})
    first = collection.by_region("First")
    assert sorted({pattern.station for pattern in first}) == [100, 104, 108, 110]
    sample = first[0]
    assert sample.elements[0].points == (sample.start_point, sample.end_point)
    connecting = sample.elements[1:]
    assert [line.points[0].z for line in connecting] == pytest.approx([20, 18, 16, 14])
    assert [line.points[1].y for line in connecting] == pytest.approx([54] * 4)
    assert [p.element_count for p in collection.at_station(110)] == [1, 1]


def test_steps_and_berms_use_configured_dimensions():
    axis, corridor = _fixture()
    steps = replace(SlopePatternStyle.steps_style(), step_height=2, step_width=2, include_berm=False)
    pattern = corridor.generate_slope_patterns(steps, alignments={axis.name: axis}).at_station(105)[0]
    stairs, = pattern.elements
    assert stairs.element_type == "polyline"
    assert (stairs.points[0], stairs.points[-1]) == (pattern.start_point, pattern.end_point)
    assert len(stairs.points) == 11
    for a, b in zip(stairs.points, stairs.points[1:]):
        assert (a.x == b.x and a.y == b.y) or a.z == b.z
        assert abs(a.z - b.z) <= 2 and math.hypot(a.x - b.x, a.y - b.y) <= 2

    with_berms = replace(steps, include_berm=True, berm_width=4)
    pattern = corridor.generate_slope_patterns(with_berms, alignments={axis.name: axis}).at_station(105)[0]
    shelf, *_ = pattern.elements
    assert shelf.points[0].z == shelf.points[1].z
    assert shelf.points[0].distance_to(shelf.points[1]) == pytest.approx(4)

    berms = replace(SlopePatternStyle.berms_style(), berm_interval=2, berm_width=2)
    pattern = corridor.generate_slope_patterns(berms, alignments={axis.name: axis}).at_station(100)[0]
    assert [element.points[0].z for element in pattern.elements] == pytest.approx([18, 16])
    for element in pattern.elements:
        a, b = element.points
        assert a.z == b.z and a.distance_to(b) == pytest.approx(2)


def test_stakes_render_in_plan_and_section_and_export(tmp_path):
    axis, corridor = _fixture()
    style = replace(SlopePatternStyle.stakes_style(), stake_spacing=4, stake_length=4,
                    show_label=True, lineweight=0.5, layer="SLOPE-STAKES")
    all_patterns = corridor.generate_slope_patterns(style, alignments={axis.name: axis})
    patterns = all_patterns.at_station(105)
    for pat in patterns:
        bases = [elem.points[0] for elem in pat.elements]
        assert bases[-1] == pat.end_point
        assert bases[0].distance_to(bases[1]) == pytest.approx(4)
        assert all(top.z - bottom.z == pytest.approx(4) for bottom, top in (elem.points for elem in pat.elements))

    plan = SlopePattern2DRenderer.render(Scene(), patterns)
    assert sum(p.type is PrimitiveType.CIRCLE for p in plan.primitives) == sum(p.element_count for p in patterns)
    assert any(p.text == "Stakes · -66.7%" for p in plan.primitives)
    assert all(p.style.lineweight == 0.5 for p in plan.primitives)
    dxf = tmp_path / "plan.dxf"
    DxfWriter(plan).write(dxf)
    assert "SLOPE-STAKES" in dxf.read_text("cp949")

    data = SectionViewBuilder.build_data(corridor, axis, 105)
    view = SectionViewStyle(vertical_exaggeration=2)
    scene = SectionViewRenderer.render(Scene(), data, view, slope_patterns=all_patterns)
    layer = [p for p in scene.primitives if p.style.layer == style.layer and p.type is PrimitiveType.LINE]
    assert len(layer) == sum(p.element_count for p in patterns)
    assert all(p.points[0].x == pytest.approx(p.points[1].x) for p in layer)
    assert all(p.points[1].y <= view.height - view.margin_top for p in layer)
    *_, plot = section_projection(data, view)
    overlay = SlopePatternSectionRenderer.render_patterns(Scene(), patterns, data, view)
    first = overlay.primitives[0].points[0]
    assert first == plot(patterns[0].start_offset, patterns[0].start_point.z)

    html, dxf3 = tmp_path / "view.html", tmp_path / "world.dxf"
    rendered = SlopePattern3DPreview.preview(all_patterns, html, dxf3, z_scale=2)
    assert len(rendered.primitives) == all_patterns.total_elements()
    assert rendered.primitives[0].points[0].z == pytest.approx(40)
    assert "SLOPE-STAKES" in html.read_text(encoding="utf-8")
    assert "SLOPE-STAKES" in dxf3.read_text("cp949")


def test_slope_sampling_on_curved_and_overlapping_baselines():
    profile = ProfileBuilder("External").add_tangent(100, 190, 10, 10).build()
    a = (AlignmentBuilder("A").with_pi_coords([(0, 0), (50, 0), (50, 50)])
         .with_radii([None, 20, None]).with_start_station(100).build())
    b = (AlignmentBuilder("B").with_pi_coords([(0, 100), (90, 100)])
         .with_start_station(100).build())
    corridor = (CorridorBuilder().add_baseline_from_alignment(a, profile, end_station=180)
                .add_baseline_from_alignment(b)
                .add_region("Curve", 140, 150, _assembly(), baseline_name="A")
                .add_region("Parallel", 140, 150, _assembly(), baseline_name="B").build())
    patterns = corridor.generate_slope_patterns(
        alignments={"A": a}, profiles={profile.name: profile}, baseline_name="A", sample_frequency=5,
    )
    pattern = patterns.at_station(145, baseline_name="A", region_name="Curve")[0]
    assert pattern.start_point.z == 10
    expected = a.point_at(145, pattern.start_offset)
    assert (pattern.start_point.x, pattern.start_point.y) == pytest.approx((expected.x, expected.y))
    assert not patterns.at_station(145, baseline_name="B")


def test_none_empty_and_invalid_styles():
    axis, corridor = _fixture()
    style = SlopePatternStyle(pattern_type=SlopePatternType.NONE)
    assert not len(corridor.generate_slope_patterns(style, alignments={}))
    assert not len(CorridorBuilder().build().generate_slope_patterns(alignments={}))
    with pytest.raises(ValueError, match="step_height"):
        replace(SlopePatternStyle.steps_style(), step_height=0)
    with pytest.raises(ValueError, match="spacing_vertical"):
        replace(SlopePatternStyle.grid_style(), spacing_vertical=math.nan)
    with pytest.raises(ValueError, match="sample_frequency"):
        corridor.generate_slope_patterns(alignments={axis.name: axis}, sample_frequency=-1)
