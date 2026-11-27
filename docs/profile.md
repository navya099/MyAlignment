# 종단과 종단 뷰

`ProfileBuilder`로 설계 종단(`ProfileType.FG`)과 현황 종단(`ProfileType.EG`)을 구성합니다. 입력 측점은 선형의 원시 측점과 맞춥니다. 인접 종단 요소의 경계 측점과 표고는 연속이어야 합니다. 접선 연결부의 구배까지 연속이어야 하는 모델은 `build(validate_grades=True)`로 검증할 수 있습니다.

## 측점·표고 데이터 일괄 입력

`Profile.from_points()`는 `(원시 측점, 표고)` 행을 받아 인접 점을 직선으로 연결합니다. 목록, 제너레이터, `zip(stations, elevations)`을 전달할 수 있습니다. CSV는 `Profile.from_csv()`로 직접 읽습니다.

```python
from pathlib import Path

from myalignment.alignment import Alignment
from myalignment.profile import Profile

path = Path("ground.csv")
path.write_text("station,elevation\n1000,95\n1050,97\n1100,96\n", encoding="utf-8")
ground = Profile.from_csv(path, name="Ground")
axis = Alignment.from_pi_coords([(0, 0), (100, 0)], start_station=1000, profiles=[ground])
assert axis.eg_profile.elevation_at(1025) == 96
```

기본 CSV 헤더는 `station`, `elevation`입니다. 다른 헤더나 구분자는 `station_column`, `elevation_column`, `delimiter`로 지정합니다. 측점과 표고만 읽으면 기본값으로 현황 종단(EG)을 만듭니다. 원시 측점은 두 개 이상이어야 하며 중복 없이 오름차순으로 입력합니다. 기존 빌더에 접선 구간을 일괄 추가하려면 `ProfileBuilder.add_points()`를 사용합니다.

## 계획 종단의 PVI 일괄 입력

`Profile.from_pvis()`는 PVI 사이의 구배를 계산하고, 각 곡선의 시작점(VPC)과 끝점(VPT)에 맞춰 접선을 연결합니다. 세 번째 값으로 대칭 포물선의 전체 길이 또는 비대칭 포물선의 `(진입 길이, 진출 길이)`를 전달합니다. 곡선이 없는 점에서는 세 번째 값을 생략하거나 `None`을 사용합니다.

```python
from myalignment.profile import Profile

design = Profile.from_pvis([
    (0, 100),
    (100, 104, 60),
    (200, 99, (20, 30)),
    (300, 102),
], name="Design")
assert abs(design.elevation_at(100) - 103.325) < 1e-9
```

곡선 제원을 넣은 행의 표고는 두 접선이 만나는 PVI 표고입니다. 따라서 같은 측점에서 계산한 실제 종곡선 표고와 다를 수 있습니다. 첫 점과 끝 점에는 곡선을 지정할 수 없으며, 인접 종곡선은 서로 접할 수 있습니다. 곡선이 인접 PVI를 넘거나 서로 겹치면 입력 오류가 발생합니다.

CSV에서 계획 종단을 읽을 때는 `Profile.from_csv("design.csv", curve_length_column="L")`을 사용합니다. 비대칭 곡선 열은 `length_in_column`과 `length_out_column`을 함께 지정합니다. 두 형식을 섞을 때는 행마다 전체 길이 또는 진입·진출 길이 한 쌍을 입력하며, 곡선이 없는 행은 길이 열을 비워 둡니다. 전체 길이 열의 `0`도 곡선이 없는 점으로 처리합니다. 기존 빌더에는 `ProfileBuilder.add_pvis()`로 추가할 수 있습니다.

## 접선과 수직곡선

다음 예제는 접선–대칭 포물선–접선으로 구성됩니다. STA 150의 PVI 표고는 102m이며, 포물선의 같은 측점에서 표고는 101.7m입니다.

