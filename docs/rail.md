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
