# 철도와 분기기

## 철도 코리더와 캔트

`as_rail_alignment()`에 궤간과 캔트 곡선을 지정합니다. 캔트 값은 우측 레일 표고에서 좌측 레일 표고를 뺀 값이며 단위는 m입니다. 코리더 단면에 캔트를 적용할 영역에는 `cant_curve=`로 같은 곡선을 전달합니다.

```python
from math import isclose

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.codes import PointCode
from myalignment.assembly.subassemblies.rail_track import SingleTrack
from myalignment.cant.curve import CantCriticalStation, CantCurve, CantPivotMethod
from myalignment.corridor.rail_corridor_builder import RailCorridorBuilder
from myalignment.export.dxf_writer import DxfWriter
from myalignment.profile.profile import ProfileBuilder
from myalignment.profile.profiletype import ProfileType
from myalignment.render.cant_diagram_composer import CantDiagramComposer

cant = CantCurve(
    name="Curve",
    start_station=100,
    end_station=200,
    pivot_method=CantPivotMethod.LEFT_RAIL,
    critical_stations=(
        CantCriticalStation(station=100),
        CantCriticalStation(station=150, cant_value=0.105, is_full_cant=True),
        CantCriticalStation(station=200),
    ),
)
grade = ProfileBuilder("FG", ProfileType.FG).add_tangent(100, 200, 50, 51).build()
rail = (
    AlignmentBuilder("Track").with_pi_coords([(0, 0), (100, 0)])
    .with_start_station(100).with_profile(grade)
    .as_rail_alignment(gauge=1.435, cant_curves=[cant]).build()
)
assembly = AssemblyBuilder().add_center(SingleTrack(gauge=rail.gauge)).build()
corridor = (
    RailCorridorBuilder("Rail corridor")
    .add_rail_baseline(rail, grade.name, 100, 200)
    .add_rail_region("Track region", 100, 200, assembly, cant_curve=cant)
    .build()
)
points, _ = corridor.cross_section_at(150)
rail_z = {point.code: point.z for point in points}
assert isclose(rail_z[PointCode.RIGHT_RAIL] - rail_z[PointCode.LEFT_RAIL], 0.105)
DxfWriter(CantDiagramComposer.separate(rail)).write("cant.dxf")
```

단면의 `point.z`는 로컬 표고 변위입니다. 설계 종단 표고까지 더한 월드 단면은 `CrossSection3D` 또는 `SectionViewBuilder`로 조회합니다. 캔트 다이어그램이나 종단 뷰의 `BandType.CANT_DATA`는 선형에 등록된 캔트를 읽습니다.

## 분기기 제원과 시저스 자동 배치

```python
from math import isclose

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.turnout.scissors_crossover import ScissorsCrossover
from myalignment.turnout.table import TurnoutTable
from myalignment.turnout.table_builder import TurnoutTableBuilder
from myalignment.turnout.turnout import Turnout

catalog = TurnoutTableBuilder("Demo").add("No. 12", 12, lead_length=30, radius=300).build()
catalog.to_csv("turnout-table.csv")
catalog = TurnoutTable.from_csv("turnout-table.csv", name="Demo")
turnout = Turnout.from_table("T1", catalog, "No. 12", "A", "Branch", 1150)
assert turnout.station_on_source == 1150
a = (
    AlignmentBuilder("A").with_pi_coords([(0, 0), (500, 0)])
    .with_start_station(1000).as_rail_alignment().build()
)
b = (
    AlignmentBuilder("B").with_pi_coords([(40, 5), (500, 5)])
    .with_start_station(2000).as_rail_alignment().build()
)
crossing = ScissorsCrossover.symmetric_auto_at(
    "SC1", a, b, catalog.get_or_raise("No. 12").to_turnout_type(), 1200,
)
assert crossing.is_valid
assert isclose(crossing.geometry.diamond_center.y, 2.5)
print([item.station_on_source for item in crossing.turnouts])
```

`center`는 첫 번째 본선의 원시 측점입니다. 자동 배치는 평행하고 진행 방향이 같은 본선에서 두 번째 본선의 측점 원점과 양쪽 분기 방향을 계산합니다. 수동 배치는 `ScissorsCrossoverBuilder.with_stations()`과 `with_sides()`를 사용합니다. 일반 단·복선 연결은 `CrossoverBuilder`로 모델을 생성하고 `compute_geometry(a, b)`로 기하를 계산합니다. 결과의 유효성과 오류 메시지를 확인하세요.

분기기 기하는 직선 접근부와 원호로 이상화합니다. `lead_length`는 이 모델의 원곡선 앞 직선장입니다. 시공·승인에는 제조사 제원과 별도의 설계 검증이 필요합니다.

## 분기기 2D·3D 출력

`TurnoutPreview`는 같은 레일 좌표를 사용해 평면도 DXF와 3D DXF·HTML을 만듭니다. 궤간은 철도 선형에서 가져오며 3D의 `elevation`은 모델 기준 표고입니다.

