# 수량 산출

## 코리더 재료 물량

`Material.shape_code`는 `ShapeCode`의 Enum 이름을 문자열로 받습니다. 포장은 `"PAVEMENT"`를 사용합니다. `AREA`는 중복을 제거한 횡단 폭을 적분한 평면 면적이고, `VOLUME`은 인접 측점의 단면적 평균에 구간 길이를 곱해 더한 체적입니다.

```python
from math import isclose

from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.quantity.material import Material, UnitType
from myalignment.quantity.report import QTOReport
from myalignment.quantity.takeoff import QuantityTakeoff

lane = AssemblyBuilder().add_right(BasicLane(width=4, slope=0)).build()
corridor = CorridorBuilder("Road").add_region("Paving", 0, 10, lane).build()
materials = [
    Material("Paving area", "PAVEMENT", UnitType.AREA, unit_price=5000),
    Material("Paving volume", "PAVEMENT", UnitType.VOLUME),
]
result = QuantityTakeoff(materials).compute(corridor, list(corridor.regions))
area, volume = result.material_quantities
assert isclose(area.total_quantity, 40)
assert isclose(volume.total_quantity, 4)
assert isclose(result.total_cost, 200000)
print(QTOReport(result=result).to_text())
```

`QuantityTakeoff.compute()`는 전달한 영역을 집계합니다. 공유 코리더에서 선형별 수량을 가져오려면 `Alignment.quantity_takeoff`를 사용합니다. 이 속성은 첫 코리더에서 해당 선형의 기준선을 사용하는 영역과 `alignment.metadata["materials"]`의 재료를 읽습니다.

## 원지형과 설계면의 절·성토량

```python
from math import isclose

from myalignment.corridor.corridor import Corridor
from myalignment.quantity.takeoff import QuantityTakeoff
from myalignment.surface.tin_surface import TinSurface

existing = TinSurface.from_points([(0, 0, 105), (10, 0, 105), (10, 10, 105), (0, 10, 105)])
design = TinSurface.from_points([(0, 0, 100), (10, 0, 100), (10, 10, 100), (0, 10, 100)])
cut, fill = existing.volume_between(design)
result = QuantityTakeoff().compute_with_surfaces(Corridor(), design, existing)
assert isclose(cut, 500) and isclose(fill, 0)
assert isclose(result.net_volume, 500)
```

공통 평면 영역의 표고 차이를 적분하며, 절토와 성토가 한 면에 섞인 경우도 나눠 계산합니다. 균일한 기준 표고는 `existing.volume_above_elevation(100)`으로 비교할 수 있습니다. `net_volume`은 절토량에서 성토량을 뺀 값입니다.
