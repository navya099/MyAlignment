from dataclasses import replace

import pytest

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.codes import LinkCode
from myalignment.assembly.conditional.branch import ConditionalBranch
from myalignment.assembly.conditional.builder import ConditionalSubassemblyBuilder
from myalignment.assembly.conditional.condition import Condition
from myalignment.assembly.conditional.condition_type import ConditionType
from myalignment.assembly.conditional.conditional_subassembly import ConditionalSubassembly
from myalignment.assembly.conditional.factory import ConditionalAssemblyFactory
from myalignment.assembly.section_context import SectionContext
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.assembly.subassemblies.ditch import VShapeDitch
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.corridor.mesh_mode import MeshMode
from myalignment.profile.profile import ProfileBuilder
from myalignment.section.section_view_builder import SectionViewBuilder
from myalignment.surface.tin_surface import TinSurface
from myalignment.target.mapping import TargetMapping
from myalignment.target.reference import TargetObjectType, TargetReference
from myalignment.target.target_type import TargetType


def _cut_fill():
    return ConditionalSubassembly.cut_fill(BasicLane(name="Fill"), VShapeDitch(name="Cut"))


def _ditch(links):
    return [link for link in links if link.code == LinkCode.DITCH]


def test_conditions_and_first_matching_branch():
    low = BasicLane(name="Low")
    high = BasicLane(name="High")
    default = BasicLane(name="Default")
    condition = Condition(ConditionType.CUSTOM, 1, ">=", "extra")
    conditional = (
        ConditionalSubassemblyBuilder()
        .add_branch(condition, low)
        .add_branch(Condition(ConditionType.CUSTOM, 2, ">", "extra"), high)
        .else_(default)
        .build()
    )
    assert conditional.selected_branch(context=SectionContext(values={"extra": 3})).subassembly is low
    assert conditional.selected_branch().subassembly is default
    assert not condition.evaluate({"extra": float("nan")})
    assert Condition(ConditionType.CUSTOM, 2, "==", "extra").evaluate({"extra": 2.0000001})
    assert Condition(ConditionType.GRADE_THRESHOLD, 0.02).evaluate({"grade": 0.03})
    with pytest.raises(ValueError, match="Unknown comparison"):
        Condition(ConditionType.CUSTOM, comparison="=")
    with pytest.raises(ValueError, match="else"):
        ConditionalSubassembly(branches=(ConditionalBranch(default), ConditionalBranch(default)))


def test_cut_fill_uses_correct_sign_and_origin_elevation():
    conditional = replace(_cut_fill(), base_elevation=10)
    assert conditional.with_surface_elevation(12).selected_branch().name == "Cut"
    assert conditional.with_surface_elevation(9).selected_branch().name == "Fill"
    assert conditional.with_surface_elevation(10).selected_branch().name == "Fill"
    assert conditional.with_surface_elevation(9).selected_branch(origin_z=-2).name == "Cut"
    assert conditional.selected_branch().name == "Fill"
    slope = ConditionalSubassembly.slope_to_surface(VShapeDitch(name="Slope"), BasicLane(), 0.5)
    assert replace(slope, base_elevation=10, surface_elevation=8).selected_branch().name == "Slope"


def test_signed_offset_and_horizontal_target_at_actual_connection():
    mapping = TargetMapping((TargetReference("TargetOffset", TargetType.OFFSET, TargetObjectType.ALIGNMENT, "Edge"),))
    conditional = (
        ConditionalSubassemblyBuilder("Horizontal")
        .add_branch(Condition(ConditionType.TARGET_REACHED), VShapeDitch())
        .else_(BasicLane(width=1))
        .build()
    )
    assembly = (
        AssemblyBuilder().add_both(lambda side: BasicLane(width=3.5, side=side))
        .add_conditional("both", conditional).build()
    )
    context = SectionContext(target_offsets={"Edge": -3.0})
    _, links = assembly.generate_cross_section(mapping, context=context)
    assert len(_ditch(links)) == 2
    assert all(link.start.x <= -3.5 and link.end.x <= -3.5 for link in _ditch(links))
    assert assembly.left_subassemblies[-1].side == -1 and conditional.side == 1
    assert Condition(ConditionType.OFFSET_RANGE, -3, "<").evaluate({"offset": -3.5})


