# 도면과 3D 출력

## 평면 스타일과 레이블

표시 규칙과 레이블 규칙을 선형에 붙인 후 `AlignmentRenderer.render_plan()`을 호출합니다. 주요·보조 측점, 기하점, 선형 요소와 측점 방정식 레이블을 각각 설정할 수 있습니다. 단일 모델의 여러 레이어를 합성할 때는 `SceneComposer`와 `RenderOptions`를 사용합니다.

```python
from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.alignment.equation_label_style import StationEquationLabelStyle
from myalignment.alignment.label_set import AlignmentLabelSet
from myalignment.alignment.style.alignment_style import AlignmentStyle
from myalignment.alignment.style.display_rule import AlignmentComponent, DisplayRule, ViewType
from myalignment.export.dxf_writer import DxfWriter
from myalignment.render.composer import RenderOptions, SceneComposer
from myalignment.render.stagger_presets import StaggerConfigPresets

style = AlignmentStyle.basic().with_rule(DisplayRule(AlignmentComponent.LINE, ViewType.PLAN, color=3))
labels = AlignmentLabelSet.with_minor_text().with_equation_style(StationEquationLabelStyle.minimal())
axis = (
    AlignmentBuilder("본선").with_pi_coords([(0, 0), (100, 0)]).with_style(style).build()
    .with_label_set(labels).add_station_equation(50, 1000)
)
scene = SceneComposer.compose_alignment(
    axis,
    RenderOptions(render_alignment_labels=True, stagger_config=StaggerConfigPresets.up_increment()),
)
assert scene.primitives
DxfWriter(scene).write("alignment-labels.dxf")
```

레이블 겹침 조정은 `StaggerConfig`의 위치와 간격 설정을 적용합니다. 종단과 종단 레이블 출력은 [종단과 종단 뷰](profile.md), 캔트 출력은 [철도와 분기기](rail.md)를 참고하세요.

## 횡단 뷰, 3D DXF와 브라우저 미리보기

```python
from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.corridor.corridor_3d_preview import Corridor3DPreview
from myalignment.corridor.corridor_3d_renderer import Corridor3DRenderer
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.export.dxf_3d_writer import Dxf3DWriter
from myalignment.export.dxf_writer import DxfWriter
from myalignment.export.json_3d_exporter import Json3DExporter
from myalignment.section.label_set import SectionLabelSet
from myalignment.section.section_view_builder import SectionViewBuilder
from myalignment.section.section_view_style import SectionViewStyle

axis = AlignmentBuilder("Axis").with_pi_coords([(0, 0), (40, 0)]).build()
assembly = AssemblyBuilder().add_both(lambda side: BasicLane(side=side)).build()
corridor = (
    CorridorBuilder("Road")
    .add_baseline("BL", axis.name, "", 0, 40)
    .add_region("Lane", 0, 40, assembly)
    .build()
)
sections = SectionViewBuilder.grid_layout(
    corridor, axis, [0, 20, 40], SectionViewStyle(), columns=2, label_set=SectionLabelSet.full(),
)
DxfWriter(sections).write("sections.dxf")
mesh = Corridor3DRenderer.render_mesh(corridor, axis, sample_frequency=5)
assert mesh.primitives
Dxf3DWriter(mesh).write("road-3d.dxf")
Json3DExporter.export(mesh, "road-3d.json")
Corridor3DPreview.mesh(corridor, axis, "road-3d.html", sample_frequency=5)
```

`SectionViewBuilder.single()`은 단일 단면을, `grid_layout()`은 여러 측점의 단면을 도면에 배치합니다. 원지형까지 겹칠 때는 `SectionViewComposer.with_surface()`를 사용합니다. 3D 뷰는 `render_wireframe()`, `render_sections_only()`, `render_mesh()` 중 원하는 표현을 선택할 수 있습니다.

HTML은 현재 폴더에서 `python -m http.server 8765`를 실행하고 `http://127.0.0.1:8765/road-3d.html`에서 엽니다. 기본 뷰어는 Three.js를 CDN에서 불러옵니다. 오프라인 환경에는 동일 버전의 배포 디렉터리를 준비한 뒤 `three_module_base="./vendor"`처럼 지정합니다.

## 횡단 뷰에 객체 투영

`SectionProjectionComposer.project_all()`은 기준 선형에 등록된 구조물과 전달한 관로, 점, FeatureLine, 대상 선형을 지정한 횡단면에 투영합니다. 투영 결과는 `single_with_projections()` 또는 `grid_layout(projections_by_station=...)`에 전달합니다. 개별 객체에 표시 스타일을 지정하려면 `SectionProjectionBuilder`를 사용합니다.

