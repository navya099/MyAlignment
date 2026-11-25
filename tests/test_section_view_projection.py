from dataclasses import replace

import pytest
from cadgeom import Point2d

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.export.dxf_writer import DxfWriter
from myalignment.featureline.feature_line import FeatureLine
from myalignment.featureline.vertex import FeatureLineVertex
from myalignment.profile.profile import ProfileBuilder
from myalignment.render.primitives import PrimitiveType
from myalignment.render.scene import Scene
from myalignment.render.section_view_renderer import SectionViewRenderer
from myalignment.section.projection_builder import SectionProjectionBuilder
from myalignment.section.projection_composer import SectionProjectionComposer
from myalignment.section.projection_style import SectionProjectionStyle
from myalignment.section.section_view_builder import SectionViewBuilder
from myalignment.section.section_view_data import SectionViewData
from myalignment.section.section_view_style import SectionViewStyle
from myalignment.structure.bridge import Bridge
from myalignment.structure.tunnel import Tunnel


def _axis():
    return (AlignmentBuilder("Axis").with_pi_coords([(100, 200), (100, 240)])
            .with_start_station(500).build())


def _xy(points):
    return [(p.offset, p.elevation) for p in points]


def test_point_tolerance_uses_selected_section_and_right_positive_offset():
    axis = _axis()
    builder = SectionProjectionBuilder
    point = builder.project_point(axis, 510, Point2d(104, 211), 13.5, "Right")
    assert _xy(point.projected_points)[0] == pytest.approx((4, 13.5))
    assert builder.project_point(axis, 510, Point2d(96, 211.1), 2) is None
    endpoint = builder.project_point(axis, 500, Point2d(96, 198.5), 2)
    assert endpoint is None
    accepted = builder.project_point(axis, 500, Point2d(96, 198.5), 2, station_tolerance=2)
    assert accepted.offset_center == pytest.approx(-4)
    with pytest.raises(ValueError, match="station_tolerance"):
        builder.project_point(axis, 510, Point2d(100, 210), 2, station_tolerance=-1)
    with pytest.raises(ValueError, match="diameter"):
        builder.project_pipe(axis, 510, Point2d(100, 210), 2, 0)


def test_feature_line_interpolates_crossings_and_keeps_coplanar_segments_separate():
    axis = _axis()
    feature = FeatureLine("Breakline", tuple(FeatureLineVertex(*vertex) for vertex in [
        (98, 205, 10), (98, 215, 20), (102, 205, 30),
        (105, 210, 40), (107, 210, 42), (108, 212, 45),
    ]))
    result = SectionProjectionBuilder.project_feature_line(axis, 510, feature)
    for point, expected in zip(_xy(result.projected_points), [(-2, 15), (0, 25), (5, 40), (7, 42)], strict=True):
        assert point == pytest.approx(expected)
    assert result.projected_links == ((2, 3),)

    closed = FeatureLine("Closed", tuple(FeatureLineVertex(*vertex) for vertex in [
        (93, 205, 10), (97, 205, 20), (95, 215, 30),
    ]), is_closed=True)
    result = SectionProjectionBuilder.project_feature_line(axis, 510, closed)
    assert len(result.projected_points) == 2
    assert result.projected_points[-1].elevation == pytest.approx(20)


def test_crossing_alignment_uses_target_station_and_profiles():
    axis = _axis()
    profile = ProfileBuilder("Target grade").add_tangent(900, 920, 50, 70).build()
    other = (AlignmentBuilder("Crossing").with_pi_coords([(90, 205), (106, 217)])
             .with_start_station(900).with_profile(profile).build())
    result = SectionProjectionBuilder.project_alignment(axis, 510, other)
    assert len(result.projected_points) == 1
    assert _xy(result.projected_points)[0] == pytest.approx((-10 / 3, 50 + 25 / 3))
    short = ProfileBuilder("Short").add_tangent(915, 920, 20, 20).build()
    assert SectionProjectionBuilder.project_alignment(axis, 510, other, profile=short) is None


