from dataclasses import replace
import math

import pytest
from cadgeom import Point2d

from myalignment.export.dxf_writer import DxfWriter
from myalignment.profile.label_component import LabelComponentType, ProfileLabelComponent
from myalignment.profile.label_set import ProfileLabelSet
from myalignment.profile.label_style import ProfileLabelStyle
from myalignment.profile.label_type import ProfileLabelType
from myalignment.profile.profile import ProfileBuilder
from myalignment.profile.station_label import StationElevationLabel
from myalignment.profile.view_style import ProfileViewStyle
from myalignment.render.primitives import PrimitiveType
from myalignment.render.profile_label_renderer import ProfileLabelRenderer
from myalignment.render.profile_view_renderer import ProfileViewRenderer
from myalignment.render.scene import Scene


def test_tangent_grade_breaks_line_labels_and_min_spacing():
    profile = (
        ProfileBuilder().add_tangent(100, 120, 10, 11)
        .add_tangent(120, 122, 11, 11.2)
        .add_tangent(122, 140, 11.2, 13)
        .add_tangent(140, 160, 13, 12).build()
    )
    style = replace(ProfileLabelStyle.gradient_break_style(), min_spacing=25)
    profile = profile.with_label_style(ProfileLabelType.GRADIENT_BREAK, style)
    profile = profile.with_label_style(ProfileLabelType.LINE, ProfileLabelStyle.line_style())
    scene = ProfileLabelRenderer.render(Scene(), profile, 2)
    texts = [p.text for p in scene.primitives if p.type is PrimitiveType.TEXT]
    assert "G: 5.00% → 10.00%" in texts
    assert "G: 10.00% → -5.00%" not in texts
    assert texts.count("PVI") == 2
    assert "G: 5.00%" in texts and "L: 20.00" in texts
    grade = next(p for p in scene.primitives if p.text == "G: 5.00%")
    assert grade.points[0].x == 110


@pytest.mark.parametrize(
    "profile, marker, expected_station, expected_elevation",
    [
        (
            ProfileBuilder().add_symmetric_parabola(100, 50, 0.03, -0.01, 100).build(),
            "HIGH POINT", 125, 49.625,
        ),
        (
            ProfileBuilder().add_asymmetric_parabola(100, 50, -0.01, 0.03, 90, 30).build(),
            "LOW POINT", 100, 50.45,
        ),
    ],
)
def test_curve_extrema_and_pvi_use_distinct_exact_model_values(profile, marker, expected_station, expected_elevation):
    scene = ProfileLabelRenderer.render(Scene(), profile, 1)
    texts = [p.text for p in scene.primitives]
    label = next(p for p in scene.primitives if p.text == marker)
    assert label.points[0].x == pytest.approx(expected_station)
    assert f"EL {expected_elevation:.3f}" in texts
    assert "PVI" in texts and "EL 50.000" in texts


def test_monotonic_curve_has_k_and_length_without_false_extremum():
    profile = ProfileBuilder().add_symmetric_parabola(100, 50, 0.03, 0.01, 100).build()
    styled = profile.with_label_style(ProfileLabelType.CURVE, ProfileLabelStyle.curve_style())
    scene = ProfileLabelRenderer.render(Scene(), styled)
    texts = [p.text for p in scene.primitives]
    assert "K: 50.00" in texts and "L: 100.00" in texts
    assert "HIGH POINT" not in texts and "LOW POINT" not in texts
    assert profile.label_set.get_style(ProfileLabelType.CURVE) is None
    with pytest.raises(TypeError):
        profile.label_set.styles[ProfileLabelType.CURVE] = ProfileLabelStyle.curve_style()
    assert ProfileLabelSet.minimal().active_types() == (ProfileLabelType.PVI,)


def test_profile_view_label_components_and_dxf_export(tmp_path):
    profile = ProfileBuilder().add_tangent(0, 100, 10, 20).build()
    label_style = ProfileLabelStyle(
        label_type=ProfileLabelType.LINE,
        components=(
            ProfileLabelComponent(contents=r"구배 <[Grade]>\P길이 <[Length]>", layer="Grades"),
            ProfileLabelComponent(component_type=LabelComponentType.TICK, rotation=math.pi / 2,
                                  layer="Ticks", offset_y=0),
            ProfileLabelComponent(contents="hidden", visible=False),
        ),
        placement="below",
        obey_vertical_exaggeration=False,
    )
    profile = profile.with_label_style(ProfileLabelType.LINE, label_style)
    view_style = ProfileViewStyle(vertical_exaggeration=2)
    scene = ProfileViewRenderer.render([profile], "Line", view_style)
    text = [p for p in scene.primitives if p.type is PrimitiveType.TEXT]
    assert [p.text for p in text] == ["구배 10.00%", "길이 100.00"]
    assert [p.points[0] for p in text] == [Point2d(50, 28), Point2d(50, 26)]
    assert {layer.name for layer in scene.layers} >= {"Grades", "Ticks"}
    tick = next(p for p in scene.primitives if p.style.layer == "Ticks")
    assert tick.points == (Point2d(50, 29), Point2d(50, 31))

    disabled = ProfileViewRenderer.render(
        [profile], "Line", view_style, render_labels=False, labels=[StationElevationLabel(50)],
    )
    assert [p.text for p in disabled.primitives if p.type is PrimitiveType.TEXT] == ["STA 50.00", "EL 15.000"]
    path = tmp_path / "profile.dxf"
    DxfWriter(scene).write(path)
    assert "구배 10.00%" in path.read_text("cp949")
