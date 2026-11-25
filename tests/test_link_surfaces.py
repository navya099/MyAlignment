import math

import pytest

from myalignment.alignment import AlignmentBuilder
from myalignment.assembly import AssemblyBuilder
from myalignment.assembly.codes import LinkCode, PointCode
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.assembly.subassemblies.side_slope import SideSlope
from myalignment.corridor import CorridorBuilder
from myalignment.corridor.link_surface_manager import LinkSurfaceManager
from myalignment.corridor.link_surface_quantity import LinkSurfaceQuantity
from myalignment.corridor.link_surface_spec import LinkSurfaceSpec
from myalignment.corridor.multi_link_surface_builder import MultiLinkSurfaceBuilder
from myalignment.corridor.surface_extraction_mode import SurfaceExtractionMode as Mode
from myalignment.export.dxf_writer import DxfWriter
from myalignment.profile import ProfileBuilder
from myalignment.render.link_surface_renderer import LinkSurfaceRenderer
from myalignment.render.scene import Scene


@pytest.fixture
def road():
    axis = (
        AlignmentBuilder("Axis").with_pi_coords([(100, 200), (100, 230)])
        .with_start_station(1000).build()
    )
    grade = ProfileBuilder("Grade").add_tangent(1000, 1030, 10, 13).build()
    assembly = (
        AssemblyBuilder()
        .add_both(lambda side: BasicLane(width=3, slope=0, side=side))
        .add_both(lambda side: SideSlope(slope_ratio=2, height=1, side=side))
        .build()
    )
    corridor = (
        CorridorBuilder("Road").add_baseline("Axis", "Axis", "Grade", 1000, 1030)
        .add_region("First", 1000, 1008, assembly, frequency=4)
        .add_region("Second", 1020, 1028, assembly, frequency=4).build()
    )
    return corridor, {"alignments": {axis.name: axis}, "profiles": {grade.name: grade}}


@pytest.mark.parametrize("use_boundary", [True, False])
def test_same_code_disjoint_slopes_and_station_gaps(road, use_boundary):
    corridor, sources = road
    spec = LinkSurfaceSpec("Slopes", link_code=LinkCode.SLOPE, use_boundary=use_boundary)
    result = MultiLinkSurfaceBuilder.build_from_spec(corridor, spec, **sources)
    surface = result.surface
    assert surface.area_2d == pytest.approx(64)
    assert result.triangle_count == 16
    assert result.point_count == 24
    assert len(surface.boundaries) == (4 if use_boundary else 0)
    assert surface.elevation_at(104, 204) == pytest.approx(9.9)
    assert surface.triangle_at(100, 204) is None
    assert surface.triangle_at(104, 215) is None
    assert surface.triangle_at(104, 224) is not None


def test_all_links_skip_vertical_faces_and_preserve_independent_levels(road):
    corridor, sources = road
    manager = LinkSurfaceManager.from_corridor(corridor, **sources)
    assert set(manager.surfaces_by_code()) == {
        LinkCode.LANE, LinkCode.PAVEMENT_TOP, LinkCode.PAVEMENT_BOTTOM, LinkCode.SLOPE,
    }
    top = manager.get_by_link_code(LinkCode.PAVEMENT_TOP).surface
    bottom = manager.get_by_link_code(LinkCode.PAVEMENT_BOTTOM).surface
    assert top.elevation_at(102, 204) - bottom.elevation_at(102, 204) == pytest.approx(0.1)
    assert top.area_2d == pytest.approx(96)
    assert manager.get(top.name).surface is top
    quantity = LinkSurfaceQuantity.from_manager(manager)
    slope = quantity.get_by_code(LinkCode.SLOPE)
    assert slope.area_2d == pytest.approx(64)
    assert slope.area_3d > slope.area_2d
    assert quantity.to_dict()["Slope"]["area_3d"] == slope.area_3d
    assert quantity.total_area_2d == pytest.approx(manager.total_area)


