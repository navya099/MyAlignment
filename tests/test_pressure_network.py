from dataclasses import replace
import math

import pytest

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.export.dxf_3d_writer import Dxf3DWriter
from myalignment.export.dxf_writer import DxfWriter
from myalignment.pressure import (
    AppurtenancePart, AppurtenanceType, FittingPart, FittingType, PressureNetworkBuilder,
    PressureNetworkValidator, PressurePipePart,
)
from myalignment.render.pressure_network_renderer import PressureNetwork3DRenderer, PressureNetworkRenderer
from myalignment.render.primitives import PrimitiveType
from myalignment.render.primitives_3d import Point3D, PrimitiveType3D
from myalignment.render.scene import Scene
from myalignment.surface.tin_point import TinPoint
from myalignment.surface.tin_surface import TinSurface
from myalignment.surface.triangle import Triangle


def _bend_and_valve():
    a, b, c, d = (Point3D(*xyz) for xyz in ((0, 0, 10), (4, 0, 10), (4, 5, 10), (4, 10, 10)))
    return (
        PressureNetworkBuilder("Supply").with_parts_list("Water")
        .add_pipe_run(a, b, end_fitting_id="PF_000")
        .add_pipe_run(b, c, end_appurtenance_id="PA_000")
        .add_pipe_run(c, d)
        .add_bend(b, connected_pipe_ids=("PP_001",))
        .add_valve(c, connected_pipe_ids=("PP_002",))
    )


def _surface(right=10):
    return TinSurface.from_points([(-1, -2, 12), (right, -2, 12), (right, 2, 12), (-1, 2, 12)])


def test_bidirectional_connections_accept_pipe_or_node_endpoints():
    network = _bend_and_valve().with_alignment("Main").build()
    assert len(network) == 5 and network.total_pipe_length == 14
    assert network.parts_list_name == "Water" and network.pipes[0].alignment_name == "Main"
    bend = network.get_fitting("PF_000")
    valve = network.get_appurtenance("PA_000")
    assert set(bend.connected_pipe_ids) == {"PP_000", "PP_001"}
    assert set(valve.connected_pipe_ids) == {"PP_001", "PP_002"}
    assert network.get_pipe("PP_001").start_fitting_id == bend.id
    assert network.get_pipe("PP_002").start_appurtenance_id == valve.id
    assert PressureNetworkValidator.is_valid(network)
    assert network.min_cover is None


def test_bend_deflection_compares_3d_axis_turn_with_nominal_angle():
    a, b, c = Point3D(0, 0, 0), Point3D(4, 0, 0), Point3D(4, 0, 5)
    builder = (
        PressureNetworkBuilder()
        .add_bend(b, angle_deg=90, max_deflection_deg=5)
        .add_pipe_run(b, a, start_fitting_id="PF_000")
        .add_pipe_run(c, b, end_fitting_id="PF_000")
    )
    network = builder.build()
    assert network.pipes[1].slope == -math.inf
    assert PressureNetworkValidator.is_valid(network)
    fitting, = network.fittings
    off_angle = replace(network, fittings=(replace(fitting, part=replace(fitting.part, angle_deg=80)),))
    errors = PressureNetworkValidator.validate(off_angle)
    assert any("deflection 10.00°" in error and "exceeds 5°" in error for error in errors)


def test_reducer_tee_and_terminal_appurtenance_port_validation():
    a, b, c, d, e = map(lambda xy: Point3D(*xy, 0), ((0, 0), (3, 0), (6, 0), (10, 0), (6, 4)))
    network = (
        PressureNetworkBuilder()
        .add_fitting(b, FittingPart(fitting_type=FittingType.REDUCER, diameter_mm=200, outlet_diameter_mm=150))
        .add_fitting(c, FittingPart(fitting_type=FittingType.TEE))
        .add_appurtenance(e, AppurtenancePart(appurtenance_type=AppurtenanceType.HYDRANT))
        .add_pipe_run(a, b, diameter_mm=200, end_fitting_id="PF_000")
        .add_pipe_run(b, c, start_fitting_id="PF_000", end_fitting_id="PF_001")
        .add_pipe_run(c, d, start_fitting_id="PF_001")
        .add_pipe_run(c, e, start_fitting_id="PF_001", end_appurtenance_id="PA_000")
        .build()
    )
    assert PressureNetworkValidator.is_valid(network)
    first = replace(network.pipes[0], part=PressurePipePart())
    invalid = replace(network, pipes=(first, *network.pipes[1:]))
    assert any("different nominal diameters" in error for error in PressureNetworkValidator.validate(invalid))
    invalid = replace(network, pipes=network.pipes[:-1])
    errors = PressureNetworkValidator.validate(invalid)
    assert any("expected 3 connected ports" in error for error in errors)
    assert any("expected 1 connected ports" in error for error in errors)