```python
from myalignment.alignment import AlignmentBuilder
from myalignment.turnout.turnout import Turnout
from myalignment.turnout.turnout_preview import TurnoutPreview
from myalignment.turnout.type import TurnoutSide, TurnoutType

axis = (
    AlignmentBuilder("Main").with_pi_coords([(0, 0), (500, 0)])
    .with_start_station(1000).as_rail_alignment().build()
)
kind = TurnoutType("No. 12", frog_number=12, lead_length=30, radius=300)
turnout = Turnout("T1", kind, axis.name, "Branch", 1150, TurnoutSide.RIGHT)

plan = TurnoutPreview.preview_2d(axis, turnout, dxf_path="turnout-plan.dxf")
spatial = TurnoutPreview.preview_3d(
    axis, [turnout], elevation=50, dxf_path="turnout-3d.dxf", html_path="turnout-3d.html",
)
assert plan.primitives and spatial.primitives
```

PS는 본선의 원시 측점입니다. 표시용 PF는 분기곡선 끝의 종방향 길이에 해당하는 본선 위치이고, PC는 분기 중심선의 곡선 끝입니다. PC의 측점은 PS부터 잰 분기 중심선 거리입니다. 분기 중심선은 PS의 접선으로 시작하는 이상화된 직선·원곡선입니다. 마커와 레일은 배치 확인용이며 실제 크로싱과 여유 한계는 제조사 제원으로 확인해야 합니다.

`TurnoutGeometryCalculator.calculate()`로 만든 기하를 `TurnoutRenderer.render_2d()`와 `Turnout3DRenderer.render_3d()`에 전달하면 기존 Scene에 추가하거나 마커와 침목 표시를 조정할 수 있습니다. 3D 렌더러의 `rail_elevation`은 모델 기준 표고 위 레일 높이입니다. 3D HTML을 여는 방법은 [도면과 3D 출력](rendering.md#횡단-뷰-3d-dxf와-브라우저-미리보기)을 참고하세요.

## 크로스오버 2D·3D 출력

`Crossover2DPreview`는 평면도 Scene을 만들고 선택적으로 DXF를 저장합니다. 단일 크로스오버는 연결 경로 하나를, 이중 크로스오버는 두 경로를 사용합니다. 각 연결 경로에는 좌우 레일이 있으며, 다이아몬드 마커는 두 직선 연결부의 실제 교점을 표시합니다.

```python
from math import tan

from myalignment.alignment import AlignmentBuilder
from myalignment.turnout.crossover_3d_preview import Crossover3DPreview
from myalignment.turnout.crossover_builder import CrossoverBuilder
from myalignment.turnout.crossover_preview import Crossover2DPreview
from myalignment.turnout.type import TurnoutSide, TurnoutType

a = AlignmentBuilder("A").with_pi_coords([(0, 0), (500, 0)]).as_rail_alignment().build()
b = AlignmentBuilder("B").with_pi_coords([(0, 4.3), (500, 4.3)]).as_rail_alignment().build()
kind = TurnoutType("No. 12", frog_number=12, lead_length=17, radius=373)
advance = 2 * kind.run + (4.3 - 2 * kind.rise) / tan(kind.frog_angle)
crossover = (
    CrossoverBuilder("X1").with_alignments("A", "B").with_turnout_type(kind)
    .at_stations(100, 100 + advance).with_sides(TurnoutSide.LEFT, TurnoutSide.RIGHT)
    .as_double().build()
)

scene = Crossover2DPreview.preview(a, b, crossover, dxf_path="crossover.dxf")
assert any(layer.name == "C-CROSSOVER-DIAMOND" for layer in scene.layers)
spatial = Crossover3DPreview.preview(
    a, b, crossover, elevation=50,
    dxf_path="crossover-3d.dxf", html_path="crossover-3d.html",
)
assert any(primitive.style.layer == "C-CROSSOVER-3D-DIAMOND" for primitive in spatial.primitives)
```

`preview(..., scene=기존_scene)`로 여러 평면도를 합성할 수 있습니다. 궤간, 샘플 간격, 표시 범위를 직접 정하려면 `CrossoverGeometryCalculator.calculate()`의 결과를 `Crossover2DRenderer.render_2d()`에 넘깁니다. PS와 PF 레이블은 해당 본선의 원시 측점을 표시합니다.

3D에서는 같은 레일 좌표를 기준 표고에 배치하고 본선과 연결 경로를 따라 침목을 그립니다. PS·PF와 다이아몬드는 수직 마커로 표시합니다. `Crossover3DRenderer.render_3d()`에서 레일 상단 높이, 침목 간격, 마커 표시를 설정할 수 있습니다. 여러 크로스오버를 합성할 때는 `Crossover3DPreview.preview(..., scene=기존_scene3d)`로 이전 결과를 전달합니다. 3D HTML을 여는 방법은 [도면과 3D 출력](rendering.md#횡단-뷰-3d-dxf와-브라우저-미리보기)을 참고하세요.
