# 평면선형

`AlignmentBuilder`는 PI 좌표, 곡선 반경, 진입·진출 완화곡선장으로 선형을 만듭니다. 각 제원 리스트를 PI 좌표 순서에 맞추고 첫 점과 끝 점의 반경은 `None`으로 둡니다. 가용 접선장을 넘어서는 반경이나 완화곡선은 오류로 처리합니다.

빌더의 설정 메서드는 같은 인스턴스를 수정하고 반환합니다. 설정이 독립적인 여러 선형을 만들 때는 선형마다 새 빌더를 생성하세요. 같은 빌더에서 PI 개수를 바꾸면 생략한 제원의 기본값은 새 개수에 맞춰 적용됩니다. 직접 지정한 반경과 완화곡선장 목록도 새 PI 개수에 맞게 갱신하세요.

## PI 좌표에서 바로 생성

`Alignment.from_pi_coords()`에 좌표 목록이나 제너레이터를 전달하면 선형을 바로 만들 수 있습니다. 반경을 생략하면 인접 PI를 직선으로 연결합니다. 기존 종단은 `profiles=`로 한꺼번에 연결할 수 있습니다.

```python
from myalignment.alignment import Alignment

axis = Alignment.from_pi_coords(
    [(0, 0), (150, 0), (150, 150)], name="Main",
    radii=[None, 40, None], entry_lengths=[0, 12, 0], start_station=1000,
)
assert axis.start_station == 1000
assert len(axis.entities) == 5
```

`entry_lengths`만 전달하면 진입과 진출에 같은 완화곡선장을 사용합니다. 비대칭 완화곡선에는 `exit_lengths`도 전달합니다.

## 좌표 조회와 편집

```python
import math

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.enum.spiraltype import SpiralType
from myalignment.structure.factory import StructureFactory

bridge = StructureFactory.create_structure("교량", "Bridge A", 1030, 1050)
axis = (
    AlignmentBuilder("Main")
    .with_pi_coords([(0, 0), (150, 0), (150, 150)])
    .with_radii([None, 40, None])
    .with_spiral_lengths(entry=[0, 12, 0], exit=[0, 16, 0], spiral_type=SpiralType.Clothoid)
    .with_start_station(1000)
    .with_structure(bridge)
    .build()
)

point = axis.point_at(1040, offset=3)
projected = axis.project(point)
assert math.isclose(projected.station, 1040)
assert math.isclose(projected.offset, 3)
assert axis.structure_at(1040).name == "Bridge A"

with axis.modify() as edit:
    edit.rename("Main Revised").update_pi_and_radius(1, radius=42)
revised = edit.result
assert revised.name == "Main Revised"
assert axis.name == "Main"
```

`project()`는 거리와 접선 방향을 포함한 `ProjectionResult`를 반환합니다. 측점과 횡거만 필요하면 `station_offset_of()`를 사용합니다. 곡선의 실제 시작·종료 측점 또는 방위각은 `entities`, `entity_at_station()`, `tangent_at()`에서 조회합니다.

트랜잭션은 정상적으로 종료되면 `result`를 제공합니다. 선형 수정 시 연결 객체의 측점이 갱신됩니다. 같은 트랜잭션에서 새로 공급하는 종단과 구조물은 편집 후 측점 기준으로 입력합니다.

## 교차 및 측점 방정식

```python
from myalignment.alignment.alignment_builder import AlignmentBuilder

axis = (
    AlignmentBuilder("Main").with_pi_coords([(0, 0), (100, 0)])
    .with_start_station(1000).build()
    .add_station_equation(1050, 2000)
)
crossing = AlignmentBuilder("Crossing").with_pi_coords([(73, -10), (73, 10)]).build()
hit, = axis.intersection_with(crossing)
assert hit.station == 1073
assert axis.raw_to_display_station(hit.station) == 2023
assert axis.display_to_raw_stations(2023) == (1073.0,)
```

`intersection_with()`는 호출한 선형의 원시 측점으로 교차점을 반환합니다. 요소의 겹침 구간은 양 끝점을 반환합니다. 한 표시 측점에 여러 원시 측점이 대응할 수 있으므로 다중 후보에는 `display_to_raw_stations()`를 사용합니다. `display_to_raw_station()`은 일치하는 원시 측점이 하나일 때만 값을 반환합니다.

`offset_alignment()`는 오른쪽 양수 규약으로 평행 선형을 만들고 새 길이에 따라 측점을 갱신합니다. `reversed_alignment()`는 진행 방향을 바꿉니다. 재생성이 필요한 저장 코리더 표면이나 크로스오버 기하는 새 모델에 맞춰 다시 계산합니다.

## 선형 제원표

