from dataclasses import replace

from cadgeom import Point2d
import pytest

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.export.dxf_3d_writer import Dxf3DWriter
from myalignment.export.dxf_writer import DxfWriter
from myalignment.pipe import (
    Pipe, PipeMaterial, PipeNetwork, PipeNetworkBuilder, PipeNetworkValidator, PipePart,
    PipeShape, Structure, StructurePart, StructureType,
)
from myalignment.profile.profile import ProfileBuilder
from myalignment.profile.view_style import ProfileViewStyle
from myalignment.render.pipe_network_renderer import PipeNetwork3DRenderer, PipeNetworkRenderer
from myalignment.render.primitives import PrimitiveType
from myalignment.render.primitives_3d import PrimitiveType3D
from myalignment.render.profile_view_renderer import ProfileViewRenderer
from myalignment.render.scene import Scene
from myalignment.surface.tin_surface import TinSurface


def _ground(end=30, *, name="Ground"):
    return TinSurface.from_points(
        [(-1, -4, 12), (end, -4, 12), (end, 4, 12), (-1, 4, 12)], name=name,
    )


def _network_builder():
    return (
        PipeNetworkBuilder("Storm drain").with_parts_list("RCP")
        .add_manhole("MH1", Point2d(0, 0), rim_elevation=12, invert_elevation=10, sump_elevation=9)
        .add_null_structure("Join", Point2d(10, 0), invert_elevation=9.9)
        .add_structure("Out", StructurePart(structure_type=StructureType.HEADWALL),
                       Point2d(20, 0), rim_elevation=11, invert_elevation=9.7)
        .add_pipe("P1", "MH1", "S_001")
        .add_pipe("P2", "Join", "Out", start_invert=9.8)
    )


def test_pipe_links_reconcile_backlinks_and_lowest_inverts():
    network = _network_builder().build()
    assert len(network) == 5
    assert network.parts_list_name == "RCP"
    assert network.total_pipe_length == 20
    main, branch = network.pipes
    assert network.get_pipe(main.id) == main
    assert main.start_structure_id == "S_000" and main.end_structure_id == "S_001"
    join = network.get_structure(main.end_structure_id)
    assert join.connected_pipe_ids == (main.id, branch.id)
    assert join.invert_elevation == 9.8
    assert main.slope_percent == pytest.approx(1)
    assert network.min_cover is None and main.cover_start is None
    assert PipeNetworkValidator.is_valid(network)
    assert main.part.outer_diameter_mm == 550 and main.part.diameter_m == 0.45


def test_builder_resolves_raw_station_and_late_alignment_without_mutating_prior_network():
    axis = (
        AlignmentBuilder("Main").with_pi_coords([(0, 0), (30, 0)])
        .with_start_station(100).build().add_station_equation(105, 200)
    )
    builder = (
        PipeNetworkBuilder()
        .add_manhole("Start", station=100, offset=3, rim_elevation=12, invert_elevation=10)
        .add_manhole("End", point=Point2d(12, -3), rim_elevation=12, invert_elevation=9.8)
        .add_pipe("Pipe", "Start", "End")
    )
    with pytest.raises(ValueError, match="requires XY or station"):
        builder.build()
    network = builder.with_alignment(axis).build()
    assert network.structures[1].station == pytest.approx(112)
    assert network.structures[1].offset == pytest.approx(3)
    assert network.pipes[0].start_point == Point2d(0, -3)
    assert network.pipes[0].length == pytest.approx(12)
    assert network.pipes[0].alignment_name == axis.name

    covered = builder.with_surface(_ground()).build()
    assert covered.min_cover == pytest.approx(1.5)
    assert network.min_cover is None


def test_cover_uses_outer_crown_on_both_ends_and_checks_tin_limits():
    network = _network_builder().with_surface(_ground()).build()
    assert PipeNetworkValidator.is_valid(network)
    assert network.pipes[0].cover_start == pytest.approx(1.5)
    assert network.pipes[0].cover_end == pytest.approx(1.6)
    assert any("P1" in error and "start cover" in error for error in PipeNetworkValidator.validate(
        network, min_cover=1.55,
    ))
    missing = network.with_cover_from(_ground(15, name=""))
    assert missing.pipes[-1].cover_end is None
    assert "end surface elevation is unavailable" in " ".join(PipeNetworkValidator.validate(missing))
    unnamed = _network_builder().with_surface(TinSurface(name="")).build()
    assert unnamed.min_cover is None and not PipeNetworkValidator.is_valid(unnamed)


