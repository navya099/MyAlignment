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

DXF writer는 R12 텍스트 DXF를 생성하고 한글은 CP949로 저장합니다. R12의 출력 범위에는 Civil 3D 편집 객체나 선가중치 속성이 포함되지 않습니다. Civil 3D에서 직접 파일을 여는 검증은 별도로 필요합니다.
