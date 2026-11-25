# 평면선형

`AlignmentBuilder`는 PI 좌표, 곡선 반경, 진입·진출 완화곡선장으로 선형을 만듭니다. 각 제원 리스트를 PI 좌표 순서에 맞추고 첫 점과 끝 점의 반경은 `None`으로 둡니다. 가용 접선장을 넘어서는 반경이나 완화곡선은 오류로 처리합니다.

빌더의 설정 메서드는 같은 인스턴스를 수정하고 반환합니다. 설정이 독립적인 여러 선형을 만들 때는 선형마다 새 빌더를 생성하세요. 같은 빌더에서 PI 개수를 바꾸면 생략한 제원의 기본값은 새 개수에 맞춰 적용됩니다. 직접 지정한 반경과 완화곡선장 목록도 새 PI 개수에 맞게 갱신하세요.

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
