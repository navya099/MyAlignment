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

## 코리더와 턴아웃 통합 출력

`TurnoutAlignmentBuilder`는 기존 턴아웃 기하의 PC에서 접선 방향으로 분기선을 만듭니다. `TurnoutCorridorBuilder`는 두 선형을 별도 기준선으로 등록하고 본선을 턴아웃 앞·턴아웃·턴아웃 뒤 영역으로 나눕니다. 각 선형에 연결된 설계 종단(FG)이 있으면 기준선에 지정합니다.

```python
from dataclasses import replace

from myalignment.alignment import AlignmentBuilder
from myalignment.assembly import AssemblyBuilder
from myalignment.assembly.subassemblies.rail_track import SingleTrack
from myalignment.corridor.corridor_turnout_preview import CorridorTurnoutPreview
from myalignment.corridor.turnout_corridor_builder import TurnoutCorridorBuilder
from myalignment.profile import ProfileBuilder, ProfileType
from myalignment.turnout.turnout import Turnout
from myalignment.turnout.turnout_alignment_builder import TurnoutAlignmentBuilder
from myalignment.turnout.type import TurnoutSide, TurnoutType

main_grade = ProfileBuilder("Main grade", ProfileType.FG).add_tangent(1000, 1200, 100, 104).build()
main = (
    AlignmentBuilder("Main").with_pi_coords([(0, 0), (200, 0)])
    .with_start_station(1000).with_profile(main_grade).as_rail_alignment().build()
)
turnout = Turnout("T1", TurnoutType("F12", 12, 10, 100), "Main", "Branch", 1040, TurnoutSide.LEFT)
branch = TurnoutAlignmentBuilder.build_branch(main, turnout, branch_length=80)
branch_grade = (
    ProfileBuilder("Branch grade", ProfileType.FG)
    .add_tangent(branch.start_station, branch.end_station, 101, 103).build()
)
branch = replace(branch, profiles=(branch_grade,))
track = AssemblyBuilder().add_center(SingleTrack(gauge=main.gauge)).build()
corridor = TurnoutCorridorBuilder.build(main, branch, turnout, track, track)
scene = CorridorTurnoutPreview.preview_3d(
    main, branch, corridor, turnouts=[turnout],
    dxf_path="corridor-turnout.dxf", html_path="corridor-turnout.html",
)
assert any(item.style.layer == "C-TURNOUT-3D-BRANCH" for item in scene.primitives)
```

통합 장면의 레일 상단은 기준선 종단 표고에 맞춥니다. 별도 분기선이 PC에 접속하면 분기 레일의 끝 표고는 그 기준선 종단에서 읽고, 그 외에는 본선 PF 표고를 사용합니다. 크로스오버 연결 레일도 양쪽 접속 측점의 표고를 보간합니다. 종단이 지정되지 않은 기준선은 표고 0을 사용합니다. 연결 레일의 개별 캔트는 계산하지 않습니다.

특수 횡단면을 지정하려면 `turnout_assembly=`에 어셈블리를 전달합니다. `TurnoutAssembly`는 부호 있는 고정 횡거로 분기 레일을 표시하는 횡단면입니다. 일반적인 통합 뷰에서는 본선 횡단면을 유지하고 분기곡선은 별도의 레일 경로로 배치합니다. [3D HTML 열기](rendering.md#횡단-뷰-3d-dxf와-브라우저-미리보기)

## 링크 코드별 표면

`LinkSurfaceManager.from_corridor()`는 코리더의 링크 코드별 TIN을 만듭니다. 각 횡단면에서 같은 링크를 다음 측점의 링크에 연결하므로, 같은 코드로 분류된 좌우 사면이나 떨어진 코리더 영역 사이의 빈 공간이 유지됩니다. 좌표와 표고에는 기준선, 종단 및 영역 캔트가 반영됩니다.

```python
from myalignment.alignment import AlignmentBuilder
from myalignment.assembly import AssemblyBuilder
from myalignment.assembly.codes import LinkCode
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.corridor import CorridorBuilder
from myalignment.corridor.link_surface_manager import LinkSurfaceManager
from myalignment.corridor.link_surface_quantity import LinkSurfaceQuantity
from myalignment.export.dxf_writer import DxfWriter
from myalignment.render.link_surface_3d_renderer import LinkSurface3DPreview
from myalignment.render.link_surface_renderer import LinkSurfaceRenderer
from myalignment.render.scene import Scene

axis = AlignmentBuilder("Main").with_pi_coords([(0, 0), (30, 0)]).build()
lane = AssemblyBuilder().add_right(BasicLane(width=3, slope=0)).build()
corridor = (
    CorridorBuilder("Road").add_baseline_from_alignment(axis)
    .add_region("Paving", 0, 30, lane, baseline_name=axis.name).build()
)
manager = LinkSurfaceManager.from_corridor(corridor, name="Road", alignments={axis.name: axis})
assert manager.get_by_link_code(LinkCode.PAVEMENT_TOP).surface.area_2d == 90
assert LinkSurfaceQuantity.from_manager(manager).get_by_code(LinkCode.PAVEMENT_BOTTOM).area_3d == 90
DxfWriter(LinkSurfaceRenderer.render(Scene(), manager)).write("link-surfaces.dxf")
scene3d = LinkSurface3DPreview.preview_combined(
    manager, "link-surfaces-3d.html", dxf_path="link-surfaces-3d.dxf", z_scale=2,
)
assert scene3d.metadata["link_surfaces"]
```

- `SINGLE_LINK`는 하나의 `link_code`를, `MULTI_LINK`는 여러 `link_codes`를 한 표면으로 추출합니다.
- `ALL_LINKS`는 코드를 표면별로 분리합니다. `link_codes`를 지정하면 해당 코드만 선택합니다. 수직 링크처럼 평면 투영 면적이 없는 코드는 일괄 추출에서 건너뜁니다.
- `POINT_BASED`는 `point_code`에 해당하는 점을 기존 코리더 TIN 방식으로 추출합니다.
- `overhang_correction=True`는 투영이 정확히 겹치고 한 면이 다른 면보다 높을 때 위쪽 면을 선택합니다. 부분적으로 겹치거나 표고가 서로 교차하는 면은 오류를 반환합니다.

`sample_frequency`를 생략하면 영역에 설정된 간격을 사용합니다. 링크 추출에서 `use_boundary=False`는 경계 객체 생성을 끄며, 삼각형의 연결은 그대로 유지됩니다. 면적 합계는 개별 표면의 합이므로 서로 겹치는 포장층도 각각 집계됩니다.

### 링크 표면 3D 뷰

3D 뷰에서 각 표면의 메쉬와 와이어프레임 레이어를 독립적으로 켜고 끌 수 있습니다. HTML의 색상 범례에는 표면 이름과 평면 면적이 표시됩니다. `LinkSurfaceSpec.color`를 지정하면 기본 코드 색상을 덮어씁니다. `opacity`는 HTML 메쉬에 적용되며 DXF R12 출력은 색상과 레이어를 저장합니다.

`LinkSurface3DPreview.preview_flat(manager, path, z_offset_per_link=5)`는 층마다 Z 간격을 줍니다. `LinkSurface3DScene.from_manager(manager).merge_selected(codes)`는 고른 단일 코드의 장면을 합칩니다. `LinkSurface3DExport.export_all(manager, output_dir)`은 통합 DXF·HTML과 단일 코드별 DXF를 저장합니다. 여러 코드를 병합하거나 점으로 추출한 표면은 통합 장면에 포함됩니다. [3D HTML 열기](rendering.md#횡단-뷰-3d-dxf와-브라우저-미리보기)
