# 어셈블리와 코리더

`AssemblyBuilder`는 기준점에서 바깥쪽으로 서브어셈블리를 배치합니다. `add_left()`와 `add_right()`의 호출 순서대로 각 측에 구성요소를 붙입니다. 양쪽에 걸친 `SingleTrack`은 `add_center()`를 사용합니다. `BasicLane`의 음수 경사는 진행 방향과 무관하게 해당 차로의 바깥쪽을 낮춥니다.

| 구성요소 | 모듈 | 대표 입력 |
| --- | --- | --- |
| `BasicLane` | `assembly.subassemblies.basic_lane` | 폭, 경사 |
| `Shoulder` | `assembly.subassemblies.shoulder` | 폭, 경사 |
| `SideSlope` | `assembly.subassemblies.side_slope` | 사면비, 높이 |
| `VShapeDitch` | `assembly.subassemblies.ditch` | 폭, 깊이 |
| `CurbSubassembly` | `assembly.subassemblies.curb` | 연석 유형, 높이, 폭, 구배 |
| `SidewalkSubassembly` | `assembly.subassemblies.sidewalk` | 폭, 구배, 두께 |
| `CurbAndSidewalkSubassembly` | `assembly.subassemblies.curb_and_sidewalk` | 연석과 보도 제원 |
| `CurbAndGutterSubassembly` | `assembly.subassemblies.curb_and_gutter` | 연석 제원, 측구 폭과 깊이 |
| `SingleTrack` | `assembly.subassemblies.rail_track` | 궤간, 도상 깊이 |

## 연석·측구·보도

`CurbSidewalkFactory.urban_road()`는 양쪽에 차로, 갓길, 연석·보도, 사면을 차례로 배치합니다. `lane_count`는 한쪽 차로 수입니다. `urban_road_with_drainage()`는 양쪽 차로와 연석 사이에 V형 배수로를 배치합니다.

```python
from myalignment.assembly.codes import PointCode
from myalignment.assembly.subassemblies import CurbSidewalkFactory
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.quantity.material import Material
from myalignment.quantity.takeoff import QuantityTakeoff

assembly = CurbSidewalkFactory.urban_road(lane_count=1, sidewalk_width=2.0)
corridor = (
    CorridorBuilder("Urban Road")
    .add_region("Road", 0, 100, assembly, frequency=10)
    .build()
)
points, _ = corridor.cross_section_at(50)
outside = [p.x for p in points if p.code is PointCode.SIDEWALK_OUT]
assert sorted(round(offset, 2) for offset in outside) == [-6.15, 6.15]

takeoff = QuantityTakeoff([Material("Sidewalk concrete", "SIDEWALK")])
quantity, = takeoff.compute(corridor, list(corridor.regions)).material_quantities
assert round(quantity.total_quantity, 2) == 40.0
```

- 개별 부품은 `AssemblyBuilder`에 추가합니다. 연석 다음 부품은 연석 후면 하단에, 보도 다음 부품은 보도 외측 포장 상단에 연결됩니다. 통합 부품에 `SidewalkParams(include_curb=False)`를 전달하면 보도만 생성합니다.
- `CurbType`은 수직·경사·마운터블·방호형의 기본 전면 형상을 제공합니다. `CurbParams.face_slope`를 지정하면 전면 높이 1m당 바깥쪽 수평 이동량을 직접 제어할 수 있습니다. `top_slope`와 보도의 `slope`는 바깥쪽으로 향하는 구배입니다.
- 차로 끝에서 연석 전면까지 내려가는 단일 측구는 `CurbAndGutterSubassembly`를 사용합니다. `gutter_depth`는 차로 끝과 측구 최저점의 표고차입니다.

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

## 코리더 피처라인 추출

`Corridor.extract_feature_lines()`는 추출 결과를 `feature_lines`에 등록한 새 코리더를 반환합니다. `alignments`는 기준선의 선형 이름을 키로 사용합니다. 기준선에 연결한 종단이 선형 자체에 등록되어 있지 않으면 `profiles`에 종단 이름으로 전달합니다. 기준선에 종단 이름이 없으면 기준 표고는 0m입니다.

