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


def test_object_baseline_uses_raw_station_range_and_profile_for_surface():
    alignment = (
        AlignmentBuilder("Axis").with_pi_coords([(0, 0), (10, 0)]).with_start_station(100).build()
        .add_station_equation(105, 200)
    )
    profile = ProfileBuilder("FG").add_tangent(100, 110, 10, 12).build()
    assembly = AssemblyBuilder().add_right(BasicLane(width=3, slope=0)).build()
    corridor = (
        CorridorBuilder().add_baseline_from_alignment(alignment, profile)
        .add_region("Region", 100, 110, assembly, baseline_name="Axis").build()
    )

    baseline, = corridor.baselines
    assert (baseline.name, baseline.alignment_name, baseline.profile_name) == ("Axis", "Axis", "FG")
    assert (baseline.start_station, baseline.end_station) == (100, 110)
    surface = corridor.build_surface(
        CorridorSurfaceSpec(), alignments={"Axis": alignment}, profiles={"FG": profile},
    )
    assert surface.elevation_at(5, -1) == pytest.approx(11)


def test_object_baseline_validates_range_before_registering():
    alignment = AlignmentBuilder("Axis").with_pi_coords([(0, 0), (10, 0)]).build()
    profile = ProfileBuilder("FG").add_tangent(2, 8, 10, 12).build()
    builder = CorridorBuilder()
    with pytest.raises(ValueError, match="선형의 측점 범위"):
        builder.add_baseline_from_alignment(alignment, end_station=11)
    with pytest.raises(ValueError, match="종단 이름과 측점 범위"):
        builder.add_baseline_from_alignment(alignment, profile)

    builder.add_baseline_from_alignment(alignment, profile, start_station=2, end_station=8)
    with pytest.raises(ValueError, match="이미 사용 중"):
        builder.add_baseline_from_alignment(alignment)
    baseline, = builder.build().baselines
    assert (baseline.start_station, baseline.end_station) == (2, 8)


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


def test_pi_edit_and_rename_refresh_the_attached_corridor_and_preserve_owner_selection():
    from myalignment.quantity.material import UnitType
    from myalignment.structure.bridge import Bridge

    builder = (
        AlignmentBuilder("Axis").with_pi_coords([(0, 0), (100, 0), (100, 100)])
        .with_radii([None, 20, None])
    )
    base = builder.build()
    profile = ProfileBuilder("Grade").add_tangent(0, base.end_station, 0, 10).build()
    lane = AssemblyBuilder().add_right(BasicLane(width=4, slope=0)).build()
    corridor = (
        CorridorBuilder().add_baseline("BL", "Axis", "Grade", 0, base.end_station)
        .add_region("Full", 0, base.end_station, lane).build()
    )
    existing_bridge = Bridge.create("Existing", base.end_station - 10, base.end_station)
    added_bridge = Bridge.create("New", 10, 20)
    original = (
        builder.with_profile(profile).with_structure(existing_bridge).with_corridor(corridor)
        .with_metadata(materials=[Material("Paving", "PAVEMENT", UnitType.AREA)]).build()
    )
    with original.modify() as tx:
        tx.rename("Renamed").update_pi_and_radius(1, radius=40).add_structure(added_bridge)

    updated = tx.result
    assert updated.end_station < original.end_station
    assert updated.primary_corridor.baselines[0].alignment_name == "Renamed"
    assert updated.primary_corridor.regions[0].end_station == updated.end_station
    assert updated.profiles[0].end_station == updated.end_station
    assert updated.profiles[0].elevation_at(updated.end_station) == pytest.approx(10)
    assert updated.structures[0] is added_bridge
    assert updated.structures[1].end_station == updated.end_station
    assert updated.quantity_takeoff.material_quantities[0].total_quantity == pytest.approx(4 * updated.length)
    assert Corridor3DRenderer.render_mesh(updated.primary_corridor, updated).primitives
    assert original.primary_corridor.baselines[0].alignment_name == "Axis"
    assert original.primary_corridor.end_station == original.end_station


