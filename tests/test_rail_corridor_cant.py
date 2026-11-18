from dataclasses import dataclass

import pytest
from cadgeom import Point2d
from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.cant.curve import CantCurve, CantCriticalStation, CantPivotMethod
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.subassembly import Subassembly
from myalignment.assembly.point import AssemblyPoint
from myalignment.assembly.link import AssemblyLink
from myalignment.corridor.region import CorridorRegion
from myalignment.target.mapping import TargetMapping
from myalignment.assembly.subassembly import Subassembly
from myalignment.assembly.point import AssemblyPoint
from myalignment.assembly.link import AssemblyLink
from myalignment.assembly.codes import PointCode, LinkCode
# assembly/rail_codes.py 또는 assembly/codes.py 하단에 추가
from enum import Enum

class RailPointCode(Enum):
    """철도 전용 Point 코드."""
    TOP_OF_RAIL_LEFT = "Top_Of_Rail_Left"
    TOP_OF_RAIL_RIGHT = "Top_Of_Rail_Right"
    GAUGE_LINE_LEFT = "Gauge_Line_Left"
    GAUGE_LINE_RIGHT = "Gauge_Line_Right"
    SLEEPER_CENTER = "Sleeper_Center"
    BALLAST_BOTTOM = "Ballast_Bottom"
    BALLAST_SHOULDER = "Ballast_Shoulder"
    SUB_BALLAST = "Sub_Ballast"

class RailLinkCode(Enum):
    """철도 전용 Link 코드."""
    RAIL = "Rail"
    SLEEPER = "Sleeper"
    BALLAST = "Ballast"
    SUB_BALLAST = "Sub_Ballast"
    TRACK_BED = "Track_Bed"

class RailShapeCode(Enum):
    """철도 물량 산출용 Shape 코드."""
    BALLAST = "Ballast"
    SUB_BALLAST = "Sub_Ballast"
    CONCRETE_TRACK = "Concrete_Track"

@dataclass(frozen=True, slots=True)
class RailSubassembly(Subassembly):
    """철도 레일 및 도상 서브어셈블리 예시"""
    rail_width: float = 0.075  # 레일 저면 반폭 (m)
    rail_height: float = 0.15  # 레일 높이 (m)

    def generate_geometry(self, target_mapping=None) -> tuple[tuple[AssemblyPoint, ...], tuple[AssemblyLink, ...]]:
        # 로컬 좌표계 기준점(0, 0)에서 시작하는 레일 형상 정의
        p1 = AssemblyPoint(code=RailPointCode.TOP_OF_RAIL_LEFT, x=-0.75, z=self.rail_height)
        p2 = AssemblyPoint(code=RailPointCode.TOP_OF_RAIL_LEFT, x=-0.75, z=0.0)
        p3 = AssemblyPoint(code=RailPointCode.TOP_OF_RAIL_RIGHT, x=0.75, z=self.rail_height)
        p4 = AssemblyPoint(code=RailPointCode.TOP_OF_RAIL_RIGHT, x=0.75, z=0.0)
        l1 = AssemblyLink(code=RailLinkCode.RAIL, start=p1, end=p2)
        l2 = AssemblyLink(code=RailLinkCode.RAIL, start=p3, end=p4)
        p5 = AssemblyPoint(code=RailPointCode.SLEEPER_CENTER, x=-1.2, z=0.0)
        p6 = AssemblyPoint(code=RailPointCode.SLEEPER_CENTER, x=1.2, z=0.0)
        l3 = AssemblyLink(code=RailLinkCode.SLEEPER, start=p5, end=p6)

        return (p1, p2, p3, p4, p5, p6), (l1 ,l2 ,l3)

def test_rail_alignment_and_cant_corridor():
    # 1. 철도 선형 생성 테스트
    rail = (
        AlignmentBuilder("본선")
        .with_pi_coords([(0, 0), (500, 0), (1000, 200)])
        .with_radii([None, 800, None])
        .as_rail_alignment(gauge=1.435)
        .build()
    )

    assert rail.is_rail is True
    assert rail.gauge == 1.435
    assert rail.name == "본선"

    # 2. 캔트(Cant) 커브 정의 (내측 레일 피벗 방식)
    cant = CantCurve(
        name="R=800 곡선부",
        start_station=200.0,
        end_station=400.0,
        pivot_method=CantPivotMethod.LEFT_RAIL,
        critical_stations=(
            CantCriticalStation(station=200.0, cant_value=0.0, left_rail_delta=0.0, right_rail_delta=0.0),
            CantCriticalStation(station=300.0, cant_value=0.105, left_rail_delta=0.0, right_rail_delta=0.105,
                                is_full_cant=True),
            CantCriticalStation(station=400.0, cant_value=0.0, left_rail_delta=0.0, right_rail_delta=0.0),
        ),
    )

    # 3. 간단한 테스트용 어셈블리 생성 (좌우 폭 1.5m 지점 포함)
    # Subassembly 구현체나 모의 객체 대신 직접 점/링크를 반환하는 커스텀 어셈블리 테스트 예시

    assembly = (
        AssemblyBuilder("철도단면")
        .add_right(RailSubassembly())
        .build()
    )

    # 4. CorridorRegion 생성 및 캔트 적용 크로스 섹션 테스트
    region = CorridorRegion(
        name="철도구간",
        start_station=200.0,
        end_station=400.0,
        frequency=50.0,
        assembly=assembly,
        cant_curve=cant,
    )

    # 4-1. 캔트가 없는 시점(Station 200.0) 검증 (초기 높이 0.15)
    points_start, _ = region.cross_section_at(200.0)
    right_pt_start = next(p for p in points_start if p.code == RailPointCode.TOP_OF_RAIL_RIGHT and p.x > 0)
    assert pytest.approx(right_pt_start.z, abs=1e-6) == 0.15

    # 4-2. 최대 캔트가 적용되는 지점(Station 300.0) 검증
    points_max, _ = region.cross_section_at(300.0)
    right_pt_max = next(p for p in points_max if p.code == RailPointCode.TOP_OF_RAIL_RIGHT and p.x > 0)

    # LEFT_RAIL 피벗 기하학에 따른 실제 계산값(약 0.2574) 검증
    assert right_pt_max.z > 0.15
    assert pytest.approx(right_pt_max.z, abs=1e-3) == 0.25738