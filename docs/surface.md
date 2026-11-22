# 지표면과 정지

`TinSurface.from_points()`는 월드 좌표 `(x, y, z)`를 삼각망으로 만듭니다. 일정한 간격의 지형은 `TinSurfaceBuilder.add_grid()`로 생성할 수 있습니다. 평면 면적과 3D 표면적은 각각 `area_2d`와 `area_3d`로 조회합니다.

## 경계와 브레이크라인

| 경계 유형 | 적용 방식 |
| --- | --- |
| `OUTER` | 유효 외곽의 안쪽만 남깁니다. |
| `SHOW` | 표시 영역들의 합집합 안쪽만 남깁니다. |
| `HIDE` | 내부 구멍을 제거합니다. |
| `DATA_CLIP` | 삼각분할 전 경계 밖 입력점을 제외하고 경계를 넘는 브레이크라인을 자릅니다. |

경계를 가로지르는 TIN 면은 실제 경계에서 자르고 절단점 표고를 보간합니다. `with_boundary()`와 `without_boundary()`는 편집된 새 표면을 반환합니다.

`STANDARD` 브레이크라인은 TIN의 변과 표고를 제약합니다. `PROXIMITY`는 입력 표고 대신 기존 표면에서 표고를 얻고, `NON_DESTRUCTIVE`는 기존 삼각망에 손대지 않습니다. `WALL`에는 방향 기준 좌측 표고와 별도로 `right_elevations`를 지정할 수 있습니다. 표면 내부에서 끝나는 벽은 끝점의 양측 표고가 같아야 합니다.

## 형상선을 TIN에 반영하기

```python
from math import isclose

from myalignment.featureline.builder import FeatureLineBuilder
from myalignment.surface.boundary import Boundary
from myalignment.surface.tin_surface_builder import TinSurfaceBuilder

ridge = FeatureLineBuilder("Ridge").add_coords([(0, 5, 102), (10, 5, 102)]).build()
surface = (
    TinSurfaceBuilder("Terrain")
    .add_points([(0, 0, 100), (10, 0, 100), (10, 10, 100), (0, 10, 100)])
    .add_feature_line_as_breakline(ridge)
    .add_outer_boundary(Boundary.rectangle(0, 0, 10, 10, "Site"))
    .build()
)
assert isclose(ridge.length_2d, 10)
assert isclose(surface.area_2d, 100)
assert isclose(surface.elevation_at(5, 5), 102)
```

기존 표면에 형상선을 추가할 때는 `surface.with_breakline(ridge.to_breakline())`를 사용합니다. 삼각망 안쪽만 대상으로 계산하려면 먼저 `triangle_at(x, y)`를 확인합니다. 면이 없는 곳에서 `elevation_at()`은 가장 가까운 정점 표고를 반환할 수 있습니다.

## 사면과 부지 정지

`Footprint`는 사면의 시작 경계를 정의합니다. 형상선을 재사용하려면 `Footprint.from_feature_line()`을 사용합니다. `SlopeToSurface`, `SlopeToDistance`, `SlopeToElevation`으로 원지형·수평거리·목표표고에 대한 사면 투영 조건을 지정합니다.

```python
from math import isclose

from myalignment.grading.criteria import ProjectionType, Slope, SlopeFormat
from myalignment.grading.criteria_surface import SlopeToSurface
from myalignment.grading.footprint import Footprint, FootprintVertex
from myalignment.grading.grading import Grading
from myalignment.grading.site import GradingGroupBuilder, SiteBuilder
from myalignment.grading.target_context import TargetContext
from myalignment.surface.tin_surface import TinSurface

ground = TinSurface.from_points([(-25, -25, 95), (50, -25, 95), (-25, 50, 95), (50, 50, 95)])
footprint = Footprint(
    name="Pad", is_closed=True,
    vertices=tuple(FootprintVertex(x, y, 100) for x, y in [(0, 0), (20, 0), (20, 20), (0, 20)]),
)
criteria = SlopeToSurface(slope=Slope(2, SlopeFormat.RATIO), projection=ProjectionType.OUTSIDE)
grading = Grading(
    name="Pad slope", footprint=footprint, criteria=criteria,
    target_context=TargetContext(surface=ground),
)
group = GradingGroupBuilder("Pad group").add_grading(grading).build()
site = SiteBuilder("Site").add_grading_group(group).build()
assert site.total_daylight_length > 0
assert all(isclose(hit.distance, 10, abs_tol=0.1) for hit in group.daylight_lines)
```
