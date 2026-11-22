# 어셈블리와 코리더

`AssemblyBuilder`는 기준점에서 바깥쪽으로 서브어셈블리를 배치합니다. `add_left()`와 `add_right()`의 호출 순서대로 각 측에 구성요소를 붙입니다. 양쪽에 걸친 `SingleTrack`은 `add_center()`를 사용합니다. `BasicLane`의 음수 경사는 진행 방향과 무관하게 해당 차로의 바깥쪽을 낮춥니다.

| 구성요소 | 모듈 | 대표 입력 |
| --- | --- | --- |
| `BasicLane` | `assembly.subassemblies.basic_lane` | 폭, 경사 |
| `Shoulder` | `assembly.subassemblies.shoulder` | 폭, 경사 |
| `SideSlope` | `assembly.subassemblies.side_slope` | 사면비, 높이 |
| `VShapeDitch` | `assembly.subassemblies.ditch` | 폭, 깊이 |
| `SingleTrack` | `assembly.subassemblies.rail_track` | 궤간, 도상 깊이 |

## 여러 기준선에서 영역 선택하기

아래는 같은 STA 범위를 가진 두 선형을 하나의 코리더에 넣는 예제입니다. `baseline_name`은 기준선 식별자이고 `alignment_name`은 선형 이름입니다.

```python
from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.corridor.surface_builder import CorridorSurfaceSpec
from myalignment.section.section_view_builder import SectionViewBuilder

a = AlignmentBuilder("A").with_pi_coords([(0, 0), (20, 0)]).build()
b = AlignmentBuilder("B").with_pi_coords([(0, 10), (20, 10)]).build()
lane = AssemblyBuilder().add_right(BasicLane(width=3, slope=0)).build()
corridor = (
    CorridorBuilder("Shared")
    .add_baseline("BL A", a.name, "", 0, 20)
    .add_baseline("BL B", b.name, "", 0, 20)
    .add_region("Region A", 0, 20, lane, frequency=7, baseline_name="BL A")
    .add_region("Region B", 0, 20, lane, baseline_name="BL B")
    .build()
)
region = corridor.region_at(10, baseline_name="BL A")
assert region.sample_stations() == [0, 7, 14, 20]
section = SectionViewBuilder.build_data(corridor, b, 10, baseline_name="BL B")
assert section.station == 10
surface = corridor.build_surface(CorridorSurfaceSpec(), alignments={a.name: a, b.name: b})
assert surface.area_2d == 120
```

기준선의 종단 이름을 지정하면 선형에 연결된 동일 이름의 종단을 먼저 찾습니다. 표면 추출에서 종단을 별도로 공급할 때는 `profiles={프로파일 이름: 프로파일}`을 전달할 수 있습니다. 종단 이름을 비우면 기준 표고로 0을 사용합니다.

`frequency`는 영역의 기본 샘플 간격이며 시작과 끝 측점을 포함합니다. `CorridorSurfaceSpec.sample_frequency`로 표면 추출 간격을 따로 설정할 수 있습니다. 표면 코드는 `TOP`, `DATUM`, `RAIL_TOP` 등을 제공하며, 사용자 정의 추출에는 `CUSTOM`과 `link_code` 또는 `point_code`를 지정합니다. 어셈블리에 해당 코드가 있어야 표면을 만들 수 있습니다.

선형 객체가 이미 있으면 `add_baseline_from_alignment(alignment, profile)`로 선형 이름과 전체 측점 범위를 가져올 수 있습니다. `name`, `start_station`, `end_station`으로 기준선 식별자와 범위를 지정할 수 있습니다. 종단을 전달한 경우 기준선의 전체 범위를 포함해야 합니다. 종단을 생략하면 기준 표고 0을 사용합니다. 이 방법으로 등록한 기준선도 표면을 추출할 때 선형 이름을 키로 하는 `alignments` 매핑을 사용합니다.

## 타깃 매핑

`TargetMapping`에 논리 이름과 참조 객체의 이름을 등록합니다. 서브어셈블리는 자신이 사용하는 논리 이름으로 타깃을 읽을 수 있습니다. `TargetReference`는 이름과 유형을 보관하므로, 타깃 객체의 기하를 해석하는 방식은 해당 서브어셈블리 구현에 따릅니다.

| 설정 | 기본 서브어셈블리의 동작 |
| --- | --- |
| `OFFSET` 또는 `ELEVATION` | 참조 이름을 저장합니다. `BasicLane`은 생성 시 지정한 폭과 경사를 사용합니다. |
| `SURFACE` | `SideSlope`의 끝점에 `is_parametric` 표시를 남깁니다. 지표면과의 교점 계산 없이 고정 사면비와 높이로 끝점 좌표를 구합니다. |
| 도로 편구배 | 선형에서 임계 측점 값을 조회할 수 있습니다. 코리더 횡단면과 그 횡단면으로 만든 표면에는 어셈블리의 경사가 적용됩니다. |
| 철도 캔트 | 영역에 지정한 `cant_curve`가 해당 측점의 횡단면 표고에 반영됩니다. |

```python
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.target.mapping import TargetMapping
from myalignment.target.reference import TargetObjectType, TargetReference
from myalignment.target.target_type import TargetType

mapping = TargetMapping().add(
    TargetReference("EdgeOffset", TargetType.OFFSET, TargetObjectType.ALIGNMENT, "Edge")
)
assembly = AssemblyBuilder().add_right(BasicLane()).build()
corridor = CorridorBuilder().add_region_with_assembly(
    "Road", 0, 40, assembly, targets=mapping,
).build()
assert corridor.regions[0].target_mapping.get("EdgeOffset").object_name == "Edge"
assert corridor.cross_section_at(20) == assembly.generate_cross_section()
```
