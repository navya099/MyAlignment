from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.superelevation.critical_station import SuperelevationCriticalStation
from myalignment.superelevation.curve import SuperelevationCurve


def test_alignment_with_superelevation_and_corridor():


    curve = SuperelevationCurve(
        name="곡선1", start_station=100, end_station=300,
        critical_stations=(SuperelevationCriticalStation(station=100),),
    )
    corridor = (
        CorridorBuilder("코리더1")
        .add_region("R1", 0, 500, "표준단면")
        .build()
    )

    a = (
        AlignmentBuilder("본선")
        .with_pi_coords([(0, 0), (500, 0), (1000, 200)])
        .with_radii([None, 800, None])
        .with_corridor(corridor)
        .build()
    )
    assert a.primary_corridor is corridor