```python
from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.codes import PointCode
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.corridor.feature_line_spec import CorridorFeatureLineSpec
from myalignment.export.dxf_writer import DxfWriter
from myalignment.render.feature_line_2d_renderer import FeatureLine2DRenderer
from myalignment.render.feature_line_3d_renderer import FeatureLine3DPreview
from myalignment.render.scene import Scene

axis = AlignmentBuilder("Main").with_pi_coords([(0, 0), (40, 0)]).build()
lane = AssemblyBuilder().add_both(lambda side: BasicLane(side=side)).build()
corridor = (
    CorridorBuilder("Road").add_baseline_from_alignment(axis)
    .add_region("Paving", 0, 40, lane, frequency=5).build()
)
specs = [
    CorridorFeatureLineSpec("Left edge", point_code=PointCode.LANE_EDGE, side="left", color=1),
    CorridorFeatureLineSpec("Fixed offset", "offset", offset=1.5, color=3),
]
manager = corridor.extract_feature_lines(specs, alignments={axis.name: axis}).feature_lines
assert manager.get("Left edge").point_at_station(12) is not None
DxfWriter(FeatureLine2DRenderer.render(Scene(), manager)).write("feature-lines-plan.dxf")
FeatureLine3DPreview.preview(manager, "feature-lines.html", "feature-lines-3d.dxf")
```

- `point_code`는 지정 코드의 점을 사용합니다. `left`와 `right`는 해당 방향의 가장 바깥 점을, `both`는 중심선에 가장 가까운 점을 선택합니다. 양측 선이 필요하면 좌우 사양을 하나씩 지정합니다.
- `link_code`는 링크의 시작점 또는 끝점을 사용합니다. `use_start`와 `use_end`를 함께 켜면 중점을 사용합니다. `offset`은 지정 횡거에서 횡단 링크를 보간하고, 여러 표고가 겹치면 가장 높은 점을 선택합니다.
- `specs`를 생략하고 `standard="road"` 또는 `standard="rail"`을 사용하면 표준 코드로 추출합니다. 코드가 없는 선은 빈 결과가 됩니다. `sample_frequency`로 영역 기본 표본 간격을 덮어쓰고 `baseline_name`으로 기준선을 선택할 수 있습니다.
- `segments`는 코드 누락, 영역 공백, 좌표가 달라지는 경계에서 선을 분리합니다. `point_at_station()`에 여러 좌표가 있는 측점을 전달하면 오류가 발생합니다. 기준선이 겹치는 경우 `baseline_name`으로 범위를 좁힐 수 있습니다.

## 코리더 사면 패턴

`Corridor.generate_slope_patterns()`은 영역의 `LinkCode.SLOPE` 링크에 해치, 격자, 계단, 말뚝 또는 소단을 배치합니다. 기준선의 평면선형과 종단을 사용하고 횡단면의 캔트를 반영합니다. 패턴은 도면에 표시할 형상이며 코리더 횡단이나 TIN을 변경하지 않습니다.

```python
from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.assembly.subassemblies.side_slope import SideSlope
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.corridor.slope_pattern_style import SlopePatternStyle
from myalignment.export.dxf_writer import DxfWriter
from myalignment.render.scene import Scene
from myalignment.render.section_view_renderer import SectionViewRenderer
from myalignment.render.slope_pattern_2d_renderer import SlopePattern2DRenderer
from myalignment.render.slope_pattern_3d_renderer import SlopePattern3DPreview
from myalignment.section.section_view_builder import SectionViewBuilder

axis = AlignmentBuilder("Main").with_pi_coords([(0, 0), (40, 0)]).build()
assembly = (
    AssemblyBuilder().add_both(lambda side: BasicLane(side=side))
    .add_both(lambda side: SideSlope(side=side, height=4)).build()
)
corridor = (
    CorridorBuilder("Road").add_baseline_from_alignment(axis)
    .add_region("Slopes", 0, 40, assembly, frequency=5).build()
)
patterns = corridor.generate_slope_patterns(SlopePatternStyle.stakes_style(), alignments={axis.name: axis})
assert patterns.total_elements() > 0
DxfWriter(SlopePattern2DRenderer.render(Scene(), patterns)).write("slope-plan.dxf")
SlopePattern3DPreview.preview(patterns, "slope.html", "slope-3d.dxf")
data = SectionViewBuilder.build_data(corridor, axis, 20)
section = SectionViewRenderer.render(
    Scene(), data, slope_patterns=patterns.at_station(20, baseline_name=axis.name, region_name="Slopes"),
)
DxfWriter(section).write("slope-section.dxf")
```

