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
