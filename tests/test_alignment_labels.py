import pytest
from cadgeom import Point2d

from myalignment.alignment.alignment import Alignment
from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.alignment.label_component import AlignmentLabelComponent, ReferenceObjectType
from myalignment.alignment.label_set import AlignmentLabelSet
from myalignment.alignment.label_style import AlignmentLabelStyle
from myalignment.alignment.label_type import AlignmentLabelType
from myalignment.enitity.arc_entity import ArcEntity
from myalignment.enitity.entity_collection import AlignmentEntityCollection
from myalignment.enitity.spiral_entity import SpiralEntity
from myalignment.enum.spiraltype import SpiralType
from myalignment.export.dxf_writer import DxfWriter
from myalignment.profile.profile import ProfileBuilder
from myalignment.render.alignment_label_renderer import AlignmentLabelRenderer
from myalignment.render.alignment_renderer import AlignmentRenderer
from myalignment.render.composer import RenderOptions, SceneComposer
from myalignment.render.primitives import PrimitiveType
from myalignment.render.scene import Scene
from myalignment.surface.tin_surface import TinSurface
from myalignment.utils import CurveDirection


def test_station_labels_deduplicate_minor_ticks_and_preserve_sta_origin():
    alignment = (
        AlignmentBuilder().with_pi_coords([(10, 20), (110, 20)])
        .with_start_station(95).with_design_speed(80).build()
    )
    major = AlignmentLabelStyle(label_type=AlignmentLabelType.MAJOR_STATION, components=(
        AlignmentLabelComponent(contents="<[Station Value]> <[Northing]> <[Design Speed]>"),
    ))
    minor = AlignmentLabelStyle.minor_station_style()
    styles = AlignmentLabelSet().with_style(major.label_type, major).with_style(minor.label_type, minor)
    scene = AlignmentLabelRenderer.render(
        Scene(), alignment.with_label_set(styles), major_interval=50, minor_interval=10,
    )
    texts = [p.text for p in scene.primitives if p.type is PrimitiveType.TEXT]
    assert texts == ["100.00 20.000 80", "150.00 20.000 80"]
    ticks = [p for p in scene.primitives if p.type is PrimitiveType.LINE]
    assert [p.points[0].x for p in ticks] == [25, 35, 45, 55, 75, 85, 95, 105]
    assert ticks[0].points == (Point2d(25, 19), Point2d(25, 21))


def test_geometry_labels_and_programmatic_reference_text_export(tmp_path):
    style = AlignmentLabelStyle(label_type=AlignmentLabelType.GEOMETRY_POINT, components=(
        AlignmentLabelComponent(contents="<[Geometry Point Text]> <[Entity Before]>/<[Entity After]>"),
        AlignmentLabelComponent(
            contents="지반 <[Surface Elevation(Um|P3)]>", reference_type=ReferenceObjectType.SURFACE,
            reference_field="Surface Elevation",
        ),
        AlignmentLabelComponent(
            contents="<[Profile Name]> <[Profile Elevation]>", reference_type=ReferenceObjectType.PROFILE,
        ),
        AlignmentLabelComponent(
            contents="<[Alignment Name]> <[Alignment Station]> <[Alignment Offset]>",
            reference_type=ReferenceObjectType.ALIGNMENT,
        ),
    ))
    alignment = (
        AlignmentBuilder().with_pi_coords([(0, 0), (50, 0), (50, 50)]).build()
        .with_label_set(AlignmentLabelSet(styles={style.label_type: style}))
    )
    surface = TinSurface.from_points([(0, -20, 9), (100, -20, 9), (50, 30, 9)])
    profile = ProfileBuilder("설계").add_tangent(0, 100, 10, 20).build()
    reference = AlignmentBuilder("Parallel").with_pi_coords([(0, -10), (100, -10)]).build()
    scene = AlignmentRenderer.render_plan(
        alignment, render_labels=True, surface=surface, profile=profile, reference_alignment=reference,
    )
    texts = [p.text for p in scene.primitives if p.type is PrimitiveType.TEXT]
    assert texts == ["PI Line/Line", "지반 9.000", "설계 15.000", "Parallel 50.00 -10.000"]
    assert [p.text for p in AlignmentLabelRenderer.render(Scene(), alignment).primitives] == [
        "PI Line/Line", "지반 ???", "??? ???", "??? ??? ???",
    ]
    path = tmp_path / "plan-labels.dxf"
    DxfWriter(scene).write(path)
    assert "지반 9.000" in path.read_text("cp949")


def test_segment_labels_render_at_midpoints_and_composer_is_opt_in():
    spiral = SpiralEntity.create(
        Point2d(0, 0), 0, 200, 20, SpiralType.Clothoid, CurveDirection.LEFT,
    )
    arc = ArcEntity.create(spiral.end_coord, spiral.end_azimuth, 200, 0.2, CurveDirection.LEFT, 20)
    curve_style = AlignmentLabelStyle(label_type=AlignmentLabelType.CURVE, components=(
        AlignmentLabelComponent(contents="<[Radius]> <[Delta]> <[Tangent]>", offset_y=0),
    ))
    spiral_style = AlignmentLabelStyle.spiral_style()
    alignment = Alignment(
        entities=AlignmentEntityCollection((spiral, arc)),
        label_set=AlignmentLabelSet().with_style(curve_style.label_type, curve_style)
        .with_style(spiral_style.label_type, spiral_style),
    )
    assert not any(p.type is PrimitiveType.TEXT for p in SceneComposer.compose_alignment(alignment).primitives)
    scene = SceneComposer.compose_alignment(alignment, RenderOptions(render_alignment_labels=True))
    labels = [p for p in scene.primitives if p.type is PrimitiveType.TEXT]
    assert [p.text for p in labels] == ["L: 20.00", "R: 200.00", "200.00 11.46° 20.07"]
    assert labels[-1].points == (arc.point_at(40),)
    with pytest.raises(ValueError, match="intervals"):
        AlignmentLabelRenderer.render(Scene(), alignment, minor_interval=0)
