# tests/surface/test_breakline.py
import math
import pytest
from myalignment.surface.breakline_vertex import BreaklineVertex
from myalignment.surface.breakline import Breakline
from myalignment.surface.breakline_type import BreaklineType
from myalignment.surface.breakline_set import BreaklineSet


def test_breakline_length():
    bl = Breakline.from_coords([(0, 0, 100), (10, 0, 100), (20, 0, 100)])
    assert math.isclose(bl.length_2d, 20.0)


def test_breakline_elevation_at_xy():
    bl = Breakline.from_coords([(0, 0, 100), (10, 0, 110)])
    # 중간점 (5, 0) → 105
    assert math.isclose(bl.elevation_at_x_y(5, 0), 105.0)
    # 선분 위 아님
    assert bl.elevation_at_x_y(5, 1) is None


def test_breakline_wall_requires_right_elevations():
    with pytest.raises(ValueError):
        Breakline(
            vertices=(BreaklineVertex(0, 0, 100), BreaklineVertex(10, 0, 100)),
            breakline_type=BreaklineType.WALL,
            right_elevations=(100,),   # 개수 불일치
        )


def test_breakline_set():
    bl1 = Breakline.from_coords([(0, 0, 100), (10, 0, 100)], name="능선")
    bl2 = Breakline.from_coords([(0, 10, 90), (10, 10, 90)], name="계곡")
    bset = BreaklineSet(breaklines=(bl1, bl2))
    assert len(bset) == 2
    assert math.isclose(bset.total_length(), 20.0)


