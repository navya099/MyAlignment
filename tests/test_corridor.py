from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.corridor.corridor import Corridor
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.corridor.region import CorridorRegion


def test_region():
    assembly = (
        AssemblyBuilder()
        .add_both(lambda side: BasicLane(width=3.5, side=side))
        .build()
    )
    r = CorridorRegion(name="R1", start_station=0, end_station=100, assembly=assembly, frequency=10)
    assert r.length == 100
    assert r.station_count == 11


def test_corridor():
    assembly = AssemblyBuilder().add_both(lambda side: BasicLane(width=3.5, side=side)).build()
    r1 = CorridorRegion(name="R1", start_station=0, end_station=100, assembly=assembly)
    r2 = CorridorRegion(name="R2", start_station=100, end_station=200, assembly=assembly)
    col = Corridor(name="C1", regions=(r1, r2))
    assert col.length == 200
    assert col.region_at(150.0) is r2


def test_builder():
    c = (
        CorridorBuilder("본선코리더")
        .add_baseline("BL1", "본선", "FG", 0, 1000)
        .add_region("R1", 0, 500, "표준단면")
        .add_region("R2", 500, 1000, "교량단면")
        .build()
    )
    assert c.name == "본선코리더"
    assert len(c.regions) == 2
    assert c.length == 1000