def test_builder_rejects_invalid_connections_and_incremental_pipe_normalizes_endpoints():
    builder = _network_builder()
    with pytest.raises(ValueError, match="different structures"):
        builder.add_pipe("Loop", "Join", "S_001")
    with pytest.raises(ValueError, match="found 0"):
        builder.add_pipe("Missing", "MH1", "Missing")
    with pytest.raises(ValueError, match="unique"):
        builder.add_manhole("MH1", Point2d(4, 0))
    network = builder.build()
    extra = Pipe(id="extra", name="Extra", start_structure_id="S_000", end_structure_id="S_002",
                 start_invert=10, end_invert=9.7)
    new_network = network.add_pipe(extra)
    assert new_network.get_pipe("extra").end_point == Point2d(20, 0)
    assert new_network.get_structure("S_000").connected_pipe_ids == ("P_000", "extra")
    assert network.get_structure("S_000").connected_pipe_ids == ("P_000",)
    with pytest.raises(ValueError, match="endpoint does not match"):
        network.add_pipe(replace(extra, start_point=Point2d(30, 0)))


def test_direct_invalid_models_report_geometry_connections_and_adverse_slope():
    a = Structure(id="a", name="Starting", point=Point2d(0, 0), rim_elevation=4, invert_elevation=1)
    b = Structure(id="b", name="Ending", point=Point2d(10, 0), rim_elevation=4, invert_elevation=2)
    pipe = Pipe(id="p", name="P", start_structure_id="a", end_structure_id="b",
                start_point=a.point, end_point=b.point, start_invert=1, end_invert=2)
    assert any("adverse slope" in error for error in PipeNetworkValidator.validate(
        PipeNetwork(pipes=(pipe,), structures=(a, b)), min_slope=0,
    ))
    broken = replace(pipe, end_structure_id="missing", end_point=None)
    errors = PipeNetworkValidator.validate(PipeNetwork(pipes=(broken,), structures=(a,)))
    assert any("missing end structure" in error for error in errors)
    assert any("positive plan length" in error for error in errors)


def test_non_circular_part_dimensions_set_cover_and_profile_center():
    part = PipePart(material=PipeMaterial.CONCRETE, shape=PipeShape.RECTANGULAR,
                    diameter_mm=600, width_mm=1000, wall_thickness_mm=75)
    pipe = Pipe(part=part, start_point=Point2d(0, 0), end_point=Point2d(5, 0),
                start_invert=10, end_invert=9.9, start_surface_elevation=12)
    assert part.width_m == 1 and part.outer_diameter_mm == 750
    assert pipe.cover_start == pytest.approx(1.325)
    assert pipe.centerline[0].z == pytest.approx(10.3)
    with pytest.raises(ValueError, match="circular pipe"):
        PipePart(width_mm=600)


def test_plan_and_3d_render_hide_null_structures_and_export(tmp_path):
    network = _network_builder().build()
    plan = PipeNetworkRenderer.render_plan(Scene(), network)
    assert [p.text for p in plan.primitives if p.type is PrimitiveType.TEXT] == ["MH1", "Out"]
    assert len([p for p in plan.primitives if p.type is PrimitiveType.CIRCLE]) == 2
    scene = PipeNetwork3DRenderer.render(network, z_scale=2)
    assert scene.primitives[0].points[1].z == pytest.approx(19.8)
    assert len([p for p in scene.primitives if p.type is PrimitiveType3D.POLYLINE]) == 2
    assert scene.primitives[2].points[1].z == 18

    out_2d, out_3d = tmp_path / "plan.dxf", tmp_path / "wireframe.dxf"
    DxfWriter(plan).write(out_2d)
    Dxf3DWriter(scene).write(out_3d)
    assert "C-PIPE-NETWORK-PIPE" in out_2d.read_text("cp949")
    assert "C-PIPE-3D" in out_3d.read_text("cp949")

    alignment = AlignmentBuilder("Main").with_pi_coords([(0, 0), (20, 0)]).build()
    projections = PipeNetworkRenderer.profile_projections(network, alignment)
    assert [(p.start_station, p.end_station) for p in projections] == [(0, 10), (10, 20)]
    assert projections[0].elevation == pytest.approx(10.225)
    fg = ProfileBuilder("FG").add_tangent(0, 20, 12, 12).build()
    profile_scene = ProfileViewRenderer.render([fg], alignment.name, ProfileViewStyle(), projections=projections)
    assert any(p.text == "P1" for p in profile_scene.primitives if p.type is PrimitiveType.TEXT)