- 기본 패턴은 해치입니다. `grid_style()`, `steps_style()`, `stakes_style()`, `berms_style()`로 바꿀 수 있고, `SlopePatternType.NONE`을 선택하면 패턴을 끕니다.
- 간격과 크기의 단위는 미터입니다. 표본 측점은 영역 간격을 따르며 격자는 `spacing_horizontal`을 사용합니다. `sample_frequency`를 전달하면 표본 측점 간격을 직접 지정할 수 있습니다. 해치와 격자의 종방향 선은 같은 영역 안에서 연결됩니다.
- 계단 높이와 폭은 각각 단의 최대 높이와 폭입니다. 소단의 높이 간격은 `berm_interval`입니다. 말뚝 간격은 사면을 따라 측정하고 말뚝은 수직으로 세웁니다. 구배는 선형에 가까운 쪽에서 바깥쪽으로 계산합니다.
- 기준선의 종단이 선형에 등록되지 않은 경우 `profiles`에 종단 이름으로 전달합니다. 여러 기준선이나 인접 영역이 횡단 측점을 공유할 경우 `at_station()`의 `baseline_name`과 `region_name`으로 표시할 패턴을 선택합니다.

## 코리더 영역 편집과 롤백

`Corridor.edit(commands)`는 편집 명령을 순서대로 적용해 새 코리더를 반환합니다. `Corridor.transaction()`은 같은 작업을 메서드 체이닝으로 예약합니다. `with` 블록이 정상 종료되면 `tx.result`에서 결과를 얻습니다. 블록이나 명령에서 오류가 발생하면 예외가 전달되며 `tx.result`는 원본을 가리킵니다.

```python
from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.corridor.rehab.report import CorridorRehabReport

axis = AlignmentBuilder("Main").with_pi_coords([(0, 0), (100, 0)]).build()
lane = AssemblyBuilder().add_both(lambda side: BasicLane(side=side)).build()
corridor = (
    CorridorBuilder("Road").add_baseline_from_alignment(axis)
    .add_region("Paving", 0, 100, lane).build()
)

with corridor.transaction() as tx:
    tx.split_region("Paving", 60).update_frequency("Paving_B", 5)
    tx.update_assembly("Paving_B", AssemblyBuilder().add_right(BasicLane(width=4)).build())

edited = tx.result
assert [region.name for region in edited.regions] == ["Paving_A", "Paving_B"]
assert corridor.regions[0].end_station == 100
print(CorridorRehabReport.from_history(tx.history).to_text())
```

- `CorridorEditCommand`로 범위, 샘플 간격, 어셈블리, 타깃을 바꾸거나 영역을 분할·병합·추가·삭제할 수 있습니다. 같은 이름이 여러 기준선에 있으면 `baseline_name`을 지정합니다.
- 각 명령의 결과는 기준선의 범위 안에 있어야 합니다. 같은 기준선에서 내부 구간이 겹칠 수 없으므로 공유 경계를 이동할 때는 한쪽 범위를 먼저 줄이고 다른 쪽을 늘립니다. 단면 조회와 샘플 조회는 공유 경계에서 먼저 시작한 영역을 사용합니다.
- 분할은 `_A`, `_B` 이름을 만들고 원래 영역의 어셈블리, 타깃, 캔트를 유지합니다. 같은 기준선에서 인접하고 캔트 및 배치 방향이 호환되는 영역을 병합하면 앞쪽 영역의 설정과 `_merged` 이름을 사용합니다.
- 편집으로 영역이 바뀌면 등록된 TIN 표면과 피처라인을 비웁니다. 필요에 따라 `build_surface()`와 `extract_feature_lines()`로 새 영역에서 다시 계산합니다. 트랜잭션 이력의 `snapshot_before`는 되돌리기에 사용할 수 있습니다.

## 코리더 3D 메시 모드

`Corridor.build_3d_mesh()`는 영역별 횡단을 샘플링해 3D 메시 장면을 반환합니다. 기준선에 지정한 종단과 영역의 캔트를 반영합니다. `sample_frequency`를 생략하면 영역별 표본 간격을 사용합니다.

