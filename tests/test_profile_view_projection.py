from dataclasses import replace

from cadgeom import Point2d
import pytest

from myalignment.alignment import AlignmentBuilder
from myalignment.export.dxf_writer import DxfWriter
from myalignment.featureline.feature_line import FeatureLine
from myalignment.featureline.vertex import FeatureLineVertex
from myalignment.profile import (
    ProfileBuilder, ProfileViewProjection, ProfileViewSplitConfig, ProfileViewSplitMethod,
    ProjectedPoint, ProjectionBuilder, ProjectionComposer, ProjectionObjectType, ProjectionReference, ProjectionStyle,
)
from myalignment.profile.view_style import ProfileViewStyle
from myalignment.render.primitives import PrimitiveType
from myalignment.render.primitives_3d import Point3D
from myalignment.render.profile_view_renderer import ProfileViewRenderer
from myalignment.render.profile_view_split_composer import ProfileViewSplitComposer
from myalignment.render.projection_renderer import ProjectionRenderer
from myalignment.render.scene import Scene
from myalignment.structure.bridge import Bridge


@pytest.fixture
def main():
    bridge = Bridge.create("교량 A", 1010, 1070)
    axis = (
        AlignmentBuilder("Main").with_pi_coords([(0, 0), (100, 0)])
        .with_start_station(1000).with_structure(bridge).build()
    )
    profile = ProfileBuilder("FG").add_tangent(1000, 1100, 10, 30).build()
    return axis, profile, bridge


def test_structures_and_multiple_crossings_use_profile_elevation(main):
    axis, profile, bridge = main
    crossing = (
        AlignmentBuilder("Cross").with_pi_coords([(20, -10), (20, 10), (80, 10), (80, -10)]).build()
    )
    structures, first, second = ProjectionComposer.project_all(axis, profile, [crossing])
    assert structures.original_object is bridge
    assert (structures.start_station, structures.end_station, structures.elevation) == (1010, 1070, 18)
    assert [(item.start_station, item.elevation) for item in (first, second)] == [(1020, 14), (1080, 26)]
    assert ProjectionBuilder.project_alignment_crossing(axis, profile, crossing) == first
    away = AlignmentBuilder("Away").with_pi_coords([(0, 10), (100, 10)]).build()
    assert ProjectionBuilder.project_alignment_crossing(axis, profile, away) is None


def test_point_block_and_pipe_preserve_elevation_sources(main):
    axis, profile, _ = main
    point = ProjectionBuilder.project_point(axis, profile, Point2d(20, -8))
    assert (point.start_station, point.elevation) == (1020, 14)
    surveyed = ProjectionBuilder.project_point(axis, profile, Point3D(40, 6, 0.0))
    assert surveyed.elevation == 0
    explicit = ProjectionBuilder.project_point(axis, profile, Point3D(40, 6, 55), elevation=15)
    assert explicit.elevation == 15

    block_style = replace(ProjectionStyle.point_style(), object_type=ProjectionObjectType.BLOCK)
    _, block, pipe = ProjectionComposer.project_all(axis, profile, references=[
        ProjectionReference(Point3D(50, 20, 33), block_style, "Survey block"),
        ProjectionReference((Point3D(10, 5, 7), Point3D(30, 5, 9)),
                            ProjectionStyle(object_type=ProjectionObjectType.PIPE), "Pipe 1"),
    ])
    assert (block.name, block.start_station, block.elevation) == ("Survey block", 1050, 33)
    assert pipe.projected_points == (ProjectedPoint(1010, 7), ProjectedPoint(1030, 9))


def test_feature_line_clips_with_interpolation_and_no_false_links(main):
    axis, profile, _ = main
    feature = FeatureLine("Ridge", tuple(
        FeatureLineVertex(x, 2, z) for x, z in ((10, 30), (50, 70), (90, 110), (40, 130))
    ))
    projection = ProjectionBuilder.project_feature_line(axis, profile, feature)
    assert tuple(point.station for point in projection.projected_points) == (1010, 1050, 1090, 1040)
    assert projection.clipped_paths((1030, 1070)) == (
        (ProjectedPoint(1030, 50), ProjectedPoint(1050, 70), ProjectedPoint(1070, 90)),
        (ProjectedPoint(1070, 118), ProjectedPoint(1040, 130)),
    )
    style = ProfileViewStyle(vertical_exaggeration=2)
    scene = ProfileViewRenderer.render([profile], "Main", style, station_range=(1030, 1070), projections=[projection])
    assert scene.metadata["elevation_range"] == pytest.approx((11, 135))
    lines = [item for item in scene.primitives if item.style.layer == projection.style.layer
             and item.type is not PrimitiveType.TEXT and item.style.color == projection.style.range_color]
    assert [tuple((p.x, p.y) for p in item.points) for item in lines] == [
        ((1030, 100), (1050, 140), (1070, 180)), ((1070, 236), (1040, 260)),
    ]


def test_split_renderer_clips_structure_at_panel_edge_and_dxf_writes(main, tmp_path):
    axis, profile, bridge = main
    projected = ProjectionBuilder.project_structure(axis, profile, bridge)
    config = ProfileViewSplitConfig(
        method=ProfileViewSplitMethod.MANUAL, manual_split_stations=(1050,), overlap_station=0, columns=2,
    )
    scene = ProfileViewSplitComposer.compose(
        [profile], axis.name, ProfileViewStyle(vertical_exaggeration=3), config, projections=[projected],
    )
    bars = [item for item in scene.primitives if item.style.layer == projected.style.layer
            and item.type is PrimitiveType.LINE and item.style.color == projected.style.range_color]
    assert len(bars) == 2
    for item, panel, bounds in zip(bars, scene.metadata["panels"], ((1010, 1050), (1050, 1070)), strict=True):
        x, y = panel["translation"]
        assert tuple(point.x - x for point in item.points) == pytest.approx(bounds)
        assert all(point.y - y == pytest.approx(54) for point in item.points)
    path = tmp_path / "projection.dxf"
    DxfWriter(scene).write(path)
    content = path.read_text(encoding="cp949")
    assert "교량 A" in content and "STA 1010.0 ~ 1070.0" in content


def test_style_visibility_and_invalid_projection_inputs(main):
    axis, profile, _ = main
    style = replace(ProjectionStyle.point_style(), show_marker=False, show_elevation=False,
                    label_format="{name}\nEL {elevation:.1f}")
    point = ProjectionBuilder.project_point(axis, profile, Point2d(20, 0), style=style)
    scene = ProjectionRenderer.render(Scene(), [point], ProfileViewStyle(), profile, 1000, 1050)
    assert [primitive.text for primitive in scene.primitives] == ["Point"]
    with pytest.raises(ValueError, match="label_format"):
        replace(style, label_format="{missing}")
    with pytest.raises(ValueError, match="outside"):
        ProjectionBuilder.project_structure(axis, profile, Bridge.create("Outside", 1110, 1120))
    with pytest.raises(ValueError, match="inside"):
        ProfileViewProjection(projected_points=(ProjectedPoint(1, 2),))
