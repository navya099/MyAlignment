# tests/quantity/test_takeoff.py
from myalignment.quantity.material import Material, UnitType
from myalignment.quantity.takeoff import QuantityTakeoff
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.corridor.corridor import Corridor
from myalignment.corridor.region import CorridorRegion


def test_takeoff_simple_lane():
    """직선 차로: 체적 = 폭 × 두께 × 길이 (평균단면법)."""
    assembly = (
        AssemblyBuilder()
        .add_both(lambda side: BasicLane(width=3.5, slope=0.0, side=side))
        .build()
    )

    region = CorridorRegion(
        name="R1",
        start_station=0,
        end_station=100,
        assembly=assembly,
        frequency=10,
    )
    corridor = Corridor(name="C1", regions=(region,))

    # 포장 재료
    material = Material(
        name="아스팔트",
        shape_code="PAVEMENT",
        unit_type=UnitType.VOLUME,
        unit_price=100_000,
    )
    qto = QuantityTakeoff(materials=[material])
    result = qto.compute(corridor, [region])

    # 결과 검증
    asph = [mq for mq in result.material_quantities if mq.material_name == "아스팔트"][0]
    assert asph.total_quantity > 0


def test_takeoff_no_materials():
    """재료 없음 → 수량 0."""
    assembly = (
        AssemblyBuilder()
        .add_both(lambda side: BasicLane(width=3.5, side=side))
        .build()
    )
    region = CorridorRegion(
        name="R1", start_station=0, end_station=100,
        assembly=assembly, frequency=10,
    )
    corridor = Corridor(name="C1", regions=(region,))

    qto = QuantityTakeoff()   # 재료 없음
    result = qto.compute(corridor, [region])
    assert len(result.material_quantities) == 0
    assert result.total_cost == 0.0
