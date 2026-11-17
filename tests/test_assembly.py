# tests/assembly/test_assembly.py
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.codes import PointCode, LinkCode, ShapeCode
from myalignment.assembly.link import AssemblyLink
from myalignment.assembly.point import AssemblyPoint
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.assembly.subassemblies.ditch import VShapeDitch
from myalignment.assembly.subassemblies.shoulder import Shoulder
from myalignment.assembly.subassemblies.side_slope import SideSlope
from myalignment.assembly.subassembly import Subassembly
import math

def test_assembly_symmetric():
    a = (
        AssemblyBuilder("표준단면")
        .add_both(lambda side: BasicLane(width=3.5, slope=-0.02, side=side))
        .add_both(lambda side: Shoulder(width=2.0, slope=-0.04, side=side))
        .build()
    )

    points, links = a.generate_cross_section()

    # centerline + 좌/우 각 2개 서브어셈블리 × 2점 = 8점
    # 중복 제거: 5점 (centerline + 좌/우 각 2점)
    assert len(points) >= 5
    assert len(links) >= 4

    # 우측 차로 끝 = x=3.5
    lane_edges = [p for p in points if p.code == PointCode.LANE_EDGE]
    assert len(lane_edges) == 2
    assert any(math.isclose(p.x, 3.5) for p in lane_edges)
    assert any(math.isclose(p.x, -3.5) for p in lane_edges)


def test_assembly_with_slope():
    a = (
        AssemblyBuilder()
        .add_right(BasicLane(width=3.5, slope=-0.02, side=+1))
        .add_right(Shoulder(width=2.0, slope=-0.04, side=+1))
        .add_right(SideSlope(slope_ratio=1.5, height=5.0, side=+1))
        .add_left(BasicLane(width=3.5, slope=-0.02, side=-1))
        .add_left(Shoulder(width=2.0, slope=-0.04, side=-1))
        .add_left(SideSlope(slope_ratio=1.5, height=5.0, side=-1))
        .build()
    )

    points, links = a.generate_cross_section()
    for p in points:
        print(f"{p.code}: x={p.x}, z={p.z}")
    assert len(points) > 0
    assert len(links) > 0

    # 전체 폭 확인
    xs = [p.x for p in points]
    total_width = max(xs) - min(xs)
    # 우측: 3.5+2+7.5=13, 좌측: 13 → 총 26
    assert math.isclose(total_width, 26.0, abs_tol=0.1)