`AlignmentTableRenderer`는 직선, 원곡선, 완화곡선의 제원을 각각 또는 하나의 통합 표로 그립니다. 측점은 원시 측점으로 표시합니다. 방위각은 +X축에서 반시계 방향으로 잰 도 단위 값이며, Delta는 요소 내부의 방향 변화량을 도 단위로 표시합니다.

```python
from cadgeom import Point2d

from myalignment.alignment import AlignmentBuilder, AlignmentTableStyle
from myalignment.export.dxf_writer import DxfWriter
from myalignment.render.alignment_renderer import AlignmentRenderer
from myalignment.render.alignment_table_renderer import AlignmentTableRenderer

axis = (
    AlignmentBuilder("Main")
    .with_pi_coords([(0, 0), (150, 0), (150, 180)])
    .with_radii([None, 40, None])
    .with_spiral_lengths([0, 12, 0], [0, 16, 0])
    .with_start_station(1000)
    .build()
)
style = AlignmentTableStyle.segment_style()
assert len(AlignmentTableRenderer.collect_rows(axis, style)) == 5
scene = AlignmentTableRenderer.render(
    AlignmentRenderer.render_plan(axis), axis, style, Point2d(0, -30),
)
DxfWriter(scene).write("alignment-table.dxf")
```

`line_style()`, `curve_style()`, `spiral_style()`로 요소 유형을 선택할 수 있습니다. `TableColumnSpec`으로 제목, 폭, 숫자 형식을 지정합니다. 폭을 0으로 두면 내용에 맞게 계산합니다. `sort_by`는 표에 표시하지 않는 열에도 적용할 수 있습니다. `split_table=True`를 쓰면 `max_rows_per_table`씩 나눠 제목과 머리글이 있는 표를 오른쪽에 배치합니다.

적용할 수 없는 제원은 빈 셀로 둡니다. 완화곡선의 반경에는 원곡선 쪽 끝의 반경을 표시하고, A 값은 클로소이드 모델의 설계 파라미터에서 계산합니다.

## 원곡선·완화곡선 레이블

기본 레이블 세트는 원곡선과 완화곡선의 중앙에 제원을 표시합니다. `CurveLabelStyle.detailed()`는 외선장, 중앙종거, 현장과 양 끝 측점을 추가합니다. `SpiralLabelStyle.stations()`는 인접 요소에 따라 TS·SC·CS·ST 측점을 표시합니다. 개별 BC·EC 좌표 레이블은 `AlignmentLabelStyle.curve_point_style()`로 추가합니다.

```python
from myalignment.alignment import AlignmentBuilder, CurveLabelStyle, SpiralLabelStyle
from myalignment.alignment.label_set import AlignmentLabelSet
from myalignment.alignment.label_style import AlignmentLabelStyle
from myalignment.alignment.label_type import AlignmentLabelType
from myalignment.export.dxf_writer import DxfWriter
from myalignment.render.alignment_renderer import AlignmentRenderer

axis = (
    AlignmentBuilder("Main").with_pi_coords([(0, 0), (150, 0), (150, 180)])
    .with_radii([None, 40, None]).with_spiral_lengths([0, 12, 0], [0, 16, 0]).build()
)
labels = (
    AlignmentLabelSet.standard()
    .with_style(AlignmentLabelType.CURVE, CurveLabelStyle.detailed())
    .with_style(AlignmentLabelType.SPIRAL, SpiralLabelStyle.stations())
    .with_style(AlignmentLabelType.CURVE_POINT, AlignmentLabelStyle.curve_point_style())
)
scene = AlignmentRenderer.render_plan(axis.with_label_set(labels), render_labels=True)
assert any(primitive.style.layer == "C-ALIGN-CURVE-LABEL" for primitive in scene.primitives)
DxfWriter(scene).write("curve-spiral-labels.dxf")
```

`angle_format`은 `dms` 또는 `decimal`을 사용합니다. 레이블의 측점에는 측점 방정식이 적용됩니다. `CurveSpiralExtractor`는 원시 측점과 라디안 각도, 완화곡선 시작 접선 좌표계의 끝점 `x`, `y`를 반환합니다. A 값은 클로소이드에 해당하며, 적용할 수 없는 제원이나 전이 측점은 대시로 표시됩니다.

`render_curves=False`와 `render_spirals=False`로 해당 유형의 중앙 제원 레이블을 숨길 수 있습니다. 겹침 방지는 `stagger_config=`로 설정합니다. 기존 장면에 한 유형만 추가하려면 `CurveLabelRenderer.render()` 또는 `SpiralLabelRenderer.render()`를 사용합니다.

## 측점·횡거 레이블

