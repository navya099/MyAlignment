import pytest

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.codes import LinkCode, PointCode
from myalignment.assembly.subassemblies.rail_track import SingleTrack
from myalignment.assembly.subassemblies.side_slope import SideSlope
from myalignment.cant.curve import CantCriticalStation, CantCurve, CantPivotMethod
from myalignment.corridor.rail_corridor_builder import RailCorridorBuilder
from myalignment.target.mapping import TargetMapping
from myalignment.target.reference import TargetReference
from myalignment.target.target_type import TargetType


@pytest.mark.parametrize(
    "pivot, left_z, right_z",
    [
        (CantPivotMethod.CENTERLINE, -0.0525, 0.0525),
        (CantPivotMethod.LEFT_RAIL, 0.0, 0.105),
        (CantPivotMethod.RIGHT_RAIL, -0.105, 0.0),
    ],
)
def test_rail_corridor_cross_section(pivot, left_z, right_z):
    gauge = 1.6
    rail = (
        AlignmentBuilder("Main")
        .with_pi_coords([(0, 0), (500, 0)])
        .as_rail_alignment(gauge=gauge)
        .build()
    )
    cant = CantCurve(
        start_station=200,
        end_station=400,
        pivot_method=pivot,
        critical_stations=(
            CantCriticalStation(station=200),
            CantCriticalStation(station=300, cant_value=0.105, is_full_cant=True),
            CantCriticalStation(station=400),
        ),
    )
    assembly = (
        AssemblyBuilder("Track")
        .add_center(SingleTrack(gauge, 0.3))
        .add_both(lambda side: SideSlope(height=3, side=side))
        .build()
    )
    targets = TargetMapping.empty().add(
        TargetReference("TargetDTM", TargetType.SURFACE, object_name="Existing ground")
    )
    corridor = (
        RailCorridorBuilder("Main corridor")
        .add_rail_baseline(rail, "Design profile", 0, 500)
        .add_rail_region("Cant region", 100, 450, assembly, cant, targets=targets)
        .add_rail_region("Approach", 0, 95, assembly)
        .build()
    )
    assert corridor.baselines[0].alignment_name == rail.name
    assert corridor.baselines[0].profile_name == "Design profile"
    assert [region.name for region in corridor.regions] == ["Approach", "Cant region"]
    region = corridor.region_at(300)
    assert region.target_mapping is targets
    assert region.frequency == 5
    assert region.cant_curve is cant

    points, links = corridor.cross_section_at(300)
    neighbors = [p for p in points if p.code is PointCode.CATCH_POINT]
    assert len(neighbors) == 2
    assert all(point.is_parametric for point in neighbors)
    assert sorted(p.x for p in neighbors) == pytest.approx([-5.8, 5.8])
    rails = [p for p in points if p.code in (PointCode.LEFT_RAIL, PointCode.RIGHT_RAIL)]
    assert [(p.code, p.x) for p in rails] == [
        (PointCode.LEFT_RAIL, -gauge / 2),
        (PointCode.RIGHT_RAIL, gauge / 2),
    ]
    assert [p.z for p in rails] == pytest.approx([left_z, right_z])
    rail_link = next(link for link in links if link.code is LinkCode.PAVEMENT)
    assert rail_link.start is rails[0]
    assert rail_link.end is rails[1]
    slopes = [link for link in links if link.code is LinkCode.SLOPE]
    assert slopes[0].start.x == pytest.approx(-1.3)
    assert slopes[1].end.x == pytest.approx(1.3)
    assert slopes[2].start.z == pytest.approx(slopes[1].end.z)
    assert slopes[3].start.z == pytest.approx(slopes[0].start.z)

    for station, expected in [(150, 0), (250, 0.0525), (350, 0.0525), (425, 0)]:
        _, links = corridor.cross_section_at(station)
        rail_link = next(link for link in links if link.code is LinkCode.PAVEMENT)
        assert rail_link.end.z - rail_link.start.z == pytest.approx(expected)


def test_rail_builder_rejects_road_baseline():
    road = AlignmentBuilder("Road").with_pi_coords([(0, 0), (100, 0)]).build()

    with pytest.raises(ValueError, match="Rail Alignment"):
        RailCorridorBuilder().add_rail_baseline(road, "Profile", 0, 100)