- `MeshMode.LINK_BASED`는 기본 모드입니다. 링크 코드마다 레이어를 만들고, HTML 뷰어 범례에서 각 레이어를 켜고 끌 수 있습니다.
- `MeshMode.QUAD_STRIP`은 인접 횡단의 링크로 만든 사각형을 삼각형 두 개로 나누어 영역당 하나의 메시로 묶습니다.
- `MeshMode.TRIANGULATED`는 영역의 샘플 점을 Delaunay 삼각분할하고 좌우 경계로 자릅니다. 같은 XY에 표고가 여러 개 있으면 가장 높은 점으로 TIN을 만듭니다. 수직 면이나 하부 층까지 표시하려면 링크 기반이나 사각 스트립 모드를 사용합니다.

```python
from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.corridor.mesh_mode import MeshMode
from myalignment.render.corridor_3d_mesh_renderer import Corridor3DMeshPreview

axis = AlignmentBuilder("Main").with_pi_coords([(0, 0), (40, 0)]).build()
lane = AssemblyBuilder().add_both(lambda side: BasicLane(side=side)).build()
corridor = (
    CorridorBuilder("Road").add_baseline_from_alignment(axis)
    .add_region("Paving", 0, 40, lane, frequency=5).build()
)
top = corridor.build_3d_mesh(axis, MeshMode.TRIANGULATED)
assert top.primitives
Corridor3DMeshPreview.preview(
    corridor, axis, "corridor-mesh.html", "corridor-mesh.dxf", mode=MeshMode.LINK_BASED,
)
```

같은 선형을 여러 기준선에서 쓰면 `baseline_name`으로 범위를 지정합니다. `profile`은 기준선의 종단을 덮어쓰며, `z_offset`은 모든 점의 표고에 더합니다. HTML 미리보기는 기존 Three.js 뷰어를 사용하고, DXF의 메시 면은 `3DFACE`로 저장됩니다.

## 조건부 서브어셈블리

`ConditionalSubassembly`는 현재 배치 접점에서 조건을 순서대로 평가하고 처음 참인 분기의 형상을 사용합니다. 참인 조건이 없으면 마지막 `else` 분기가 적용됩니다. 표준 도로 어셈블리는 `ConditionalAssemblyFactory.road_with_cut_fill()` 또는 `road_with_drainage()`로 생성합니다.

```python
from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.codes import LinkCode
from myalignment.assembly.conditional.factory import ConditionalAssemblyFactory
from myalignment.assembly.section_context import SectionContext
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.profile.profile import ProfileBuilder
from myalignment.surface.tin_surface import TinSurface
from myalignment.target.mapping import TargetMapping
from myalignment.target.reference import TargetReference

grade = ProfileBuilder("Grade").add_tangent(0, 40, 10, 10).build()
axis = AlignmentBuilder("Main").with_pi_coords([(0, 0), (40, 0)]).with_profile(grade).build()
ground = TinSurface.from_points([(0, -6, 12), (40, -6, 12), (40, 6, 8), (0, 6, 8)])
targets = TargetMapping((TargetReference("TargetDTM", object_name="Ground"),))

def context_at(station):
    return SectionContext.from_alignment(axis, station, profile=grade, surfaces={"Ground": ground})

assembly = ConditionalAssemblyFactory.road_with_cut_fill()
corridor = (
    CorridorBuilder("Road").add_baseline_from_alignment(axis, grade)
    .add_region_with_assembly("Road", 0, 40, assembly, targets=targets, context_provider=context_at)
    .build()
)
_, links = corridor.cross_section_at(10)
assert sum(link.code is LinkCode.DITCH for link in links) == 2
```

- 절토·성토는 **원지반 표고 − 설계 접점 표고**로 판정합니다. 차로 끝의 좌우 횡거에서 각각 TIN을 조회합니다. 표면 범위 밖에서는 지정한 고정 지표면 표고를 사용하며, 그 값도 없으면 해당 조건은 거짓입니다.
- 구배 조건의 단위는 소수 비율입니다. 표준 배수 어셈블리는 종단 구배의 절댓값이 0.02를 넘으면 배수로를 배치합니다. 사용자 조건은 `context_key`로 좁히고 `SectionContext.values`에 추가 값을 전달할 수 있습니다.
- 수평 타깃은 `target_offsets`에 실제 객체 이름과 부호 있는 횡거를 전달합니다. `TARGET_REACHED`는 같은 쪽에서 현재 접점이 목표 횡거에 도달했는지 확인합니다. `slope_to_surface()`는 표고차에 따라 미리 설정한 사면 또는 평탄 형상을 선택합니다.
- 링크 기반 3D 메시와 사각 스트립은 조건 변경으로 횡단 연결 구조가 달라지는 지점에서 구간을 나눕니다. 평면선형의 위치가 바뀌는 편집 후에는 기존 선형을 참조하는 컨텍스트 공급자를 새 선형에 맞춰 갱신합니다.

