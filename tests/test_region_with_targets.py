# tests/corridor/test_region_with_targets.py
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.assembly.subassemblies.side_slope import SideSlope
from myalignment.corridor.region import CorridorRegion
from myalignment.target.mapping import TargetMapping
from myalignment.target.reference import TargetReference, TargetObjectType
from myalignment.target.target_type import TargetType



def test_region_with_target_mapping():
    assembly = (
        AssemblyBuilder()
        .add_both(lambda side: BasicLane(width=3.5, side=side))
        .add_both(lambda side: SideSlope(slope_ratio=1.5, height=5.0, side=side))
        .build()
    )

    targets = TargetMapping(references=(
        TargetReference(
            logical_name="TargetDTM",
            target_type=TargetType.SURFACE,
            object_type=TargetObjectType.SURFACE,
            object_name="기존지표면",
        ),
    ))

    region = CorridorRegion(
        name="R1",
        start_station=0,
        end_station=100,
        assembly=assembly,
        frequency=10,
        target_mapping=targets,
    )

    points, links = region.cross_section_at(50.0)
    assert len(points) > 0

    # Target이 매핑된 CatchPoint는 is_parametric=True
    catch_points = [p for p in points if p.code.name == "CATCH_POINT"]
    assert all(p.is_parametric for p in catch_points)


def test_region_without_targets():
    assembly = (
        AssemblyBuilder()
        .add_both(lambda side: BasicLane(width=3.5, side=side))
        .add_both(lambda side: SideSlope(slope_ratio=1.5, height=5.0, side=side))
        .build()
    )

    region = CorridorRegion(
        name="R1",
        start_station=0,
        end_station=100,
        assembly=assembly,
        frequency=10,
        target_mapping=TargetMapping.empty(),
    )

    points, links = region.cross_section_at(50.0)
    catch_points = [p for p in points if p.code.name == "CATCH_POINT"]
    assert all(not p.is_parametric for p in catch_points)