```python
from cadgeom import Point2d
from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.export.dxf_writer import DxfWriter
from myalignment.section.projection_composer import SectionProjectionComposer
from myalignment.section.section_view_builder import SectionViewBuilder
from myalignment.structure.bridge import Bridge

axis = (
    AlignmentBuilder("Axis").with_pi_coords([(0, 0), (40, 0)])
    .with_structure(Bridge.create("Bridge", 15, 25, width=12, bottom_elevation=2.5))
    .build()
)
assembly = AssemblyBuilder().add_both(lambda side: BasicLane(side=side)).build()
corridor = (
    CorridorBuilder("Road").add_baseline("BL", axis.name, "", 0, 40)
    .add_region("Lane", 0, 40, assembly).build()
)
sections = {
    station: SectionProjectionComposer.project_all(
        axis, station,
        pipes=[(Point2d(20, -6), -3, 1.2, "Drain")],
        points=[(Point2d(30, 4), 1.5, "Survey point")],
    )
    for station in (20, 30)
}
scene = SectionViewBuilder.grid_layout(corridor, axis, [20, 30], columns=2, projections_by_station=sections)
DxfWriter(scene).write("section-projections.dxf")
```

- 측점에는 측점 방정식 적용 전의 기하 측점을 사용합니다. 횡거는 진행 방향 기준 오른쪽이 양수입니다. 점과 관 중심의 횡단면까지 허용 거리는 기본 1m이며 `station_tolerance`로 지정합니다.
- FeatureLine의 교차 표고는 선분에서 보간합니다. 횡단면 위에 놓인 선분은 그대로 연결합니다. 대상 선형은 교차 위치에서 해당 선형의 종단 표고를 사용합니다.
- 구조물은 개략 단면으로 표시합니다. 교량의 기본 폭은 20m, 상판 두께는 2m입니다. `width`, `deck_height`, `pier_bottom_elevation` 메타데이터로 치수를 지정합니다. 터널은 `diameter`를 사용하며 기본값은 4m입니다. 하단 표고는 `bottom_elevation`, 해당 측점을 포함하는 종단, 0m 순서로 결정합니다. 기준 종단을 직접 선택하려면 `project_all(profile=...)`을 사용합니다.
- 투영 레이어 이름, 외곽선, 마커, 레이블은 `SectionProjectionStyle`로 설정합니다. 원지형도 표시할 때는 `SectionViewComposer.with_surface(projections=...)`를 사용합니다.

DXF writer는 R12 텍스트 DXF를 생성하고 한글은 CP949로 저장합니다. R12의 출력 범위에는 Civil 3D 편집 객체나 선가중치 속성이 포함되지 않습니다. Civil 3D에서 직접 파일을 여는 검증은 별도로 필요합니다.

## 3D 드라이브 뷰

`DriveViewPreview.preview()`는 선형을 따라 카메라 경로를 생성하고 브라우저에서 재생할 수 있는 HTML을 저장합니다. 코리더를 전달하면 3D 메시를 배경으로 사용합니다.

```python
from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.drive.camera_direction import CameraDirectionMode
from myalignment.drive.drive_config import DriveViewConfig
from myalignment.drive.drive_preview import DriveViewPreview
from myalignment.profile.profile import ProfileBuilder

grade = ProfileBuilder("Grade").add_tangent(0, 40, 10, 12).build()
axis = (
    AlignmentBuilder("Road").with_pi_coords([(500000, 300000), (500040, 300000)])
    .with_profile(grade).build()
)
assembly = AssemblyBuilder().add_both(lambda side: BasicLane(side=side)).build()
corridor = (
    CorridorBuilder("Road").add_baseline_from_alignment(axis, grade)
    .add_region("Paving", 0, 40, assembly).build()
)
config = DriveViewConfig(
    speed_kmh=36, sample_interval=5, x_offset=1.7, y_offset=1.5,
    direction_mode=CameraDirectionMode.LOOK_AHEAD, look_ahead_distance=15,
)
DriveViewPreview.preview(axis, config, "drive.html", corridor)
```

- `start_station`과 `end_station`은 기하 측점입니다. `station_offset`은 선형 진행 방향, `x_offset`은 오른쪽, `y_offset`은 위쪽이 양수입니다. 카메라가 선형과 종단의 유효 범위 안에 있도록 주행 구간을 조정합니다.
- 카메라 높이는 `surface_elevation_func(x, y)`, 선택한 종단, 0m 순서로 기준 표고를 구한 뒤 `y_offset`을 더합니다. 코리더에 지정한 종단이 하나면 미리보기가 해당 종단을 선택합니다. 여러 종단이 있으면 `baseline_name`이나 `profile`을 지정할 수 있습니다.
- HTML에서 재생·일시정지, 위치 탐색, 재생 속도 조절과 전체 보기를 사용할 수 있습니다. 자유 시점에서는 드래그로 주시 방향을 바꿀 수 있습니다. 브라우저의 실제 시야각은 `field_of_view`를 사용합니다.
- 카메라 프레임이 필요하면 `DriveViewGenerator.generate()`를 호출합니다. `DrivePath.at_time()`은 초 단위로 프레임을 보간합니다. `DriveView3DRenderer`는 경로와 방향선을 별도 장면에 그릴 때 사용합니다.

## 2D Scene을 SVG로 내보내기

