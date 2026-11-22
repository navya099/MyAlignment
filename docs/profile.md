# 종단과 종단 뷰

`ProfileBuilder`로 설계 종단(`ProfileType.FG`)과 현황 종단(`ProfileType.EG`)을 구성합니다. 입력 측점은 선형의 원시 측점과 맞춥니다. 인접 종단 요소의 경계 측점과 표고는 연속이어야 합니다. 접선 연결부의 구배까지 연속이어야 하는 모델은 `build(validate_grades=True)`로 검증할 수 있습니다.

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