```python
from math import isclose

from myalignment.profile.profile import ProfileBuilder
from myalignment.profile.profiletype import ProfileType

design = (
    ProfileBuilder("FG", ProfileType.FG)
    .add_tangent(0, 120, 99, 101.4)
    .add_symmetric_parabola(
        pvi_station=150, pvi_elevation=102, grade_in=0.02,
        grade_out=-0.02, curve_length=60,
    )
    .add_tangent(180, 300, 101.4, 99)
    .build(validate_grades=True)
)
assert isclose(design.elevation_at(150), 101.7)
assert isclose(design.grade_at(150), 0, abs_tol=1e-9)
```

`add_asymmetric_parabola()`에는 `curve_length` 대신 `length_in`과 `length_out`을 전달합니다. 종단 범위 밖의 `elevation_at()`과 `grade_at()`은 오류를 반환합니다. 완성한 모델은 `AlignmentBuilder.with_profile()`로 선형에 붙입니다.

## 밴드와 레이블

```python
from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.export.dxf_writer import DxfWriter
from myalignment.profile.grade_break_style import GradeBreakLabelStyle
from myalignment.profile.profile import ProfileBuilder
from myalignment.profile.profiletype import ProfileType
from myalignment.profile.station_label import StationElevationLabel
from myalignment.profile.view_band import BandType, ProfileViewBand
from myalignment.profile.view_style import ProfileViewStyle
from myalignment.render.profile_view_renderer import ProfileViewRenderer
from myalignment.render.stagger_presets import StaggerConfigPresets

fg = (
    ProfileBuilder("FG", ProfileType.FG)
    .add_tangent(0, 50, 100, 102).add_tangent(50, 100, 102, 101).build()
)
eg = ProfileBuilder("EG", ProfileType.EG).add_tangent(0, 100, 99, 100).build()
axis = AlignmentBuilder("Main").with_pi_coords([(0, 0), (100, 0)]).build()
label = StationElevationLabel(50).with_profile1("FG").with_profile2("EG")
scene = ProfileViewRenderer.render(
    [fg, eg],
    axis.name,
    ProfileViewStyle(vertical_exaggeration=3),
    [
        ProfileViewBand(BandType.PROFILE_DATA),
        ProfileViewBand(BandType.HORIZONTAL_GEOMETRY),
        ProfileViewBand(BandType.VERTICAL_GEOMETRY),
    ],
    alignment=axis,
    labels=[label],
    grade_break_style=GradeBreakLabelStyle.standard(),
    stagger_config=StaggerConfigPresets.up_increment(),
)
DxfWriter(scene).write("profile.dxf")
```

`ProfileViewBand`는 종단 데이터, 수평·수직 지오메트리, 캔트 밴드를 지원합니다. 수평 지오메트리와 캔트 밴드에는 `alignment=`를 전달합니다. `StationElevationLabel`의 `LabelStyle`은 지정 측점의 두 종단 표고에 사용합니다. `ProfileLabelStyle`과 `ProfileLabelSet`은 종단 요소의 구배 변경점, PVI, 종곡선 레이블을 설정합니다. 구배 변경점을 별도로 강조할 때는 위 예제의 `GradeBreakLabelStyle`을 사용합니다.

## 두 측점의 표고차 레이블

`DepthLabel`은 같은 종단의 두 원시 측점에서 표고를 조회합니다. 수평거리는 끝 측점에서 시작 측점을 뺀 값이고, 평균 구배는 표고차를 수평거리로 나눈 값입니다. `summary()`의 구배는 소수 비율이고 `evaluate()`의 구배는 부호를 포함한 백분율 문자열입니다. 수직 과장은 도면의 Y 좌표와 텍스트 높이에만 적용됩니다.