`SvgWriter`와 `SvgExporter`는 평면도, 종단 뷰, 횡단 뷰 등 기존 2D `Scene`을 SVG로 저장합니다. 선, 열린·닫힌 폴리라인, 원, 원호와 회전·여러 줄 텍스트를 지원합니다. 레이어 이름, 표시 상태, ACI 색상과 표준 선종류도 반영합니다.

```python
from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.export.svg_composer import SvgExportComposer
from myalignment.export.svg_gallery import SvgGallery
from myalignment.export.svg_style import SvgStyle
from myalignment.render.alignment_renderer import AlignmentRenderer

axis = (
    AlignmentBuilder("Main").with_pi_coords([(0, 0), (40, 0), (70, 30)])
    .with_radii([None, 12, None]).build()
)
scene = AlignmentRenderer.render_plan(axis)
outputs = SvgExportComposer.export_all(
    {"평면도": scene, "밝은 글꼴": scene}, "svg",
    {"평면도": SvgStyle.print(), "밝은 글꼴": SvgStyle.dark()},
)
SvgGallery.create(outputs.items(), "svg/index.html", title="평면도 비교")
```

단일 도면은 `SvgExporter.export(scene, "plan.svg", SvgStyle.web())`로 저장할 수 있습니다. 기본값은 A4 가로, 10mm 여백, 자동 맞춤입니다. 자동 맞춤은 표시 중인 객체만 기준으로 하며, 텍스트 범위는 글꼴 크기로 추정하므로 실제 폭은 브라우저 글꼴에 따라 달라집니다. `auto_fit_viewport=False`에서는 1 도면 단위가 1mm에 대응하고 CAD 원점은 페이지 왼쪽 아래 여백에 놓입니다.

## 평면·종단 도면 시트

`SheetComposer`는 같은 원시 측점 구간의 평면도와 종단도를 한 시트에 배치합니다. 선형·지형의 월드 좌표와 종단의 측점·표고는 미터 단위로 입력하고, 출력 도형은 용지의 좌하단을 원점으로 하는 밀리미터 좌표를 사용합니다. 평면 축척과 종단의 수평·수직 축척을 각각 지정할 수 있습니다.

```python
import math

from myalignment.alignment import AlignmentBuilder
from myalignment.export.sheet_exporter import SheetExporter
from myalignment.profile import ProfileBuilder
from myalignment.sheet import SheetComposer, SheetLayout

alignment = (
    AlignmentBuilder("Main Road")
    .with_pi_coords([(450000, 4180000), (450000, 4180220)])
    .with_start_station(1000).build()
)
design = ProfileBuilder("FG").add_tangent(1000, 1220, 100, 104).build()
ground = ProfileBuilder("EG").add_tangent(1000, 1220, 102, 103).build()
layout = SheetLayout.standard_a3(plan_scale=500, profile_scale=1000, drawing_number="C-01")
scene = SheetComposer.compose(
    layout, alignment, design, ground,
    station_start=1020, station_end=1120,
    plan_rotation=math.pi / 2,
    profile_datum=98, profile_vertical_scale=100,
)
profile_view = scene.metadata["profile_transform"]
assert profile_view.to_paper(1120, 100).x - profile_view.to_paper(1020, 100).x == 100
SheetExporter.export_svg(scene, "plan-profile.svg")
SheetExporter.export_dxf(scene, "plan-profile.dxf")
```

- `plan_center`는 평면 뷰포트 중심의 월드 XY입니다. 생략하면 선택한 선형 구간을 중심에 배치합니다. `plan_rotation`은 월드 +X축에서 용지 +X축까지의 반시계 방향 각도(라디안)입니다. `scene.metadata["plan_transform"]`의 `to_world()`로 시트의 평면도 좌표를 월드 XY로 역변환할 수 있습니다.
- 종단의 `profile_datum`은 그리드 하단 표고입니다. 생략하면 선택 구간의 종단과 투영 객체에서 기준고를 계산합니다. `profile_vertical_scale`을 생략하면 `ProfileViewStyle.vertical_exaggeration`으로 수직 축척을 정합니다. 그리드 밖의 종단 기하는 잘리므로 필요하면 기준고와 수직 축척을 조정합니다. 측점 방정식은 레이블에 적용하며, 도형 배치에는 원시 측점을 사용합니다. FG와 EG가 겹치면 절토·성토 밴드를 기본 표시합니다.
- `surface=`로 지형 등고선을, `corridor=`로 저장된 피처라인과 표면 경계를 추가합니다. 관망이나 구조물 등 이미 그린 월드 XY 장면은 `plan_scene=`으로 전달합니다. 긴 구간은 `SheetComposer.compose_series()`로 동일 축척의 연속 시트를 만들 수 있습니다. `compose()`에서 끝 측점을 생략하면 첫 시트의 폭에 해당하는 구간을 사용합니다.
- SVG와 PDF의 용지 크기는 시트에서 가져옵니다. `SheetExporter.export_pdf()`에는 CairoSVG 또는 Inkscape가 필요합니다. DXF는 용지 mm 좌표로 변환된 도형을 R12 모델 공간에 기록합니다.
