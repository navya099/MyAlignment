# tests/assembly/test_subassembly.py
import math
import pytest
from myalignment.assembly.codes import PointCode, LinkCode, ShapeCode
from myalignment.assembly.link import AssemblyLink
from myalignment.assembly.point import AssemblyPoint
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.assembly.subassemblies.ditch import VShapeDitch
from myalignment.assembly.subassemblies.shoulder import Shoulder
from myalignment.assembly.subassemblies.side_slope import SideSlope
from myalignment.assembly.subassembly import Subassembly


def test_basic_lane():
    lane = BasicLane(width=3.5, slope=-0.02, side=+1)
    points, links = lane.generate_geometry()
    assert len(points) == 4   # 상단 2 + 포장 하단 2
    # 상단 점 확인
    top = [p for p in points if p.code == PointCode.LANE_EDGE]
    assert len(top) == 2
    assert math.isclose(top[0].x, 0.0)
    assert math.isclose(top[1].x, 3.5)


def test_shoulder():
    sh = Shoulder(width=2.0, slope=-0.04)
    points, links = sh.generate_geometry()
    assert math.isclose(points[1].x, 2.0)
    assert math.isclose(points[1].z, -0.08)


def test_side_slope():
    slope = SideSlope(slope_ratio=1.5, height=5.0)
    points, links = slope.generate_geometry()
    assert math.isclose(points[1].x, 7.5)
    assert math.isclose(points[1].z, -5.0)


def test_v_ditch():
    ditch = VShapeDitch(width=1.5, depth=0.5)
    points, links = ditch.generate_geometry()
    assert len(points) == 3
    assert len(links) == 2
    assert math.isclose(points[1].z, -0.5)


def test_place_at():
    lane = BasicLane(width=3.5, slope=-0.02, side=+1)
    points, links = lane.place_at(origin_x=5.0, origin_z=1.0)
    assert math.isclose(points[0].x, 5.0)
    assert math.isclose(points[1].x, 8.5)






@pytest.mark.parametrize("side", [-1, 1])
def test_negative_lane_crossfall_lowers_outer_edges_on_both_sides(side):
    lane = BasicLane(width=4, slope=-0.02, side=side)
    points, _ = lane.place_at(origin_x=0, origin_z=1)
    assert points[1].x == pytest.approx(side * 4)
    assert points[1].z == pytest.approx(0.92)
    assert points[2].z == pytest.approx(0.82)