def test_nested_branches_keep_context_and_attachment():
    nested = (
        ConditionalSubassemblyBuilder("Inner")
        .add_branch(Condition(ConditionType.OFFSET_RANGE, -3, "<"), VShapeDitch(width=2))
        .else_(BasicLane(width=1))
        .build()
    )
    outer = ConditionalSubassemblyBuilder("Outer").else_(nested).build()
    _, links = outer.place_at(-4, 2, side_sign=-1, context=SectionContext(station=10))
    assert len(_ditch(links)) == 2
    assert links[-1].end.x == -6 and links[-1].end.z == 2


def test_tin_queries_both_attachments_and_falls_back_outside_coverage():
    axis = AlignmentBuilder("Road").with_pi_coords([(0, 0), (40, 0)]).build()
    grade = ProfileBuilder("Design").add_tangent(0, 40, 10, 10).build()
    tin = TinSurface.from_points([(0, -6, 13), (20, -6, 13), (20, 6, 7), (0, 6, 7)])
    assembly = ConditionalAssemblyFactory.road_with_cut_fill(cut_ditch_width=2)
    mapping = TargetMapping((TargetReference("TargetDTM", object_name="Ground"),))

    def context(station):
        return SectionContext.from_alignment(axis, station, profile=grade, surfaces={"Ground": tin})

    corridor = (
        CorridorBuilder().add_baseline_from_alignment(axis, grade)
        .add_region_with_assembly("Road", 0, 40, assembly, targets=mapping, context_provider=context).build()
    )
    _, links = corridor.cross_section_at(10)
    assert len(_ditch(links)) == 2
    slopes = [link for link in links if link.code == LinkCode.SLOPE]
    right = next(link for link in slopes if link.end.x > 0)
    left = next(link for link in slopes if link.end.x < 0)
    assert right.start.x == pytest.approx(5.5)
    assert right.end.z - right.start.z == pytest.approx(5)
    assert left.end.z - left.start.z == pytest.approx(-5)
    assert not _ditch(corridor.cross_section_at(30)[1])
    assert any(link.code == LinkCode.DITCH.value for link in SectionViewBuilder.build_data(
        corridor, axis, 10, profile=grade,
    ).links)


def test_conditional_station_sampling_splits_loft_at_topology_change():
    axis = AlignmentBuilder("Road").with_pi_coords([(0, 0), (40, 0)]).build()
    grade = ProfileBuilder("Design").add_tangent(0, 40, 10, 10).build()
    mapping = TargetMapping((TargetReference("TargetDTM", object_name="Ground"),))
    assembly = ConditionalAssemblyFactory.road_with_cut_fill()

    def context(station):
        return SectionContext(station, 10, surface_elevation_at=lambda name, offset: 8 if station < 20 else 12)

    corridor = (
        CorridorBuilder().add_baseline_from_alignment(axis, grade)
        .add_region_with_assembly("Road", 0, 40, assembly, targets=mapping, context_provider=context).build()
    )
    samples = corridor.sample_cross_sections()
    assert not _ditch(samples[10][1]) and len(_ditch(samples[20][1])) == 4
    scene = corridor.build_3d_mesh(axis, MeshMode.QUAD_STRIP, profile=grade)
    assert [{point.x for point in primitive.points} for primitive in scene.primitives] == [
        {0, 10}, {20, 30, 40},
    ]


def test_drainage_uses_longitudinal_grade_and_provider_survives_reversal():
    axis = AlignmentBuilder("Road").with_pi_coords([(0, 0), (40, 0)]).build()
    profile = ProfileBuilder("Design").add_tangent(0, 40, 10, 8).build()
    assembly = ConditionalAssemblyFactory.road_with_drainage()
    _, links = assembly.generate_cross_section(context=SectionContext(grade=-0.04))
    assert len(_ditch(links)) == 4
    _, links = assembly.generate_cross_section(context=SectionContext(grade=0.01))
    assert not _ditch(links)

    def context(station):
        return SectionContext.from_alignment(axis, station, profile=profile)

    corridor = (
        CorridorBuilder().add_baseline_from_alignment(axis, profile)
        .add_region("Road", 0, 40, assembly, context_provider=context).build()
    )
    reversed_axis = replace(axis, profiles=(profile,), corridors=(corridor,)).reversed_alignment()
    flipped = reversed_axis.corridors[0]
    assert flipped.regions[0].context_provider(30).grade == pytest.approx(0.05)
    assert len(_ditch(flipped.cross_section_at(30)[1])) == 4