def test_grouped_specs_deduplicate_and_correct_coincident_overhangs(road):
    corridor, sources = road
    top_codes = (LinkCode.LANE, LinkCode.PAVEMENT_TOP, LinkCode.SLOPE)
    spec = LinkSurfaceSpec("Finish", Mode.MULTI_LINK, top_codes)
    finished = MultiLinkSurfaceBuilder.build_from_spec(corridor, spec, **sources).surface
    assert finished.area_2d == pytest.approx(160)

    stacked = (LinkCode.PAVEMENT_BOTTOM, LinkCode.PAVEMENT_TOP)
    with pytest.raises(ValueError, match="Conflicting elevations"):
        MultiLinkSurfaceBuilder.build_from_spec(corridor, LinkSurfaceSpec("Layers", Mode.MULTI_LINK, stacked), **sources)
    upper = MultiLinkSurfaceBuilder.build_from_spec(
        corridor, LinkSurfaceSpec("Upper", Mode.MULTI_LINK, stacked, overhang_correction=True), **sources,
    ).surface
    assert upper.area_2d == pytest.approx(96)
    assert upper.elevation_at(102, 204) == pytest.approx(10.4)


def test_selected_all_and_point_based_specs_and_dxf(road, tmp_path):
    corridor, sources = road
    all_spec = LinkSurfaceSpec(
        "Pavement", Mode.ALL_LINKS, (LinkCode.PAVEMENT_TOP, LinkCode.PAVEMENT_BOTTOM), color=2,
    )
    point_spec = LinkSurfaceSpec("Edges", Mode.POINT_BASED, point_code=PointCode.CATCH_POINT)
    manager = LinkSurfaceManager.from_corridor(corridor, specs=[all_spec, point_spec], **sources)
    assert len(manager) == 3
    assert manager.get("Edges").surface.area_2d == pytest.approx(160)
    scene = LinkSurfaceRenderer.render(Scene(), manager, show_triangles=False)
    assert any(layer.name == "C-CORRIDOR-SURFACE-PAVEMENT_TOP" and layer.color == 2 for layer in scene.layers)
    out = tmp_path / "link-surfaces.dxf"
    DxfWriter(scene).write(out)
    text = out.read_text(encoding="cp949")
    assert "Pavement_Pavement_Top" in text and "C-CORRIDOR-SURFACE-EDGES" in text


def test_data_errors_are_not_skipped(road):
    corridor, sources = road
    with pytest.raises(ValueError, match="Missing profile"):
        LinkSurfaceManager.from_corridor(corridor, alignments=sources["alignments"])
    with pytest.raises(ValueError, match="do not form a TIN"):
        LinkSurfaceManager.from_corridor(
            corridor, specs=[LinkSurfaceSpec("Vertical", link_code=LinkCode.PAVEMENT_SIDE)], **sources,
        )


def test_link_sample_frequency_defaults_to_region_and_can_be_overridden(road):
    corridor, sources = road
    spec = LinkSurfaceSpec("Flat", link_code=LinkCode.PAVEMENT_TOP, sample_frequency=2.5)
    surface = MultiLinkSurfaceBuilder.build_from_spec(corridor, spec, **sources).surface
    assert any(math.isclose(point.y, 202.5) for point in surface.points)
    assert surface.area_2d == pytest.approx(96)


def test_partial_projected_overlap_is_rejected_even_with_overhang_correction():
    axes = {
        name: AlignmentBuilder(name).with_pi_coords([(0, y), (10, y)]).build()
        for name, y in (("South", 0), ("North", 1))
    }
    assembly = AssemblyBuilder().add_right(BasicLane(width=3, slope=0)).build()
    builder = CorridorBuilder()
    for axis in axes.values():
        builder.add_baseline_from_alignment(axis)
        builder.add_region(axis.name, 0, 10, assembly, baseline_name=axis.name)
    spec = LinkSurfaceSpec("Top", link_code=LinkCode.LANE, overhang_correction=True)
    with pytest.raises(ValueError, match="projected link triangles overlap"):
        MultiLinkSurfaceBuilder.build_from_spec(builder.build(), spec, alignments=axes)
