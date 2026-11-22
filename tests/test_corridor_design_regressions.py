import pytest

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.corridor.corridor_3d_renderer import Corridor3DRenderer
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.corridor.surface_builder import CorridorSurfaceSpec
from myalignment.profile.profile import ProfileBuilder
from myalignment.quantity.material import Material
from myalignment.quantity.takeoff import QuantityTakeoff
from myalignment.section.section_view_builder import SectionViewBuilder


@pytest.mark.parametrize("length, widths, expected_stations", [
    (5, (3.5,), [100, 105]),
    (10, (3, 4), [100, 110]),
    (23, (3, 4), [100, 110, 120, 123]),
])
def test_takeoff_integrates_full_region_and_shared_edge_paving_faces(length, widths, expected_stations):
    assembly = AssemblyBuilder().add_right(BasicLane(width=widths[0], slope=0))
    if len(widths) > 1:
        assembly.add_left(BasicLane(width=widths[1], slope=0, side=-1))
    corridor = CorridorBuilder().add_region("Region", 100, 100 + length, assembly.build()).build()
    assert corridor.regions[0].sample_stations() == expected_stations
    takeoff = QuantityTakeoff().add_material(Material("Paving", "PAVEMENT"))
    quantity, = takeoff.compute(corridor, list(corridor.regions)).material_quantities
    assert quantity.total_quantity == pytest.approx(sum(widths) * 0.1 * length)


@pytest.mark.parametrize("use_boundary", [False, True])
def test_parallel_baselines_share_station_range_without_sharing_sections(use_boundary):
    def axis(name, y, z):
        profile = ProfileBuilder("FG").add_tangent(100, 110, z, z).build()
        return (
            AlignmentBuilder(name).with_pi_coords([(0, y), (10, y)])
            .with_start_station(100).with_profile(profile).build()
        )

    a, b = axis("A", 0, 10), axis("B", 20, 30)
    lane = AssemblyBuilder().add_right(BasicLane(width=3, slope=0)).build()
    corridor = (
        CorridorBuilder().add_baseline("BL A", "A", a.profiles[0].name, 100, 110)
        .add_baseline("BL B", "B", b.profiles[0].name, 100, 110)
        .add_region("Region A", 100, 110, lane, baseline_name="BL A")
        .add_region_with_assembly("Region B", 100, 110, lane, baseline_name="BL B")
        .build()
    )
    with pytest.raises(ValueError, match="baseline_name"):
        corridor.region_at(105)
    assert corridor.region_at(105, baseline_name="BL B").name == "Region B"
    assert sorted(corridor.sample_cross_sections(alignment_name="B")) == [100, 110]
    surface = corridor.build_surface(
        CorridorSurfaceSpec(use_boundary=use_boundary), alignments={"A": a, "B": b},
    )
    assert surface.area_2d == pytest.approx(60)
    assert surface.triangle_at(5, 10) is None
    assert surface.elevation_at(5, -1) == pytest.approx(10)
    assert surface.elevation_at(5, 19) == pytest.approx(30)
    scene = Corridor3DRenderer.render_mesh(corridor, b)
    assert scene.primitives and all(p.y >= 17 for mesh in scene.primitives for p in mesh.points)
    assert SectionViewBuilder.build_data(corridor, b, 105).station == 105


def test_explicit_baseline_must_cover_region():
    lane = AssemblyBuilder().add_right(BasicLane()).build()
    builder = CorridorBuilder().add_baseline("BL", "Axis", "", 0, 10)
    with pytest.raises(ValueError, match="BL"):
        builder.add_region("Outside", 0, 12, lane, baseline_name="BL").build()


def test_corridor_plan_area_uses_width_length_and_each_region():
    one_side = AssemblyBuilder().add_right(BasicLane(width=4, slope=0)).build()
    both_sides = (
        AssemblyBuilder().add_left(BasicLane(width=2)).add_right(BasicLane(width=3)).build()
    )
    corridor = (
        CorridorBuilder().add_region("One side", 10, 20, one_side)
        .add_region("Both sides", 30, 38, both_sides).build()
    )
    assert corridor.total_surface_area() == pytest.approx(80)


def test_add_corridor_is_immutable_and_builder_does_not_share_corridor_list():
    from myalignment.alignment.alignment import Alignment
    from myalignment.corridor.corridor import Corridor

    first, second = Corridor("First"), Corridor("Second")
    source = [first]
    original = Alignment(corridors=source)
    source.append(second)
    assert original.corridors == (first,)
    assert original.add_corridor(second).corridors == (first, second)
    assert Alignment().add_corridor(first).corridors == (first,)

    builder = AlignmentBuilder().with_pi_coords([(0, 0), (10, 0)]).with_corridor(first)
    built = builder.build()
    assert builder.with_corridor(second).build().corridors == (first, second)
    assert built.corridors == (first,)