def test_rename_preserves_quantity_in_shared_corridor_and_updates_alignment_targets():
    from myalignment.quantity.material import UnitType
    from myalignment.target.mapping import TargetMapping
    from myalignment.target.reference import TargetObjectType, TargetReference
    from myalignment.target.target_type import TargetType

    lane = AssemblyBuilder().add_right(BasicLane(width=4, slope=0)).build()
    targets = TargetMapping((TargetReference("Width", TargetType.OFFSET, TargetObjectType.ALIGNMENT, "A"),))
    corridor = (
        CorridorBuilder().add_baseline("BL A", "A", "", 0, 10)
        .add_baseline("BL B", "B", "", 0, 10)
        .add_region_with_assembly("A region", 0, 10, lane, targets=targets, baseline_name="BL A")
        .add_region("B region", 0, 10, lane, baseline_name="BL B").build()
    )
    a = (
        AlignmentBuilder("A").with_pi_coords([(0, 0), (10, 0)]).with_corridor(corridor)
        .with_metadata(materials=[Material("Paving", "PAVEMENT", UnitType.AREA)]).build()
    )
    with a.modify() as tx:
        tx.rename("New A")
    renamed = tx.result
    new_corridor = renamed.primary_corridor
    assert tuple(b.alignment_name for b in new_corridor.baselines) == ("New A", "B")
    assert new_corridor.region_by_name("A region").target_mapping.get("Width").object_name == "New A"
    assert renamed.quantity_takeoff.material_quantities[0].total_quantity == a.quantity_takeoff.material_quantities[0].total_quantity
    assert Corridor3DRenderer.render_mesh(new_corridor, renamed).primitives


@pytest.mark.parametrize("new_name", ["FG original", "FG revised"])
def test_replacing_profile_updates_references_and_invalidates_surface_cache(new_name):
    from myalignment.profile.profiletype import ProfileType
    from myalignment.target.mapping import TargetMapping
    from myalignment.target.reference import TargetObjectType, TargetReference
    from myalignment.target.target_type import TargetType

    original_profile = ProfileBuilder("FG original", ProfileType.FG).add_tangent(0, 10, 20, 21).build()
    replacement = ProfileBuilder(new_name, ProfileType.FG).add_tangent(0, 10, 25, 26).build()
    lane = AssemblyBuilder().add_right(BasicLane(width=4, slope=0)).build()
    targets = TargetMapping((
        TargetReference("Elevation", TargetType.ELEVATION, TargetObjectType.PROFILE, original_profile.name),
    ))
    corridor = (
        CorridorBuilder().add_baseline("A", "Axis", original_profile.name, 0, 10)
        .add_baseline("B", "Other", original_profile.name, 0, 10)
        .add_region_with_assembly("Axis lane", 0, 10, lane, targets=targets, baseline_name="A")
        .add_region_with_assembly("Other lane", 0, 10, lane, targets=targets, baseline_name="B")
        .build()
    )
    builder = AlignmentBuilder("Axis").with_pi_coords([(0, 0), (10, 0)]).with_profile(original_profile)
    axis = builder.build()
    other = AlignmentBuilder("Other").with_pi_coords([(0, 10), (10, 10)]).with_profile(original_profile).build()
    surface = corridor.build_surface(CorridorSurfaceSpec(), alignments={"Axis": axis, "Other": other})
    axis = axis.add_corridor(corridor.with_surface(surface))

    with axis.modify() as tx:
        tx.update_profile(replacement)
    revised = tx.result
    new_corridor = revised.primary_corridor

    assert revised.fg_profile is replacement
    assert new_corridor.baselines[0].profile_name == new_name
    assert new_corridor.baselines[1] is corridor.baselines[1]
    assert new_corridor.region_by_name("Axis lane").target_mapping.get("Elevation").object_name == new_name
    assert new_corridor.region_by_name("Other lane") is corridor.region_by_name("Other lane")
    assert not new_corridor.surfaces
    assert axis.primary_corridor.surfaces.get(surface.name) is surface
    scene = Corridor3DRenderer.render_mesh(new_corridor, revised)
    assert scene.primitives
    assert min(p.z for mesh in scene.primitives for p in mesh.points) == pytest.approx(24.9)
    rebuilt = new_corridor.build_surface(CorridorSurfaceSpec(), alignments={"Axis": revised, "Other": other})
    assert rebuilt.elevation_at(5, -1) == pytest.approx(25.5)