`StationOffsetLabel`은 고정 XY 또는 원시 측점과 횡거에 배치합니다. 고정점은 선형을 수정해도 XY를 유지하며 새 선형에 투영해 값을 다시 계산합니다. 상대점은 지정한 원시 측점과 횡거를 유지하며 선형과 함께 움직입니다. 횡거는 진행 방향 기준 왼쪽이 음수, 오른쪽이 양수입니다.

```python
from cadgeom import Point2d
from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.alignment.station_offset_label import StationOffsetLabel
from myalignment.alignment.station_offset_label_style import StationOffsetLabelStyle
from myalignment.export.dxf_writer import DxfWriter
from myalignment.render.alignment_renderer import AlignmentRenderer

axis = (
    AlignmentBuilder("Main").with_pi_coords([(0, 0), (100, 0)]).build()
    .add_station_equation(20, 200)
)
relative = StationOffsetLabel(relative_station=30, relative_offset=5)
fixed = StationOffsetLabel(
    label_style=StationOffsetLabelStyle.offset_only(),
    fixed_point=Point2d(45, 6),
)
axis = axis.with_station_offset_labels([relative, fixed])
assert relative.evaluate(axis)["Station Value"] == "210.00"
scene = AlignmentRenderer.render_plan(axis, render_labels=True)
DxfWriter(scene).write("station-offset-labels.dxf")
```

- 템플릿의 `<[Station Value]>`는 측점 방정식을 적용한 표시 측점이고 `<[Raw Station]>`은 원시 측점입니다. `Easting`과 `Northing`은 표식기 좌표입니다. 선형 위 투영점 좌표는 `Alignment Easting`과 `Alignment Northing`을 사용합니다.
- 다른 선형을 참조하려면 `reference_alignment_name`을 설정하고 `render_plan(reference_alignments=...)`에 이름별 선형을 전달합니다. `Ref Station`, `Ref Raw Station`, `Ref Offset`, `Ref Alignment Name` 필드를 사용할 수 있습니다. 측량점은 `reference_point_name`과 `reference_points`로 전달합니다. 템플릿에서 참조를 찾을 수 없으면 `???`로 표시합니다.
- 공통 스타일은 `AlignmentLabelSet.with_station_offset_style()`로 지정합니다. 개별 레이블의 `label_style`이 공통 스타일보다 우선합니다. `render_plan(station_offset_labels=...)`로 출력할 레이블을 임시 지정할 수 있습니다. 현재 선형 범위 밖의 상대 레이블은 일괄 출력에서 생략합니다.

## 평면도의 종단 기하점 레이블

`AlignmentLabelSet.with_profile_geometry()`는 표준 평면도 레이블에 PVI와 종단곡선 시작점(VPC)·끝점(VPT)을 추가합니다. `with_profile_geometry_style()`로 고점·저점, 구배 변경점, 종단 시작·끝까지 선택할 수 있습니다. 같은 측점의 기하점은 표식기를 공유하며 텍스트는 선형의 횡방향으로 쌓입니다.

```python
from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.alignment.label_set import AlignmentLabelSet
from myalignment.alignment.profile_geometry_label_style import ProfileGeometryLabelStyle
from myalignment.alignment.profile_geometry_label_type import ProfileGeometryPointLabelType
from myalignment.export.dxf_writer import DxfWriter
from myalignment.profile.profile import ProfileBuilder
from myalignment.render.alignment_renderer import AlignmentRenderer

profile = (
    ProfileBuilder("Design")
    .add_tangent(100, 140, 10, 12)
    .add_tangent(140, 200, 12, 10)
    .build()
)
labels = AlignmentLabelSet().with_profile_geometry_style(
    ProfileGeometryLabelStyle.with_grade_info(),
    labeled_points=(ProfileGeometryPointLabelType.GRADE_BREAK,),
)
axis = (
    AlignmentBuilder("Main").with_pi_coords([(0, 0), (100, 0)])
    .with_start_station(100).build().add_station_equation(130, 300)
    .with_label_set(labels)
)
scene = AlignmentRenderer.render_plan(axis, render_labels=True, fg_profile=profile)
assert any("STA 310.00" in (primitive.text or "") for primitive in scene.primitives)
DxfWriter(scene).write("profile-geometry-labels.dxf")
```

`fg_profile=`로 레이블을 추출할 종단을 지정합니다. 생략하면 선형에 연결된 계획 종단을 사용합니다. 원시 측점으로 좌표를 계산하고 `<[Station Value]>`에는 측점 방정식을 적용합니다. 포물선 PVI의 표고는 접선 교점에서 가져오며, 고점·저점의 표고는 곡선에서 계산합니다. `show_leader=True`는 표식기에서 텍스트로 지시선을 추가합니다.
