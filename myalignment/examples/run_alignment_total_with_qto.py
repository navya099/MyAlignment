from myalignment.quantity.takeoff import QuantityTakeoff
from myalignment.quantity.material import Material, UnitType
from myalignment.quantity.report import QTOReport
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.assembly.subassemblies.shoulder import Shoulder
from myalignment.corridor.corridor_builder import CorridorBuilder

# 어셈블리 생성
assembly = (
    AssemblyBuilder("표준단면")
    .add_both(lambda side: BasicLane(width=3.5, slope=-0.02, side=side))
    .add_both(lambda side: Shoulder(width=2.0, slope=-0.04, side=side))
    .build()
)

# 코리더 생성
corridor = (
    CorridorBuilder("본선코리더")
    .add_region_with_assembly("일반구간", 0, 500, assembly, frequency=10)
    .build()
)

# 재료 정의
materials = [
    Material(name="아스팔트", shape_code="PAVEMENT", unit_type=UnitType.VOLUME, unit_price=120_000),
    Material(name="기층", shape_code="SHOULDER", unit_type=UnitType.VOLUME, unit_price=80_000),
]

# 수량 산출
qto = QuantityTakeoff(materials=materials)
result = qto.compute(corridor, list(corridor.regions))

# 리포트
report = QTOReport(result=result)
print(report.to_text())