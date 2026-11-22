# 시작하기

## 설치

Python 3.11 이상과 Git을 준비하고 저장소 루트에서 실행합니다. `cadgeom` 설치에는 GitHub의 의존 저장소에 접근할 수 있어야 합니다.

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# PowerShell에서는 .venv\Scripts\Activate.ps1 실행
python -m pip install .
```

대규모 TIN에는 선택 의존성인 SciPy를 설치할 수 있습니다. SciPy가 없으면 내장 삼각분할을 사용합니다.

```bash
python -m pip install scipy
```

## 선형부터 도면까지

아래 코드를 `first_project.py`로 저장하고 `python first_project.py`로 실행합니다. 길이 100m 평면선형의 시점은 STA 1000이고, 완성된 차도의 평면 폭은 7m입니다. 예제의 좌표와 표고는 m 단위입니다.

```python
from pathlib import Path
from math import isclose

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.corridor.corridor_3d_renderer import Corridor3DRenderer
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.corridor.surface_builder import CorridorSurfaceSpec
from myalignment.export.dxf_3d_writer import Dxf3DWriter
from myalignment.export.dxf_writer import DxfWriter
from myalignment.profile.profile import ProfileBuilder
from myalignment.profile.profiletype import ProfileType
from myalignment.render.alignment_renderer import AlignmentRenderer
from myalignment.section.section_view_builder import SectionViewBuilder

grade = ProfileBuilder("FG", ProfileType.FG).add_tangent(1000, 1100, 100, 102).build()
axis = (
    AlignmentBuilder("Main")
    .with_pi_coords([(220000, 410000), (220100, 410000)])
    .with_start_station(1000)
    .with_profile(grade)
    .build()
)
assembly = AssemblyBuilder().add_both(lambda side: BasicLane(side=side)).build()
corridor = (
    CorridorBuilder("Road")
    .add_baseline("BL Main", axis.name, grade.name, axis.start_station, axis.end_station)
    .add_region("Road section", axis.start_station, axis.end_station, assembly, baseline_name="BL Main")
    .build()
)

surface = corridor.build_surface(CorridorSurfaceSpec(), alignments={axis.name: axis})
assert isclose(surface.area_2d, 700)
assert isclose(grade.elevation_at(1050), 101)

output = Path("output")
output.mkdir(exist_ok=True)
DxfWriter(AlignmentRenderer.render_plan(axis)).write(output / "plan.dxf")
DxfWriter(SectionViewBuilder.single(corridor, axis, 1050)).write(output / "section.dxf")
Dxf3DWriter(Corridor3DRenderer.render_mesh(corridor, axis)).write(output / "corridor-3d.dxf")
print(f"STA {axis.start_station:.0f}–{axis.end_station:.0f}, 표면적 {surface.area_2d:.1f} m²")
```

출력은 `STA 1000–1100, 표면적 700.0 m²`입니다. `output/`에는 평면도, STA 1050 횡단면, 코리더 3D 메시가 저장됩니다. 도면 설정은 [도면과 3D 출력](rendering.md)에서 확인할 수 있습니다.

## 측점과 좌표 규약

- 기하 조회와 코리더 계산에는 연속된 원시 측점을 사용합니다. 측점 방정식의 표시 측점은 `raw_to_display_station()`으로 변환합니다.
- `point_at(station, offset)`의 횡거는 진행 방향 기준 오른쪽이 양수입니다. `distance_to_alignment()`는 탐색 결과에서 왼쪽을 양수로 반환합니다.
- 방위각은 +X축이 0인 라디안이며 반시계 방향이 양수입니다. 구배·횡단 경사는 소수로 입력합니다. `0.02`는 2%입니다.
- 편집과 `with_*` 메서드가 새 모델을 반환하는 경우 결과를 변수에 다시 할당합니다.
