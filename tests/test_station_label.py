from cadgeom import Point2d

from myalignment.export.dxf_writer import DxfWriter
from myalignment.profile.label_style import LabelStyle
from myalignment.profile.profile import ProfileBuilder
from myalignment.profile.station_label import StationElevationLabel
from myalignment.profile.view_style import ProfileViewStyle
from myalignment.render.primitives import PrimitiveType
from myalignment.render.profile_view_renderer import ProfileViewRenderer
from myalignment.render.scene import Scene
from myalignment.render.station_label_renderer import StationLabelRenderer


def _profile(name, start=100, elevation=10):
    return ProfileBuilder(name).add_tangent(start, start + 50, elevation, elevation + 5).build()


def test_station_label_evaluates_two_profiles_and_unavailable_fields():
    profiles = [_profile("설계"), _profile("현황", start=120, elevation=9)]
    style = LabelStyle(fields=(
        "STA <[Station Value]>",
        "<[Profile 1 Name]>: <[Profile 1 Elevation]>",
        "<[Profile 2 Name]>: <[Profile 2 Elevation]>",
    ))
    label = StationElevationLabel(110, style).with_profile2("현황")
    assert tuple(label.evaluate(profiles).values()) == ("STA 110.00", "설계: 11.000", "현황: ???")
    updated = label.with_profile1("현황").with_profile2("설계")
    assert tuple(updated.evaluate(profiles).values()) == ("STA 110.00", "현황: ???", "설계: 11.000")
    assert label.profile1_name == "" and label.profile2_name == "현황"
    legacy = StationElevationLabel(125, style, profile_name="현황")
    assert legacy.evaluate(profiles)[style.fields[1]] == "현황: 9.500"
    assert legacy.evaluate(profiles)[style.fields[2]] == "???: ???"


def test_profile_view_renders_station_label_as_dxf_text_rows(tmp_path):
    profiles = [_profile("설계"), _profile("현황", elevation=9)]
    style = LabelStyle(
        fields=("STA <[Station Value]>\n<[Profile 1 Name]> <[Profile 1 Elevation]>",
                "<[Profile 2 Name]> <[Profile 2 Elevation]>"),
        text_height=1.5, offset_x=1, offset_y=4, marker_size=0.5, text_color=2,
    )
    label = StationElevationLabel(125, style).with_profile2("현황")
    scene = ProfileViewRenderer.render(
        profiles, "Rail", ProfileViewStyle(vertical_exaggeration=2), labels=[label],
    )

    marks = [p for p in scene.primitives if p.style.layer == StationLabelRenderer.LAYER]
    assert [p.type for p in marks] == [PrimitiveType.LINE] * 2 + [PrimitiveType.TEXT] * 3
    assert set(marks[0].points + marks[1].points) == {
        Point2d(124, 24), Point2d(124, 26), Point2d(126, 24), Point2d(126, 26),
    }
    assert [p.points[0] for p in marks[2:]] == [Point2d(127, 33), Point2d(127, 30), Point2d(127, 27)]
    assert all(p.style.color == 2 for p in marks)
    assert all(p.text_height == 3 for p in marks[2:])

    path = tmp_path / "labels.dxf"
    DxfWriter(scene).write(path)
    data = path.read_text("cp949").splitlines()
    groups = list(zip(data[::2], data[1::2]))
    assert groups.count(("0", "TEXT")) == 3
    assert ("1", "STA 125.00") in groups
    assert ("1", "설계 12.500") in groups
    assert ("1", "현황 11.500") in groups


def test_missing_anchors_are_skipped_and_marker_can_be_disabled():
    profiles = [_profile("Main")]
    scene = Scene()
    outside = StationElevationLabel(175)
    missing = StationElevationLabel(125, profile_name="Other")
    assert StationLabelRenderer.render(scene, outside, profiles) is scene
    assert StationLabelRenderer.render(scene, missing, profiles) is scene
    label = StationElevationLabel(125, LabelStyle(show_marker=False))
    rendered = StationLabelRenderer.render(scene, label, profiles)
    assert [p.type for p in rendered.primitives] == [PrimitiveType.TEXT, PrimitiveType.TEXT]
