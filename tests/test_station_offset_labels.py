from dataclasses import replace
import math
from xml.etree import ElementTree as ET

from cadgeom import Point2d
import pytest

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.alignment.label_component import AlignmentLabelComponent, AlignmentLabelComponentType
from myalignment.alignment.label_set import AlignmentLabelSet
from myalignment.alignment.station_offset_label import StationOffsetLabel
from myalignment.alignment.station_offset_label_style import StationOffsetLabelStyle
from myalignment.export.dxf_writer import DxfWriter
from myalignment.export.svg_writer import SvgWriter
from myalignment.render.alignment_renderer import AlignmentRenderer
from myalignment.render.composer import RenderOptions, SceneComposer
from myalignment.render.primitives import PrimitiveType
from myalignment.render.scene import Scene
from myalignment.render.station_offset_label_renderer import StationOffsetLabelRenderer


def _axis(name="Axis", y=0):
    return AlignmentBuilder(name).with_pi_coords([(0, y), (100, y)]).with_start_station(100).build()


def _texts(scene):
    return [p.text for p in scene.primitives if p.type is PrimitiveType.TEXT]


def _marker(scene):
    points = next(p.points for p in scene.primitives if p.style.layer == "C-ALIGN-SO-LABEL"
                  and p.type is PrimitiveType.LINE)
    a, b = points
    return (a.x + b.x) / 2, (a.y + b.y) / 2


def test_relative_and_fixed_positions_respond_differently_to_alignment_edit():
    axis = _axis()
    shifted = axis.offset_alignment(8)
    relative = StationOffsetLabel(relative_station=130, relative_offset=4)
    fixed = StationOffsetLabel(fixed_point=Point2d(30, -4))
    assert relative.evaluate(axis)["Offset Value"] == fixed.evaluate(axis)["Offset Value"] == "+4.000"

    renderer = StationOffsetLabelRenderer
    anchor = shifted.point_at(130, 4)
    assert _marker(renderer.render(Scene(), relative, shifted)) == pytest.approx((anchor.x, anchor.y))
    assert _marker(renderer.render(Scene(), fixed, shifted)) == (30, -4)
    assert fixed.evaluate(shifted)["Offset Value"] != "+4.000"
    assert relative.evaluate(shifted)["Offset Value"] == "+4.000"


def test_curve_station_equation_and_real_anchor_coordinates():
    axis = (
        AlignmentBuilder("Curve").with_pi_coords([(0, 0), (40, 0), (40, 40)])
        .with_radii([None, 15, None]).with_start_station(100).build()
        .add_station_equation(125, 300)
    )
    station, offset = 145, -2.5
    point = axis.point_at(station, offset)
    fields = StationOffsetLabel(fixed_point=point).evaluate(axis)
    assert fields["Raw Station"] == "145.00" and fields["Station Value"] == "320.00"
    assert fields["Offset Value"] == "-2.500"
    assert (fields["Easting"], fields["Northing"]) == (f"{point.x:.3f}", f"{point.y:.3f}")
    foot = axis.point_at(station)
    assert (fields["Alignment Easting"], fields["Alignment Northing"]) == (f"{foot.x:.3f}", f"{foot.y:.3f}")


def test_reference_alignment_projects_label_xy_and_reference_point_fields():
    axis = _axis().add_station_equation(110, 500)
    reference = (
        AlignmentBuilder("Cross").with_pi_coords([(25, -30), (25, 70)]).with_start_station(100).build()
        .add_station_equation(120, 200)
    )
    label = StationOffsetLabel(
        relative_station=130, relative_offset=4, reference_alignment_name="Cross", reference_point_name="CP1",
    )
    fields = label.evaluate(axis, reference, reference_point=Point2d(35, 6))
    assert fields["Ref Station"] == "206.00"
    assert fields["Ref Offset"] == "+5.000" and fields["Ref Alignment Name"] == "Cross"
    assert fields["Ref Point Station"] == "525.00"
    assert fields["Ref Point Name"] == "CP1" and fields["Ref Point Offset"] == "-6.000"


def test_style_inheritance_visibility_ticks_and_dxf_splits_text(tmp_path):
    components = (
        AlignmentLabelComponent(contents="STA <[Station Value]>\\Poff <[Offset Value]>",
                                offset_x=2, offset_y=3, rotation=math.pi / 4, layer="Custom"),
        AlignmentLabelComponent(AlignmentLabelComponentType.TICK, size=2, offset_y=0, layer="Mark"),
    )
    style = StationOffsetLabelStyle(components=components, show_station=False, show_marker=False)
    axis = _axis().with_label_set(AlignmentLabelSet().with_station_offset_style(style))
    label = StationOffsetLabel(relative_station=130, relative_offset=4)
    scene = StationOffsetLabelRenderer.render(Scene(), label, axis)
    assert _texts(scene) == ["off +4.000"]
    text, tick = scene.primitives
    assert text.points == (Point2d(32, -1),) and text.rotation == math.pi / 4
    assert (tick.points[0].x, tick.points[1].x) == pytest.approx((30, 30))
    assert (tick.points[0].y, tick.points[1].y) == pytest.approx((-6, -2))
    target = tmp_path / "labels.dxf"
    DxfWriter(scene).write(target)
    assert "off +4.000" in target.read_text("cp949")
    svg = ET.fromstring(SvgWriter(scene).to_string())
    assert [item.text for item in svg.iter("{http://www.w3.org/2000/svg}text")] == ["off +4.000"]


def test_plan_and_composer_accept_stored_transient_and_named_reference_labels():
    style = StationOffsetLabelStyle(components=(AlignmentLabelComponent(
        contents="<[Ref Alignment Name]> <[Ref Station]> <[Ref Point Name]>", layer="Named",
    ),))
    label = StationOffsetLabel(style, relative_station=130, relative_offset=-3,
                               reference_alignment_name="Ref", reference_point_name="CP")
    main = _axis().with_label_set(AlignmentLabelSet()).add_station_offset_label(label)
    ref = _axis("Ref", 10).with_label_set(AlignmentLabelSet())
    assert not _texts(AlignmentRenderer.render_plan(main))
    assert _texts(AlignmentRenderer.render_plan(main, render_labels=True, station_offset_labels=())) == []
    scene = SceneComposer.compose_multiple(
        (axis for axis in (main, ref)), RenderOptions(render_alignment_labels=True),
        reference_points={"CP": Point2d(30, 0)},
    )
    assert _texts(scene) == ["Ref 130.00 CP"]
    assert _texts(AlignmentRenderer.render_plan(main, render_labels=True)) == ["??? ??? ???"]
    assert _marker(scene) == (30, 3)


def test_invalid_labels_and_out_of_range_relative_annotations():
    axis = _axis()
    assert not StationOffsetLabelRenderer.render_multiple(
        Scene(), [StationOffsetLabel(relative_station=500)], axis,
    ).primitives
    assert not StationOffsetLabelRenderer.render_multiple(
        Scene(), [StationOffsetLabel(fixed_point=Point2d(0, 0))], replace(axis, entities=type(axis.entities)()),
    ).primitives
    with pytest.raises(ValueError, match="fixed_point"):
        StationOffsetLabel(StationOffsetLabelStyle(is_fixed_point=True))
    with pytest.raises(ValueError, match="marker_size"):
        StationOffsetLabelStyle(marker_size=0)
    with pytest.raises(ValueError, match="AlignmentLabelComponent"):
        StationOffsetLabelStyle(components=())