def test_unmatched_duplicate_and_unknown_connections_are_reported():
    location = Point3D(5, 0, 1)
    network = (
        PressureNetworkBuilder()
        .add_bend(location, connected_pipe_ids=("PP_000", "missing"))
        .add_valve(location, connected_pipe_ids=("PP_000",))
        .add_pipe_run(Point3D(0, 0, 1), location)
        .add_pipe_run(location, Point3D(8, 0, 1), start_appurtenance_id="unknown")
        .add_pipe_run(Point3D(5, 0, 2), Point3D(9, 0, 2), start_fitting_id="PF_000")
        .build()
    )
    errors = PressureNetworkValidator.validate(network)
    assert sum("no matching endpoint reference" in error for error in errors) == 2
    assert any("unknown connected pipe" in error for error in errors)
    assert any("unknown start connection" in error for error in errors)
    assert any("does not coincide" in error for error in errors)


def test_cover_checks_interior_tin_breaks_and_outside_ground():
    ground = TinSurface.from_points([
        (x, y, z) for x, z in ((0, 12), (5, 10.5), (10, 12)) for y in (-2, 2)
    ])
    network = (
        PressureNetworkBuilder().add_pipe_run(Point3D(0, 0, 10), Point3D(10, 0, 10))
        .with_surface(ground).build()
    )
    assert network.min_cover == pytest.approx(0.415)
    assert any("cover 0.415 m" in error for error in PressureNetworkValidator.validate(network))
    assert PressureNetworkValidator.is_valid(network, _surface())
    unknown = network.with_cover_from(_surface(9))
    assert unknown.min_cover is None
    assert any("surface coverage is incomplete" in error for error in PressureNetworkValidator.validate(unknown))


def test_cover_requires_continuous_tin_and_handles_vertical_runs():
    points = tuple(TinPoint(x, y, 15) for x in (0, 3, 7, 10) for y in (-1, 1))
    surface = TinSurface(points=points, triangles=(
        Triangle(0, 1, 2), Triangle(1, 2, 3), Triangle(4, 5, 6), Triangle(5, 6, 7),
    ))
    network = (
        PressureNetworkBuilder()
        .add_pipe_run(Point3D(0, 0, 10), Point3D(10, 0, 10))
        .add_pipe_run(Point3D(10, 0, 10), Point3D(10, 0, 12))
        .with_surface(surface).build()
    )
    assert [p.cover for p in network.pipes] == [None, pytest.approx(2.915)]


def test_length_pressure_rating_and_nominal_diameter_checks():
    network = (
        PressureNetworkBuilder().with_pressure_rating(200)
        .add_pipe_run(Point3D(0, 0, 0), Point3D(0.5, 0, 0), diameter_mm=200, end_fitting_id="PF_000")
        .add_pipe_run(Point3D(0.5, 0, 0), Point3D(3, 0, 0), start_fitting_id="PF_000", pressure_rating_psi=200)
        .add_fitting(Point3D(0.5, 0, 0), FittingPart(fitting_type=FittingType.COUPLING))
        .build()
    )
    errors = PressureNetworkValidator.validate(network)
    assert any("length 0.500 m" in error for error in errors)
    assert any("pressure rating" in error for error in errors)
    assert any("incompatible nominal diameter" in error for error in errors)
    with pytest.raises(ValueError, match="pressure_rating_psi"):
        PressurePipePart(pressure_rating_psi=float("nan"))
    with pytest.raises(ValueError, match="distinct"):
        PressureNetworkBuilder().add_pipe_run(Point3D(), Point3D())


def test_render_and_export_plan_3d_and_profile(tmp_path):
    network = _bend_and_valve().build()
    plan = PressureNetworkRenderer.render_plan(Scene(), network)
    assert [p.type for p in plan.primitives] == [PrimitiveType.LINE] * 3 + [
        PrimitiveType.CIRCLE, PrimitiveType.POLYLINE,
    ]
    assert plan.primitives[-1].closed
    scene = PressureNetwork3DRenderer.render(network, z_scale=2)
    assert [p.type for p in scene.primitives] == [PrimitiveType3D.LINE] * 3 + [PrimitiveType3D.POINT] * 2
    assert scene.primitives[-1].points == (Point3D(4, 5, 20),)
    path2d, path3d = tmp_path / "plan.dxf", tmp_path / "scene.dxf"
    DxfWriter(plan).write(path2d)
    Dxf3DWriter(scene).write(path3d)
    assert "C-PRESSURE-APP" in path2d.read_text("cp949")
    assert "C-PRESSURE-APP-3D" in path3d.read_text("cp949")

    axis = AlignmentBuilder("Main").with_pi_coords([(0, 0), (4, 0), (4, 10)]).build()
    projected = PressureNetworkRenderer.profile_projections(network, axis)
    assert [(p.start_station, p.end_station) for p in projected] == [(0, 4), (4, 9), (9, 14)]
    assert projected[-1].elevation == 10