## 동적 파라미터 서브어셈블리

`ParametricLane`, `ParametricShoulder`, `ParametricSlope`는 일반 `AssemblyBuilder`와 조건부 분기에서 사용할 수 있습니다. `ParametricAssemblyBuilder`는 세 요소를 좌우에 한 번에 조립합니다. `with_params()`는 입력값과 계산 결과를 갱신한 새 객체를 반환합니다.

```python
from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.codes import LinkCode
from myalignment.assembly.parameter.display import show_parameters
from myalignment.assembly.parameterized.parametric_lane import ParametricLane
from myalignment.assembly.parameterized.parametric_slope import ParametricSlope
from myalignment.assembly.section_context import SectionContext
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.surface.tin_surface import TinSurface
from myalignment.target.mapping import TargetMapping
from myalignment.target.reference import TargetReference

axis = AlignmentBuilder("Road").with_pi_coords([(0, 0), (20, 0)]).build()
ground = TinSurface.from_points([(0, -12, -2), (20, -12, -2), (20, 12, -2), (0, 12, -2)])
targets = TargetMapping((TargetReference("NaturalGround", object_name="Ground"),))
lane = ParametricLane.create(width=3.5).with_params(width=4.0, slope=-0.025)
slope = ParametricSlope.create(slope_ratio=1.5).with_params(target_surface="NaturalGround")
assembly = AssemblyBuilder().add_right(lane).add_right(slope).build()

def context_at(station):
    return SectionContext.from_alignment(axis, station, surfaces={"Ground": ground})

corridor = (
    CorridorBuilder().add_baseline_from_alignment(axis)
    .add_region_with_assembly("Road", 0, 20, assembly, targets=targets, context_provider=context_at)
    .build()
)
_, links = corridor.cross_section_at(10)
catch = next(link.end for link in links if link.code is LinkCode.SLOPE)
assert catch.is_parametric and abs(catch.z - (-2.0)) < 1e-8
print(show_parameters(lane))
```

- `ParameterSet.evaluate_computed()`는 이름 참조, 괄호와 산술식을 지원합니다. 계산 순서는 의존성으로 정합니다. 잘못된 참조, 순환 의존성, 0으로 나누기는 오류를 반환합니다. 수식은 계산값과 읽기 전용 출력값을 만들 수 있습니다. 측점별 수식에는 `station`, `base_elevation`, `grade` 및 `SectionContext.values`를 사용할 수 있습니다.
- 차로·갓길의 경사는 소수 비율입니다. 차로의 `computed_slope_percent`는 퍼센트로, `computed_area`는 차로 길이 1m당 평면적으로 표시합니다. `apply_aor`는 차로 점의 캔트 적용 여부를 제어합니다.
- 사면의 `target_surface`는 `TargetMapping`의 논리 이름입니다. 사면은 현재 접점에서 시작해 해당 TIN의 횡단 교선과 만나는 가장 가까운 점을 사용합니다. 타깃이 없거나 사면이 교차하지 않으면 지정 높이를 적용한 기본 하향 사면을 사용합니다.

## 서브어셈블리 편구배와 캔트

도로는 `SuperelevationBinding`을 연결하고 `apply_aor=True`를 설정하면 해당 횡단 세그먼트의 측점별 경사를 사용합니다. `ParametricAssemblyBuilder.with_superelevation()`은 좌우 차로에 대응하는 세그먼트를 자동으로 연결합니다. 임계 측점 사이의 경사는 선형 보간하며, 곡선 밖에서는 기본 경사를 적용합니다.

