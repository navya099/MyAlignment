import math

import pytest

from myalignment.export.dxf_writer import DxfWriter
from myalignment.profile.band_style import VerticalGeometryBandStyle
from myalignment.profile.profile import ProfileBuilder
from myalignment.profile.vertical_geometry_extractor import VerticalGeometryExtractor
from myalignment.profile.view_band import BandType, ProfileViewBand
from myalignment.profile.view_style import ProfileViewStyle
from myalignment.render.primitives import PrimitiveType
from myalignment.render.profile_view_renderer import ProfileViewRenderer


@pytest.mark.parametrize("profile, symbol, station, elevation", [
    (ProfileBuilder().add_symmetric_parabola(100, 50, .03, -.01, 100).build(), "HP", 125, 49.625),
    (ProfileBuilder().add_asymmetric_parabola(100, 50, -.01, .03, 90, 30).build(), "LP", 100, 50.45),
])
def test_curve_points_include_pvi_and_exact_extremum(profile, symbol, station, elevation):
    points = VerticalGeometryExtractor.extract(profile)
    curve_points = {p.label_text: p for p in points if p.curve_length}
    assert set(curve_points) == {"VPC", "PVI", "VPT", symbol}
    assert curve_points["PVI"].station == 100
    assert curve_points["PVI"].elevation == 50
    assert curve_points["VPC"].station == profile.start_station
    assert curve_points["VPT"].station == profile.end_station
    extremum = curve_points[symbol]
    assert extremum.station == pytest.approx(station)
    assert extremum.elevation == pytest.approx(elevation)
    assert extremum.radius == pytest.approx(profile.length / .04)


def test_grade_break_requires_an_actual_change_and_monotonic_curves_have_no_extrema():
    tangents = (
        ProfileBuilder().add_tangent(0, 50, 0, 1)
        .add_tangent(50, 100, 1, 2).add_tangent(100, 150, 2, 1).build()
    )
    points = VerticalGeometryExtractor.extract(tangents)
    assert [p.station for p in points if p.label_text == "PVI"] == [0, 100, 150]
    grade_break, = [p for p in points if p.label_text == "GB"]
    assert grade_break.station == 100
    assert grade_break.grade_change == pytest.approx(-.04)
    monotonic = ProfileBuilder().add_symmetric_parabola(100, 50, .03, .01, 100).build()
    assert {p.label_text for p in VerticalGeometryExtractor.extract(monotonic)} == {"PVI", "VPC", "VPT"}


def test_profile_view_uses_named_profile_and_stacks_vertical_band(tmp_path):
    ground = ProfileBuilder("Ground").add_tangent(0, 200, 40, 40).build()
    design = ProfileBuilder("Design").add_symmetric_parabola(100, 50, .03, -.01, 100).build()
    style = VerticalGeometryBandStyle(
        band_height=5, tick_length=2, vpc_vpt_color=3, high_low_color=4,
        visible_types=("VPC", "VPT", "HP"),
    )
    bands = [
        ProfileViewBand(BandType.VERTICAL_GEOMETRY, location="bottom", gap=1, profile_names=("Design",)),
        ProfileViewBand(BandType.PROFILE_DATA, location="bottom", gap=2),
    ]
    scene = ProfileViewRenderer.render(
        [ground, design], "Main", ProfileViewStyle(vertical_exaggeration=2), bands,
        vertical_geometry_band_style=style, render_labels=False,
    )
    band = [p for p in scene.primitives if p.style.layer == style.layer]
    assert [p.points[0].y for p in band[:2]] == [68, 58]
    assert [p.x for p in band[0].points] == [50, 150]
    labels = [p for p in band if p.type is PrimitiveType.TEXT]
    assert [(p.text, p.points[0].x, p.style.color) for p in labels] == [
        ("VPC", 50, 3), ("HP", 125, 4), ("VPT", 150, 3),
    ]
    assert all(p.rotation == math.pi / 2 for p in labels)
    next_band = next(p for p in scene.primitives if p.style.layer == "C-PROF-BAND")
    assert next_band.points[0].y == 44
    path = tmp_path / "vertical-band.dxf"
    DxfWriter(scene).write(path)
    assert "\nHP\n50\n90.0\n" in path.read_text("cp949")