def test_reversed_alignment_mirrors_only_its_baseline_sections_in_world():
    from myalignment.cant.curve import CantCriticalStation, CantCurve, CantPivotMethod
    from myalignment.corridor.cross_section_3d import CrossSection3D

    assembly = AssemblyBuilder().add_right(BasicLane(width=4)).build()
    cant = CantCurve(
        start_station=10, end_station=20, pivot_method=CantPivotMethod.LEFT_RAIL,
        critical_stations=(CantCriticalStation(10, 0.05), CantCriticalStation(20, 0.1)),
    )
    corridor = (
        CorridorBuilder()
        .add_baseline("Owned", "Axis", "", 0, 100)
        .add_baseline("Other", "Parallel", "", 0, 100)
        .add_region_with_assembly("Own", 10, 20, assembly, baseline_name="Owned", cant_curve=cant)
        .add_region("Foreign", 10, 20, assembly, baseline_name="Other").build()
    )
    original = AlignmentBuilder("Axis").with_pi_coords([(0, 0), (100, 0)]).with_corridor(corridor).build()
    reversed_axis = original.reversed_alignment()
    reflected = reversed_axis.primary_corridor
    own = reflected.region_at(85, baseline_name="Owned")
    assert (own.start_station, own.end_station) == (80, 90)
    assert reflected.region_at(15, baseline_name="Other") is corridor.region_by_name("Foreign")
    assert reflected.region_at(15, baseline_name="Owned") is None

    before = CrossSection3D.from_region(original, 15, corridor.region_by_name("Own"))
    after = CrossSection3D.from_region(reversed_axis, 85, own)
    assert after.links == before.links
    for a, b in zip(after.points, before.points):
        assert (a.x, a.y, a.z) == pytest.approx((b.x, b.y, b.z))

    restored = reversed_axis.reversed_alignment().primary_corridor
    assert restored.baselines == corridor.baselines
    assert restored.region_by_name("Own") == corridor.region_by_name("Own")
    assert restored.region_by_name("Foreign") == corridor.region_by_name("Foreign")


def test_offset_remaps_profile_objects_and_allows_attached_corridor_to_render():
    from myalignment.structure.bridge import Bridge

    builder = (
        AlignmentBuilder("Axis").with_pi_coords([(0, 0), (100, 0), (100, 100)])
        .with_radii([None, 30, None]).with_start_station(1000)
    )
    base = builder.build()
    profile = (
        ProfileBuilder("Grade").add_tangent(base.start_station, base.end_station, 10, 30).build()
    )
    assembly = AssemblyBuilder().add_right(BasicLane(width=4)).build()
    corridor = (
        CorridorBuilder().add_baseline("BL", "Axis", profile.name, base.start_station, base.end_station)
        .add_region("Whole", base.start_station, base.end_station, assembly)
        .build()
    )
    corridor = corridor.with_surface(corridor.build_surface(
        CorridorSurfaceSpec(), alignments={"Axis": base}, profiles={profile.name: profile},
    ))
    arc = base.entities[1]
    bridge = Bridge.create("Bridge", arc.start_station + 8, arc.start_station + 10)
    alignment = (
        builder.with_profile(profile).with_structure(bridge).with_corridor(corridor).build()
        .add_station_equation(bridge.start_station, 5000)
    )

    offset = alignment.offset_alignment(-5)
    shifted_arc = offset.entities[1]
    expected_start = shifted_arc.start_station + 8 * 25 / 30
    expected_end = shifted_arc.start_station + 10 * 25 / 30
    remapped = offset.profiles[0]
    assert remapped.end_station == offset.end_station < alignment.end_station
    assert remapped.elevation_at(expected_start) == pytest.approx(profile.elevation_at(bridge.start_station))
    assert remapped.grade_at(expected_start) == pytest.approx(profile.grade_at(bridge.start_station) * 30 / 25)
    assert offset.structures[0].start_station == pytest.approx(expected_start)
    assert offset.structures[0].end_station == pytest.approx(expected_end)
    assert offset.raw_to_display_station(expected_start) == pytest.approx(5000)
    assert offset.primary_corridor.baselines[0].end_station == offset.end_station
    assert offset.primary_corridor.regions[0].end_station == offset.end_station
    assert len(offset.primary_corridor.surfaces) == 0
    assert len(alignment.primary_corridor.surfaces) == 1
    assert Corridor3DRenderer.render_mesh(offset.primary_corridor, offset).primitives
    restored = offset.reversed_alignment().reversed_alignment()
    assert restored.profiles[0].elevation_at(expected_start) == pytest.approx(remapped.elevation_at(expected_start))


def test_alignment_takeoff_counts_only_its_baselines_in_shared_corridor():
    from myalignment.quantity.material import UnitType

    builder = CorridorBuilder()
    for name, width in (("A", 4), ("B", 6)):
        lane = AssemblyBuilder().add_right(BasicLane(width=width, slope=0)).build()
        builder.add_baseline(f"BL {name}", name, "", 0, 10)
        builder.add_region(name, 0, 10, lane, baseline_name=f"BL {name}")
    corridor = builder.build()
    material = Material("Paving", "PAVEMENT", UnitType.AREA)
    for name, area in (("A", 40), ("B", 60), ("Other", 0)):
        axis = (
            AlignmentBuilder(name).with_pi_coords([(0, 0), (10, 0)])
            .with_corridor(corridor).with_metadata(materials=[material]).build()
        )
        assert axis.quantity_takeoff.material_quantities[0].total_quantity == pytest.approx(area)

    corridor_total = QuantityTakeoff([material]).compute(corridor, list(corridor.regions))
    assert corridor_total.material_quantities[0].total_quantity == pytest.approx(100)