```python
from math import isclose

from myalignment.export.dxf_writer import DxfWriter
from myalignment.profile import DepthLabel, DepthLabelStyle, ProfileBuilder
from myalignment.profile.view_style import ProfileViewStyle
from myalignment.render.profile_view_renderer import ProfileViewRenderer

profile = ProfileBuilder("FG").add_tangent(1000, 1100, 100, 105).build()
depth = DepthLabel(1020, 1060, profile_name="FG")
assert isclose(depth.summary([profile])["grade"], 0.05)
assert depth.evaluate([profile])["Elevation Difference"] == "+2.000"

scene = ProfileViewRenderer.render(
    [profile],
    "Main",
    ProfileViewStyle(vertical_exaggeration=3),
    depth_labels=[depth.with_style(DepthLabelStyle.standard())],
)
DxfWriter(scene).write("profile-depth.dxf")
```

종단 이름을 생략하면 입력 목록의 첫 종단을 사용합니다. 이름이 일치하는 종단이 없거나 두 점 중 하나가 종단 범위 밖에 있으면 결과는 빈 딕셔너리이고 레이블은 그리지 않습니다. 끝 측점은 시작 측점보다 커야 합니다.

`DepthLabelStyle.standard()`는 측점·표고차·구배·거리를 표시합니다. `minimal()`은 표고차, `slope_only()`는 구배를 표시하며, `show_arrow=False`로 연결선과 끝점 마커를 숨길 수 있습니다. 사용자 정의 `ProfileLabelComponent`의 텍스트에는 `<[Start Station]>`, `<[End Station]>`, `<[Start Elevation]>`, `<[End Elevation]>`, `<[Elevation Difference]>`, `<[Grade]>`, `<[Distance]>` 필드를 사용할 수 있습니다.

기존 Scene에 레이블만 추가하려면 `myalignment.render.depth_label_renderer.DepthLabelRenderer`의 `render()` 또는 `render_multiple()`을 사용합니다. 생성된 API 레퍼런스에서 두 클래스와 렌더러의 시그니처를 찾을 수 있습니다.

## 종단 뷰 분할

`ProfileViewSplitComposer.compose()`는 측점 범위를 여러 패널로 나눠 하나의 DXF 장면으로 구성합니다. 여러 종단을 전달하면 전체 측점 범위를 포함하며, PVI 분할과 자동 경계 정렬에는 입력 순서의 첫 유효 종단을 사용합니다.

```python
from myalignment.export.dxf_writer import DxfWriter
from myalignment.profile import ProfileBuilder, ProfileViewSplitConfig, ProfileViewSplitMethod
from myalignment.profile.view_band import BandType, ProfileViewBand
from myalignment.profile.view_style import ProfileViewStyle
from myalignment.render.profile_view_split_composer import ProfileViewSplitComposer

profile = ProfileBuilder("FG").add_tangent(1000, 1600, 100, 112).build()
config = ProfileViewSplitConfig(
    method=ProfileViewSplitMethod.STATION_RANGE,
    max_station_per_view=240,
    overlap_station=10,
    columns=2,
)
scene = ProfileViewSplitComposer.compose(
    [profile], "Main", ProfileViewStyle(vertical_exaggeration=3), config,
    bands=[ProfileViewBand(BandType.PROFILE_DATA)],
)
assert scene.metadata["view_count"] == 3
DxfWriter(scene).write("profile-split.dxf")
```

- `STATION_RANGE`는 겹침을 더하기 전의 최대 측점 길이를 기준으로 자동 분할합니다. 범위 제약이 허용하면 경계를 PVI에 맞춥니다.
- `PVI_COUNT`는 실제 내부 PVI 개수를 사용합니다. 경계에 놓인 PVI는 분할을 계산할 때 앞 구간에 한 번만 셉니다.
- `MANUAL`은 오름차순 원시 측점 목록을 사용합니다. 전체 범위 밖의 측점은 건너뜁니다. `NONE`은 한 패널로 표시합니다.

