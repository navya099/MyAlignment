# tests/corridor/test_corridor_with_assembly.py
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.corridor.corridor import Corridor
from myalignment.corridor.region import CorridorRegion


def test_corridor_cross_section():
    a = (
        AssemblyBuilder()
        .add_both(lambda side: BasicLane(width=3.5, side=side))
        .build()
    )
    r = CorridorRegion(
        name="R1",
        start_station=0,
        end_station=100,
        assembly=a,
        frequency=10,
    )
    c = Corridor(name="C1", regions=(r,))

    points, links = c.cross_section_at(50.0)
    assert len(points) > 0
    assert len(links) > 0


def test_sample_cross_sections():
    a = AssemblyBuilder().add_both(lambda side: BasicLane(side=side)).build()
    r = CorridorRegion(name="R1", start_station=0, end_station=50, assembly=a, frequency=10)
    c = Corridor(name="C1", regions=(r,))

    sections = c.sample_cross_sections()
    assert len(sections) == 6   # 0, 10, 20, 30, 40, 50