def test_structure_uses_profile_metadata_and_actual_label_stations():
    profile = ProfileBuilder("Grade").add_tangent(500, 540, 10, 14).build()
    bridge = Bridge.create("교량", 505, 515, width=12, deck_height=1.2, pier_bottom_elevation=4)
    tunnel = Tunnel.create("터널", 520, 535, diameter=8, bottom_elevation=3)
    axis = replace(_axis(), profiles=(profile,))
    bridge_projection = SectionProjectionBuilder.project_structure(axis, 510, bridge)
    assert bridge_projection.offset_width == 12
    assert bridge_projection.bottom_elevation == 11
    assert bridge_projection.top_elevation == pytest.approx(12.2)
    assert bridge_projection.pier_bottom_elevation == 4
    assert SectionProjectionBuilder.project_structure(axis, 510, tunnel) is None
    tunnel_projection = SectionProjectionBuilder.project_structure(axis, 520, tunnel)
    assert (tunnel_projection.bottom_elevation, tunnel_projection.top_elevation) == (3, 11)
    assert tunnel_projection.offset_width == tunnel_projection.elevation_height == 8
    scene = SectionViewRenderer.render(Scene(), SectionViewData(510), projections=[bridge_projection])
    assert "(505.0~515.0)" in [p.text for p in scene.primitives]
    markers = [p for p in scene.primitives if p.style.layer == bridge_projection.style.layer
               and p.type is PrimitiveType.POLYLINE and not p.closed]
    assert len(markers) == 2


def test_pipe_shares_section_scale_and_honors_visibility():
    axis = _axis()
    style = replace(SectionProjectionStyle.pipe_style(), show_marker=False, show_label=False)
    pipe = SectionProjectionBuilder.project_pipe(axis, 510, Point2d(130, 210), -15, 4, style=style)
    view = SectionViewStyle(vertical_exaggeration=2)
    scene = SectionViewRenderer.render(Scene(), SectionViewData(510), view, projections=[pipe])
    outline, = [p for p in scene.primitives if p.style.layer == style.layer]
    assert outline.type is PrimitiveType.POLYLINE and outline.closed
    width = max(p.x for p in outline.points) - min(p.x for p in outline.points)
    height = max(p.y for p in outline.points) - min(p.y for p in outline.points)
    assert height / width == pytest.approx(2)
    assert all(view.margin_left <= p.x <= view.width - view.margin_right + 1e-9 for p in outline.points)
    assert all(view.margin_bottom <= p.y <= view.height - view.margin_top for p in outline.points)


def test_composer_and_section_builders_export_station_specific_overlays(tmp_path):
    bridge = Bridge.create("교량", 505, 515)
    axis = replace(_axis(), structures=_axis().structures.add(bridge))
    assembly = AssemblyBuilder().add_both(lambda side: BasicLane(side=side)).build()
    corridor = (CorridorBuilder().add_baseline("BL", axis.name, "", 500, 540)
                .add_region("Road", 500, 540, assembly).build())
    projections = SectionProjectionComposer.project_all(
        axis, 510, pipes=[(Point2d(106, 210), -5, 2, "배수관")],
        points=[(Point2d(105, 230), 8, "Outside tolerance")],
    )
    assert [p.name for p in projections] == ["교량", "배수관"]
    assert projections[1].contains_offset(6)
    single = SectionViewBuilder.single_with_projections(corridor, axis, 510, projections)
    grid = SectionViewBuilder.grid_layout(
        corridor, axis, [530, 510], columns=2, projections_by_station={510: projections},
    )
    single_label = next(p for p in single.primitives if p.text == "배수관")
    grid_label, = [p for p in grid.primitives if p.text == "배수관"]
    assert grid_label.points[0].x - single_label.points[0].x == pytest.approx(420)
    dxf = tmp_path / "projections.dxf"
    DxfWriter(grid).write(dxf)
    contents = dxf.read_text("cp949")
    assert "C-SECTION-PROJECTION" in contents
    assert "배수관" in contents and "Φ2.0m" in contents
