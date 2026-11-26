from dataclasses import replace
import math
from xml.etree import ElementTree as ET

from cadgeom import Point2d
import pytest

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.alignment.label_component import AlignmentLabelComponent, ReferenceObjectType
from myalignment.alignment.label_set import AlignmentLabelSet
from myalignment.alignment.profile_geometry_label_extractor import ProfileGeometryLabelExtractor
from myalignment.alignment.profile_geometry_label_style import ProfileGeometryLabelStyle
from myalignment.alignment.profile_geometry_label_type import ProfileGeometryPointLabelType as Kind
from myalignment.export.dxf_writer import DxfWriter
from myalignment.export.svg_writer import SvgWriter
from myalignment.profile.profile import Profile, ProfileBuilder
from myalignment.profile.profile_symmetric_parabola import ProfileSymmetricParabola
from myalignment.profile.profileentitycollection import ProfileEntityCollection
from myalignment.profile.profiletype import ProfileType
from myalignment.render.alignment_renderer import AlignmentRenderer
from myalignment.render.composer import RenderOptions, SceneComposer
from myalignment.render.primitives import PrimitiveType
from myalignment.render.profile_geometry_label_renderer import ProfileGeometryLabelRenderer
from myalignment.render.scene import Scene


def _axis(name="Axis"):
    return AlignmentBuilder(name).with_pi_coords([(100, 200), (100, 300)]).with_start_station(100).build()


def _curve(crest=True):
    grade = 0.10 if crest else -0.10
    entity = ProfileSymmetricParabola.create(140, 10, grade, -grade, 40)
    return Profile("Design", ProfileType.FG, ProfileEntityCollection((entity,)))


def _break():
    return (
        ProfileBuilder("Design", ProfileType.FG)
        .add_tangent(100, 140, 10, 12)
        .add_tangent(140, 200, 12, 10).build()
    )


def _labels(scene, kind):
    return [p for p in scene.primitives if p.type is kind]


@pytest.mark.parametrize(("crest", "kind", "elevation"), [(True, Kind.HIGH_POINT, 9), (False, Kind.LOW_POINT, 11)])
def test_distinguishes_virtual_pvi_from_curve_extremum_and_endpoints(crest, kind, elevation):
    points = ProfileGeometryLabelExtractor.extract(_curve(crest))
    assert len(points) == 6
    indexed = {label.point_type: label for label in points}
    assert indexed[Kind.PVI].station == indexed[kind].station == 140
    assert indexed[Kind.PVI].elevation == 10 and indexed[kind].elevation == pytest.approx(elevation)
    assert indexed[Kind.PROFILE_START].grade_in is None and indexed[Kind.PROFILE_END].grade_out is None
    assert indexed[Kind.VPC].station == indexed[Kind.PROFILE_START].station == 120
    assert indexed[Kind.VPT].station == indexed[Kind.PROFILE_END].station == 160
    assert indexed[Kind.PVI].to_fields()["K Value"] == "2.000"


def test_tangent_break_can_be_filtered_independently_of_pvi():
    points = ProfileGeometryLabelExtractor.extract(_break(), (Kind.GRADE_BREAK,))
    point, = points
    assert point.station == 140 and point.grade_in == pytest.approx(0.05)
    assert point.to_fields()["Grade Out"] == "-3.33%"
    assert ProfileGeometryLabelExtractor.extract(_break(), ()) == []
    assert not ProfileGeometryLabelExtractor.extract(Profile())
    assert [p.station for p in ProfileGeometryLabelExtractor.extract(_break(), (Kind.PVI,))] == [140]


def test_station_equation_position_offsets_and_leader():
    axis = _axis().add_station_equation(130, 300)
    point, = ProfileGeometryLabelExtractor.extract(_break(), (Kind.GRADE_BREAK,))
    style = ProfileGeometryLabelStyle(
        labeled_points=(Kind.GRADE_BREAK,), show_leader=True, components=(AlignmentLabelComponent(
            contents="<[Raw Station]> · <[Station Value]> · <[Elevation Value]>",
            offset_x=2, offset_y=6, rotation=math.pi / 6, layer="My label",
        ),),
    )
    scene = ProfileGeometryLabelRenderer.render(Scene(), axis, [point], style)
    marker, = _labels(scene, PrimitiveType.CIRCLE)
    text, = _labels(scene, PrimitiveType.TEXT)
    assert marker.points == (Point2d(100, 240),)
    assert text.points == (Point2d(94, 242),) and text.rotation == math.pi / 6
    assert text.text == "140.00 · 310.00 · 12.000"
    assert _labels(scene, PrimitiveType.LINE)[-1].points == (marker.points[0], text.points[0])