`overlap_station`은 내부 경계의 양쪽 패널을 각각 지정 거리만큼 확장합니다. 측점 레이블은 해당 측점이 있는 패널에 나타나며, Depth 레이블은 두 끝점이 모두 패널에 포함될 때 표시됩니다. `include_start_label=False`는 패널 제목 아래의 측점 범위 표기를 숨깁니다. 패널별 표시 범위와 도면 이동량은 `scene.metadata["panels"]`에서 조회할 수 있습니다.

## 종단 뷰 객체 투영

`ProjectionBuilder`와 `ProjectionComposer`는 평면 객체를 종단 뷰의 원시 측점·표고로 변환합니다. `ProfileViewRenderer.render(..., projections=...)`와 `ProfileViewSplitComposer.compose(..., projections=...)`에 같은 투영 결과를 전달할 수 있습니다.

```python
from myalignment.alignment import AlignmentBuilder
from myalignment.export.dxf_writer import DxfWriter
from myalignment.featureline.feature_line import FeatureLine
from myalignment.featureline.vertex import FeatureLineVertex
from myalignment.profile import ProfileBuilder, ProjectionBuilder, ProjectionComposer
from myalignment.profile.view_style import ProfileViewStyle
from myalignment.render.primitives_3d import Point3D
from myalignment.render.profile_view_renderer import ProfileViewRenderer

axis = (
    AlignmentBuilder("Main").with_pi_coords([(0, 0), (100, 0)])
    .with_start_station(1000).with_bridge("교량 A", 1020, 1060).build()
)
profile = ProfileBuilder("FG").add_tangent(1000, 1100, 10, 30).build()
crossing = AlignmentBuilder("Cross").with_pi_coords([(70, -20), (70, 20)]).build()
feature = FeatureLine("Ridge", (FeatureLineVertex(10, 5, 30), FeatureLineVertex(60, 8, 45)))
projections = ProjectionComposer.project_all(axis, profile, [crossing], [feature])
projections.append(ProjectionBuilder.project_point(axis, profile, Point3D(90, 8, 29), name="Survey"))
assert projections[-1].start_station == 1090
scene = ProfileViewRenderer.render(
    [profile], axis.name, ProfileViewStyle(vertical_exaggeration=3), projections=projections,
)
DxfWriter(scene).write("profile-projections.dxf")
```

교량·터널은 표시 가능한 구조물 구간의 중앙에서 참조 종단 표고를 읽습니다. 교차 선형은 참조 종단 범위 안에서 발견된 교차점마다 표시합니다. 형상선과 관로 경로는 입력 정점 순서와 Z 좌표를 유지합니다. 점과 블록 삽입점은 명시한 표고, 점의 Z, 참조 종단 표고 순으로 사용합니다. 평면 투영에는 선형의 최근접점을 사용하므로 선형 끝의 바깥쪽에 있는 점은 끝 측점에 투영될 수 있습니다.

관로는 `project_pipe()`에 3D 중심선 좌표를 전달합니다. 블록은 `ProjectionObjectType.BLOCK` 스타일을 지정한 삽입점으로 표현합니다. 분할 뷰에서는 경계에서 경로 표고를 보간하며, 패널을 벗어났다가 다시 들어오는 경로는 별도 조각으로 그립니다.

## 종단 절토·성토 해치

`ProfileViewRenderer.render(hatch_style=...)`는 설계 종단이 원지반 아래에 있는 구간을 절토로, 위에 있는 구간을 성토로 그립니다. 이름이 `FG`, `EG`인 종단을 먼저 찾고 종단 유형을 확인합니다. 다른 이름을 명시하려면 `fg_profile_name`과 `eg_profile_name`을 전달합니다. 분할 종단 뷰에도 같은 옵션을 사용할 수 있습니다.