```python
from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.parameterized.builder import ParametricAssemblyBuilder
from myalignment.cant.curve import CantCriticalStation, CantCurve, CantPivotMethod
from myalignment.corridor.corridor_builder import CorridorBuilder

axis = (
    AlignmentBuilder("Track").with_pi_coords([(0, 0), (40, 0)])
    .as_rail_alignment(gauge=1.435).build()
)
cant = CantCurve(
    start_station=0, end_station=40,
    critical_stations=(CantCriticalStation(0, 0), CantCriticalStation(40, 0.15)),
)
track = (
    ParametricAssemblyBuilder("Rail")
    .with_cant((cant,), CantPivotMethod.LEFT_RAIL, gauge=1.435)
    .build()
)
corridor = (
    CorridorBuilder("Rail").add_baseline_from_alignment(axis)
    .add_region("Track", 0, 40, track).build()
)
_, (rails,) = corridor.cross_section_at(20)
assert abs(rails.start.z) < 1e-8
assert abs(rails.end.z - 0.075) < 1e-8
```

- `CantCurve.cant_value`와 레일 표고 변위는 m입니다. `CantBinding.cant_at()`과 `default_cant`의 단위는 mm입니다. `rail_offsets_at()`은 중심선·좌측 레일·우측 레일 피벗에 맞춰 좌우 변위를 m로 반환합니다.
- `ParametricAssemblyBuilder.with_cant()`는 중심 레일 서브어셈블리를 생성합니다. 개별 차로나 레일은 `with_station()`으로 평가한 파라미터와 형상을 미리 확인할 수 있습니다.
- 코리더는 실제 기하 측점에서 바인딩을 평가합니다. 레일에 자체 바인딩이 있으면 그 레일의 표고에 영역 캔트를 다시 더하지 않습니다. 선형을 반전하면 좌우 레일 코드가 바뀌며 대응 위치의 물리적 표고는 유지됩니다.

## 사용자 정의 서브어셈블리

`CustomSubassemblyBuilder`로 입력값과 계산값, 점 좌표와 링크를 선언할 수 있습니다. 점과 링크의 인덱스는 추가 순서대로 0부터 시작합니다. 작성한 부품은 `AssemblyBuilder`로 좌우에 배치하거나 조건부 서브어셈블리의 분기로 사용할 수 있습니다.

```python
from myalignment.assembly import AssemblyBuilder
from myalignment.assembly.codes import LinkCode, PointCode
from myalignment.assembly.custom import CustomSubassemblyBuilder, CustomSubassemblyLibrary

path = (
    CustomSubassemblyBuilder("Service Path")
    .with_parameter("width", 2.0, unit="m", min_value=0.5)
    .with_parameter("slope", -0.02, unit="m/m")
    .with_computed("drop", "width * slope", unit="m")
    .with_output("crossfall_percent", "slope * 100", unit="%")
    .add_point(PointCode.SIDEWALK_IN)
    .add_point(PointCode.SIDEWALK_OUT, x="width", z="drop")
    .add_link(0, 1, LinkCode.PAVEMENT)
    .build()
)
library = CustomSubassemblyLibrary.standard().register(path)
wider = library.get("Service Path").with_params(width=3)
section = AssemblyBuilder().add_right(wider).build()
_, links = section.generate_cross_section()
assert links[0].end.x == 3.0
assert links[0].end.z == -0.06
assert wider.param_set.outputs()["crossfall_percent"] == -2.0
```

- 좌표 수식은 입력·계산·출력 파라미터와 산술 연산 `+`, `-`, `*`, `/`, `//`, `%`, `**`를 지원합니다. 동적 좌표에는 `station`, `grade`, `base_elevation`, `SectionContext.values`를 참조할 수 있습니다. `grade`처럼 컨텍스트가 필요한 수식은 `build(context=...)`에 초기 검증용 값을 전달합니다. 코리더는 횡단면을 생성할 때 해당 측점의 컨텍스트에서 수식을 다시 계산합니다.
- `add_shape()`는 하나의 닫힌 경계를 이루는 링크에 형상 코드를 지정합니다. `QuantityTakeoff`는 그 코드로 재료 물량을 집계합니다. `custom_lane()`은 닫힌 포장층을 정의하는 예제입니다.
- `presets`에는 차로, 갓길·연석, V형 배수로, 사면, 도시도로 단면이 있습니다. `custom_slope()`는 `TargetDTM`으로 연결된 지표면과의 교점을 사용합니다. 타깃을 연결하지 않았거나 교점을 찾지 못하면 지정한 높이와 사면비로 배치합니다.
