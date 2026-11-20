import pytest
from cadgeom import Point2d

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.codes import LinkCode, PointCode
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.assembly.subassemblies.rail_track import SingleTrack
from myalignment.cant.curve import CantCriticalStation, CantCurve
from myalignment.corridor.corridor import Corridor
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.corridor.surface_builder import CorridorSurfaceSpec
from myalignment.corridor.surface_code import CorridorSurfaceCode
from myalignment.profile.profile import ProfileBuilder
from myalignment.quantity.takeoff import QuantityTakeoff
from myalignment.surface.tin_surface import TinSurface


def test_corridor_surface_uses_world_coordinates_profile_and_spec_frequency():
    alignment = (
        AlignmentBuilder("Axis")
        .with_pi_coords([(100, 200), (100, 230)])
        .with_start_station(1000)
        .build()
    )
    profile = ProfileBuilder("Grade").add_tangent(1000, 1030, 10, 40).build()
    assembly = AssemblyBuilder().add_right(BasicLane(width=3, slope=0)).build()
    corridor = (
        CorridorBuilder("Road")
        .add_baseline("Axis", "Axis", "Grade", 1000, 1030)
        .add_region("First", 1000, 1008, assembly, frequency=30)
        .add_region("Second", 1020, 1028, assembly, frequency=30)
        .build()
    )
    surface = corridor.build_surface(
        CorridorSurfaceSpec(sample_frequency=5),
        alignments={"Axis": alignment},
        profiles={"Grade": profile},
    )

    projection = alignment.project(Point2d(101, 204))
    assert projection.station == pytest.approx(1004)
    assert projection.offset == pytest.approx(1)
    assert surface.name == "Road_Top"
    assert surface.bbox == pytest.approx((100, 200, 103, 228))
    assert sorted({round(p.y) for p in surface.points}) == [200, 205, 208, 220, 225, 228]
    assert surface.elevation_at(101, 204) == pytest.approx(14)
    assert surface.area_2d == pytest.approx(48)
    assert not surface.is_inside_boundary(101, 215)
    assert surface.triangle_at(101, 215) is None
    assert len(surface.boundaries) == 2
    ground = TinSurface.from_points([
        (99, 199, 40), (104, 199, 40), (104, 229, 40), (99, 229, 40),
    ])
    earthwork = QuantityTakeoff().compute_with_surfaces(corridor, surface, ground)
    assert earthwork.cut_volume == pytest.approx(768)
    assert earthwork.fill_volume == pytest.approx(0)
    assert earthwork.net_volume == pytest.approx(768)
    saved = corridor.with_surface(surface)
    assert len(corridor.surfaces) == 0
    assert tuple(saved.surfaces) == (surface,)
    assert saved.add_region(corridor.regions[0]).surfaces.get("Road_Top") is surface
    assert saved.surfaces.get("missing") is None

    with pytest.raises(ValueError, match="Missing profile"):
        corridor.build_surface(CorridorSurfaceSpec(), alignments={"Axis": alignment})


@pytest.mark.parametrize(
    "spec, width, expected_z",
    [
        (CorridorSurfaceSpec(code=CorridorSurfaceCode.RAIL_TOP), 1.6, 0.08),
        (CorridorSurfaceSpec(code=CorridorSurfaceCode.BALLAST), 2.6, -0.17),
        (CorridorSurfaceSpec(code=CorridorSurfaceCode.CUSTOM, point_code=PointCode.EDGE), 2.6, -0.17),
        (CorridorSurfaceSpec(code=CorridorSurfaceCode.CUSTOM, link_code=LinkCode.PAVEMENT,
                             use_boundary=False), 1.6, 0.08),
    ],
)
def test_rail_surface_codes_include_cant(spec, width, expected_z):
    alignment = AlignmentBuilder("Axis").with_pi_coords([(0, 0), (10, 0)]).build()
    assembly = AssemblyBuilder().add_center(SingleTrack(gauge=1.6)).build()
    cant = CantCurve(critical_stations=(CantCriticalStation(cant_value=0.16),))
    corridor = (
        CorridorBuilder()
        .add_baseline("Axis", "Axis", "", 0, 10)
        .add_region_with_assembly("Track", 0, 10, assembly, cant_curve=cant)
        .build()
    )
    surface = corridor.build_surface(spec, alignments={"Axis": alignment})

    assert surface.area_2d == pytest.approx(width * 10)
    assert max(point.z for point in surface.points) == pytest.approx(expected_z)
    assert bool(len(surface.boundaries)) is spec.use_boundary


def test_surface_takeoff_splits_cut_and_fill_in_overlap_of_different_meshes():
    existing = TinSurface.from_points([
        (-1, 0, -1), (1, 0, 1), (-1, 2, -1), (1, 2, 1), (0, 1, 0),
    ])
    design = TinSurface.from_points([
        (-1, 1, 0), (1, 1, 0), (1, 3, 0), (-1, 3, 0),
    ])

    result = QuantityTakeoff().compute_with_surfaces(Corridor(), design, existing)

    assert result.cut_volume == pytest.approx(0.5)
    assert result.fill_volume == pytest.approx(0.5)
    assert result.net_volume == pytest.approx(0)
    assert result.material_quantities == ()