```python
from myalignment.export.dxf_writer import DxfWriter
from myalignment.export.svg_writer import SvgWriter
from myalignment.profile.hatch_generator import ProfileHatchGenerator
from myalignment.profile.hatch_pattern import HatchPattern
from myalignment.profile.hatch_style import ProfileHatchStyle
from myalignment.profile.profile import ProfileBuilder
from myalignment.profile.view_style import ProfileViewStyle
from myalignment.render.profile_view_renderer import ProfileViewRenderer

fg = ProfileBuilder("FG").add_tangent(0, 100, 10, 16).build()
eg = ProfileBuilder("EG").add_tangent(0, 100, 13, 13).build()
style = ProfileHatchStyle(cut_pattern=HatchPattern.DIAGONAL, fill_pattern=HatchPattern.SOLID)
scene = ProfileViewRenderer.render([fg, eg], "Road", ProfileViewStyle(), hatch_style=style)
SvgWriter(scene).write("profile-hatch.svg")
DxfWriter(scene).write("profile-hatch.dxf")

hatches = ProfileHatchGenerator.generate(fg, eg, style, road_width=8)
assert hatches.total_area("cut") == 75.0
```

패턴은 단색, 대각선, 교차, 수평선, 수직선과 점을 지원합니다. `show_net=True`는 두 영역을 `net_color`로 표시하며 `HatchCollection.net_area`는 절토 면적에서 성토 면적을 뺀 값입니다. SVG에는 불투명도를 보존하고 DXF R12의 단색 채우기는 불투명한 `SOLID` 삼각형으로 저장합니다.

`sample_step`은 곡선 해치 외곽의 샘플 간격을 정합니다. 면적은 샘플로 구성한 종단면의 면적이며 체적은 그 면적에 일정한 `road_width`를 곱한 추정치입니다. 도로 폭을 생략하면 10m를 사용합니다.

## 절토·성토와 계획고·지반고 밴드

`ProfileViewBand(BandType.EARTHWORK)`를 추가하면 계획 종단과 현황 종단이 겹치는 구간에 측점, 계획고(FG), 지반고(EG), 절토 깊이(CUT), 성토 깊이(FILL)를 표시합니다. `EarthworkBandStyle.minimal()`은 측점과 절토·성토만 표시하고, `detailed()`는 부호가 있는 표고차(FG − EG)를 추가합니다.

```python
from myalignment.export.dxf_writer import DxfWriter
from myalignment.profile import EarthworkBandGenerator, EarthworkBandStyle, ProfileBuilder
from myalignment.profile.view_band import BandType, ProfileViewBand
from myalignment.profile.view_style import ProfileViewStyle
from myalignment.render.profile_view_renderer import ProfileViewRenderer

fg = ProfileBuilder("FG").add_tangent(1000, 1100, 10, 16).build()
eg = ProfileBuilder("EG").add_tangent(1000, 1100, 13, 13).build()
band_style = EarthworkBandStyle.detailed()
scene = ProfileViewRenderer.render(
    [fg, eg], "Road", ProfileViewStyle(vertical_exaggeration=3),
    [ProfileViewBand(BandType.EARTHWORK, gap=2)],
    earthwork_band_style=band_style, render_labels=False,
)
DxfWriter(scene).write("earthwork-band.dxf")

data = EarthworkBandGenerator.generate(fg, eg, band_style, road_width=8)
assert data.total_cut_volume == data.total_fill_volume == 600.0
```

- 종단 이름이 다르면 `profile_names=("설계 종단", "현황 종단")`으로 FG, EG 순서로 지정합니다. 렌더러의 `fg_profile_name`, `eg_profile_name`으로 공통 이름을 지정할 수도 있습니다. 이름을 생략하면 기본 이름 `FG`, `EG`와 종단 유형을 순서대로 확인합니다.
- `sample_interval`의 기본값은 50m입니다. 공통 구간의 시작점에서 간격을 계산하고 끝점을 포함합니다. 분할 뷰는 이 간격을 유지하면서 패널 경계에 값을 추가합니다. `alignment=`을 전달하면 측점 행에 측점 방정식을 적용합니다.
- `EarthworkBandGenerator.generate()`의 체적은 종단면 면적에 일정한 폭을 곱한 추정치입니다. `net_volume`은 성토량에서 절토량을 뺀 값입니다.
