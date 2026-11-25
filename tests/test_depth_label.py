from dataclasses import replace
import math

from cadgeom import Point2d
import pytest

from myalignment.export.dxf_writer import DxfWriter
from myalignment.profile import DepthLabel, DepthLabelStyle, ProfileBuilder
from myalignment.profile.label_component import ProfileLabelComponent
from myalignment.profile.station_label import StationElevationLabel
from myalignment.profile.view_style import ProfileViewStyle
from myalignment.render.depth_label_renderer import DepthLabelRenderer
from myalignment.render.primitives import PrimitiveType
from myalignment.render.profile_view_renderer import ProfileViewRenderer
from myalignment.render.scene import Scene
from myalignment.render.stagger_presets import StaggerConfigPresets
from myalignment.render.station_label_renderer import StationLabelRenderer


def test_depth_label_uses_named_profile_and_signed_average_grade():
    rising = ProfileBuilder("FG").add_tangent(0, 100, 100, 105).build()
    falling = ProfileBuilder("EG").add_tangent(0, 100, 95, 91).build()
    label = DepthLabel(10, 60)
    named = label.with_profile("EG")
    profiles = (rising, falling)

    assert label.evaluate(profiles)["Grade"] == "+5.00%"
    assert named.summary(profiles) == pytest.approx({
        "start_station": 10, "end_station": 60,
        "start_elevation": 94.6, "end_elevation": 92.6,
        "delta_elevation": -2, "distance": 50, "grade": -0.04,
    })
    assert named.evaluate(profiles) == {
        "Start Station": "10.00", "End Station": "60.00",
        "Start Elevation": "94.600", "End Elevation": "92.600",
        "Elevation Difference": "-2.000", "Grade": "-4.00%", "Distance": "50.00",
    }


@pytest.mark.parametrize("start,end", [(10, 10), (20, 10), (math.nan, 10), (10, math.inf)])
def test_depth_label_requires_finite_increasing_stations(start, end):
    with pytest.raises(ValueError, match="station"):
        DepthLabel(start, end)


def test_missing_or_out_of_range_profile_leaves_scene_unchanged():
    profile = ProfileBuilder("FG").add_tangent(0, 100, 100, 105).build()
    scene = Scene(metadata={"source": "profile"})
    for label, profiles in (
        (DepthLabel(0, 25), ()),
        (DepthLabel(0, 25, profile_name="missing"), (profile,)),
        (DepthLabel(50, 150), (profile,)),
    ):
        assert label.summary(profiles) == {}
        assert label.evaluate(profiles) == {}
        assert DepthLabelRenderer.render(scene, label, profiles) is scene


@pytest.mark.parametrize("style, expected", [
    (DepthLabelStyle.standard(), [
        "STA 10.00 → 60.00", "ΔE: +2.500 m", "Grade: +5.00%", "Dist: 50.00 m",
    ]),
    (DepthLabelStyle.minimal(), ["ΔE: +2.500 m"]),
    (DepthLabelStyle.slope_only(), ["Grade: +5.00%"]),
])
def test_depth_label_styles_render_requested_text(style, expected):
    profile = ProfileBuilder("FG").add_tangent(0, 100, 100, 105).build()
    label = DepthLabel(10, 60).with_style(style)
    scene = DepthLabelRenderer.render(Scene(), label, (profile,), 3)
    connector, start_marker, end_marker = scene.primitives[:3]
    assert connector.points == (Point2d(10, 301.5), Point2d(60, 309))
    assert start_marker.points == (Point2d(9, 301.5), Point2d(11, 301.5))
    assert end_marker.points == (Point2d(59, 309), Point2d(61, 309))
    texts = scene.primitives[3:]
    assert [primitive.text for primitive in texts] == expected
    assert texts[0].points == (Point2d(35, 305.25 + 3 * style.components[0].offset_y),)
    assert texts[0].text_height == pytest.approx(3 * style.components[0].text_height)


def test_depth_label_custom_components_and_visibility():
    component = ProfileLabelComponent(
        contents="Run <[Distance]>\\PGrade <[Grade]>", text_height=2,
        text_color=4, rotation=0.5, offset_x=2, offset_y=3,
    )
    hidden = ProfileLabelComponent(contents="Hidden", visible=False)
    style = DepthLabelStyle(components=(component, hidden), show_grade=False, show_arrow=False)
    profile = ProfileBuilder("FG").add_tangent(0, 100, 100, 105).build()
    scene = DepthLabelRenderer.render(Scene(), DepthLabel(10, 60, style), (profile,), 2)
    text, = scene.primitives
    assert text.type is PrimitiveType.TEXT
    assert text.text == "Run 50.00"
    assert text.points == (Point2d(37, 209.5),)
    assert (text.style.color, text.rotation, text.text_height) == (4, 0.5, 4)

    all_hidden = replace(style, show_distance=False)
    empty = Scene()
    assert DepthLabelRenderer.render(empty, DepthLabel(10, 60, all_hidden), (profile,)) is empty


def test_depth_labels_render_in_profile_view_and_export(tmp_path):
    profile = ProfileBuilder("FG").add_tangent(1000, 1100, 100, 105).build()
    scene = ProfileViewRenderer.render(
        (profile,), "Main", ProfileViewStyle(vertical_exaggeration=2),
        labels=(StationElevationLabel(1020),),
        depth_labels=(DepthLabel(1020, 1060), DepthLabel(1060, 1080)),
        stagger_config=StaggerConfigPresets.up_increment(),
    )

    depth = [primitive for primitive in scene.primitives if primitive.style.layer == DepthLabelRenderer.LAYER]
    assert len(depth) == 14
    assert depth[0].points == (Point2d(1020, 202), Point2d(1060, 206))
    assert "Grade: +5.00%" in [primitive.text for primitive in depth]
    assert any(item.style.layer == StationLabelRenderer.LAYER for item in scene.primitives)
    assert "stagger_levels" in scene.metadata
    dxf = tmp_path / "depth.dxf"
    DxfWriter(scene).write(dxf)
    contents = dxf.read_text(encoding="cp949")
    assert DepthLabelRenderer.LAYER in contents
    assert "Grade: +5.00%" in contents
    assert contents.rstrip().endswith("EOF")
