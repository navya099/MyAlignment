from dataclasses import replace
import math

import pytest

from myalignment.alignment import AlignmentBuilder
from myalignment.assembly import AssemblyBuilder
from myalignment.assembly.codes import PointCode
from myalignment.assembly.subassemblies.rail_track import SingleTrack
from myalignment.assembly.subassemblies.turnout_assembly import TurnoutAssembly
from myalignment.corridor import CorridorBuilder
from myalignment.corridor.corridor_turnout_preview import CorridorTurnoutPreview
from myalignment.corridor.turnout_corridor_builder import TurnoutCorridorBuilder
from myalignment.profile import ProfileBuilder, ProfileType
from myalignment.render.corridor_turnout_3d_renderer import CorridorTurnout3DRenderer
from myalignment.render.crossover_2d_renderer import Crossover2DRenderer
from myalignment.render.crossover_3d_renderer import Crossover3DRenderer
from myalignment.render.turnout_3d_renderer import Turnout3DRenderer
from myalignment.turnout.crossover_builder import CrossoverBuilder
from myalignment.turnout.geometry import TurnoutGeometryCalculator
from myalignment.turnout.turnout import Turnout
from myalignment.turnout.turnout_alignment_builder import TurnoutAlignmentBuilder
from myalignment.turnout.type import TurnoutSide, TurnoutType


def _design(name, start, end, z0, z1):
    return ProfileBuilder(name, ProfileType.FG).add_tangent(start, end, z0, z1).build()


@pytest.fixture
def layout():
    main_grade = _design("Main grade", 1000, 1200, 100, 120)
    main = (
        AlignmentBuilder("Main").with_pi_coords([(0, 0), (200, 0)])
        .with_start_station(1000).with_profile(main_grade).as_rail_alignment(gauge=1.52).build()
    )
    turnout = Turnout("T1", TurnoutType("F12", 12, 10, 100), "Main", "Branch", 1040, TurnoutSide.LEFT)
    branch = TurnoutAlignmentBuilder.build_branch(main, turnout, 80, start_station=1030)
    branch = replace(branch, profiles=(_design("Branch grade", branch.start_station, branch.end_station, 110, 114),))
    assembly = AssemblyBuilder().add_center(SingleTrack(gauge=1.52)).build()
    return main, branch, turnout, assembly


def test_builder_uses_branch_pc_and_keeps_overlapping_station_origins_separate(layout):
    main, branch, turnout, assembly = layout
    geometry = TurnoutGeometryCalculator.calculate(main, turnout, extension=0)
    assert branch.point_at(branch.start_station).distance_to(geometry.pc_point) < 1e-9
    assert branch.tangent_at(branch.start_station) == pytest.approx(geometry.branch_azimuth)
    assert branch.gauge == 1.52
    corridor = TurnoutCorridorBuilder.build(main, branch, turnout, assembly, assembly, turnout_length=500)
    assert [item.start_station for item in corridor.regions] == [1000, 1030, 1040]
    turnout_region = corridor.region_at(1045, baseline_name="Main")
    assert turnout_region.end_station == main.end_station
    assert turnout_region.assembly is assembly
    assert corridor.region_at(1045, baseline_name="Branch").name == "Branch"
    assert {item.profile_name for item in corridor.baselines} == {"Main grade", "Branch grade"}


def test_fixed_section_branch_tracks_support_either_side():
    points, links = TurnoutAssembly(gauge=1.5, branch_offset=-3).generate_geometry()
    rails = {point.code: point.x for point in points}
    assert rails[PointCode.BRANCH_LEFT_RAIL] == -3.75
    assert rails[PointCode.BRANCH_RIGHT_RAIL] == -2.25
    assert all(link.start in points and link.end in points for link in links)


def test_3d_preview_aligns_rail_tops_to_both_profiles_and_exports(layout, tmp_path):
    main, branch, turnout, assembly = layout
    corridor = TurnoutCorridorBuilder.build(main, branch, turnout, assembly, assembly)
    dxf, html = tmp_path / "rail.dxf", tmp_path / "rail.html"
    scene = CorridorTurnoutPreview.preview_full(
        main, branch, corridor, (turnout,), dxf, html, elevation=20,
    )

    def rail(layer):
        return next(item.points for item in scene.primitives if item.style.layer == layer)

    main_rail = rail(Turnout3DRenderer.MAIN_RAIL_LAYER)
    branch_rail = rail(Turnout3DRenderer.BRANCH_RAIL_LAYER)
    assert main_rail[0].z == pytest.approx(124)
    assert main_rail[-1].z > main_rail[0].z
    assert (branch_rail[0].z, branch_rail[-1].z) == pytest.approx((124, 130))
    sections = [point for item in scene.primitives if item.style.layer == "C-CORRIDOR-SECTION" for point in item.points]
    assert any(point.distance_to(branch_rail[-1]) < 1e-8 for point in sections)
    assert any(point.z == pytest.approx(134) for point in sections)
    assert Turnout3DRenderer.BRANCH_RAIL_LAYER in dxf.read_text(encoding="cp949")
    assert "C-CORRIDOR-SECTION" in html.read_text(encoding="utf-8")


def test_crossover_uses_declared_source_order_and_connects_profiles_in_both_views():
    kind = TurnoutType("F12", 12, 17, 373)
    advance = 2 * kind.run + (4.3 - 2 * kind.rise) / math.tan(kind.frog_angle)
    profiles = (_design("First", 0, 500, 100, 110), _design("Second", 0, 500, 125, 130))
    axes = tuple(
        AlignmentBuilder(name).with_pi_coords([(0, y), (500, y)])
        .with_profile(profile).as_rail_alignment().build()
        for name, y, profile in zip(("A", "B"), (0, 4.3), profiles)
    )
    assembly = AssemblyBuilder().add_center(SingleTrack()).build()
    builder = CorridorBuilder()
    for axis, profile in zip(axes, profiles):
        builder.add_baseline_from_alignment(axis, profile)
        builder.add_region(axis.name, 0, 500, assembly, baseline_name=axis.name)
    corridor = builder.build()
    crossover = (
        CrossoverBuilder("X").with_alignments("B", "A").with_turnout_type(kind)
        .at_stations(100, 100 + advance).with_sides(TurnoutSide.RIGHT, TurnoutSide.LEFT)
        .as_double().build()
    )

    scene = CorridorTurnout3DRenderer.render(*axes, corridor, crossovers=[crossover])
    rails = [item for item in scene.primitives if item.style.layer == Crossover3DRenderer.CONNECT_LAYER]
    assert len(rails) == 4
    assert (rails[0].points[0].z, rails[0].points[-1].z) == pytest.approx((
        profiles[1].elevation_at(100), profiles[0].elevation_at(100 + advance),
    ))
    assert (rails[2].points[0].z, rails[2].points[-1].z) == pytest.approx((
        profiles[0].elevation_at(100), profiles[1].elevation_at(100 + advance),
    ))
    plan = CorridorTurnout3DRenderer.render_2d(axes[0], corridor, crossovers=[crossover], branch_alignment=axes[1])
    assert any(item.style.layer == Crossover2DRenderer.DIAMOND_LAYER for item in plan.primitives)


def test_unknown_source_turnout_is_reported(layout):
    main, branch, turnout, assembly = layout
    corridor = TurnoutCorridorBuilder.build(main, branch, turnout, assembly, assembly)
    bad = replace(turnout, source_alignment_name="Unknown")
    with pytest.raises(ValueError, match="Missing alignment: Unknown"):
        CorridorTurnout3DRenderer.render(main, branch, corridor, turnouts=[bad])