def test_colocated_types_share_marker_and_reference_text_uses_actual_location():
    axis = _axis()
    labels = ProfileGeometryLabelExtractor.extract(_curve(), (Kind.PVI, Kind.HIGH_POINT))
    reference_axis = (
        AlignmentBuilder("Cross").with_pi_coords([(50, 240), (150, 240)])
        .with_start_station(10).build().add_station_equation(30, 500)
    )
    reference_profile = ProfileBuilder("Ground").add_tangent(100, 200, 4, 4).build()
    style = ProfileGeometryLabelStyle(
        labeled_points=(Kind.PVI, Kind.HIGH_POINT), components=(AlignmentLabelComponent(
            contents="<[Point Type]> <[Ref Station]> <[Profile Name]> <[Profile Elevation]>",
            reference_type=ReferenceObjectType.PROFILE, offset_y=3,
        ),),
    )
    scene = ProfileGeometryLabelRenderer.render(
        Scene(), axis, labels, style, reference_profile=reference_profile, reference_alignment=reference_axis,
    )
    texts = _labels(scene, PrimitiveType.TEXT)
    assert [p.text for p in texts] == ["HighPoint 530.00 Ground 4.000", "PVI 530.00 Ground 4.000"]
    assert texts[0].points != texts[1].points
    assert len(_labels(scene, PrimitiveType.CIRCLE)) == 1


def test_plan_composer_filters_styles_selects_profile_and_exports(tmp_path):
    profile = _curve()
    labels = AlignmentLabelSet().with_profile_geometry_style(
        ProfileGeometryLabelStyle.standard(), labeled_points=(Kind.HIGH_POINT,),
    )
    axis = replace(_axis(), profiles=(profile,)).with_label_set(labels)
    assert not _labels(AlignmentRenderer.render_plan(axis), PrimitiveType.TEXT)
    scene = SceneComposer.compose_alignment(axis, RenderOptions(render_alignment_labels=True, render_profiles=False))
    assert [p.text for p in _labels(scene, PrimitiveType.TEXT)] == ["HighPoint", "STA 140.00", "EL 9.000"]

    target = tmp_path / "labels.dxf"
    DxfWriter(scene).write(target)
    assert "C-ALIGN-PROF-GEOM" in target.read_text("cp949")
    svg = ET.fromstring(SvgWriter(scene).to_string())
    assert "HighPoint" in [p.text for p in svg.iter("{http://www.w3.org/2000/svg}text")]

    assert not _labels(
        AlignmentRenderer.render_plan(axis.with_label_set(
            labels.with_profile_geometry_style(labels.profile_geometry_style, labeled_points=()),
        ), render_labels=True), PrimitiveType.TEXT,
    )
    explicit = AlignmentRenderer.render_plan(
        _axis().with_label_set(AlignmentLabelSet().with_profile_geometry_style(ProfileGeometryLabelStyle.pvi_only())),
        render_labels=True, fg_profile=_break(),
    )
    assert [p.text for p in _labels(explicit, PrimitiveType.TEXT)] == ["PVI 140.00"]
    assert AlignmentLabelSet.with_profile_geometry().styles == AlignmentLabelSet.standard().styles


def test_outside_alignment_range_and_invalid_styles():
    axis = _axis()
    outside = ProfileBuilder("Design").add_tangent(0, 10, 0, 1).add_tangent(10, 20, 1, 0).build()
    result = ProfileGeometryLabelRenderer.render(Scene(), axis, ProfileGeometryLabelExtractor.extract(outside))
    assert not result.primitives
    with pytest.raises(ValueError, match="marker_size"):
        ProfileGeometryLabelStyle(marker_size=float("nan"))
