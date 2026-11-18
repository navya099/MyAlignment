# tests/surface/test_boundary.py
import math
import pytest
from myalignment.surface.boundary_vertex import BoundaryVertex
from myalignment.surface.boundary import Boundary
from myalignment.surface.boundary_type import BoundaryType
from myalignment.surface.boundary_set import BoundarySet


def test_boundary_area_rectangle():
    b = Boundary.rectangle(0, 0, 10, 10)
    assert math.isclose(b.area, 100.0)
    assert math.isclose(b.perimeter, 40.0)


def test_boundary_contains_point():
    b = Boundary.rectangle(0, 0, 10, 10)
    assert b.contains_point(5, 5)
    assert b.contains_point(0, 5)    # 경계 위
    assert b.contains_point(10, 10)  # 꼭짓점
    assert not b.contains_point(-1, 5)
    assert not b.contains_point(11, 11)


def test_boundary_circle():
    b = Boundary.circle(0, 0, 10, n_segments=64)
    assert b.contains_point(0, 0)
    assert b.contains_point(9, 0)
    assert not b.contains_point(11, 0)


def test_boundary_ccw():
    b = Boundary.rectangle(0, 0, 10, 10)   # 반시계
    assert b.is_counterclockwise


def test_boundary_set_outer_only():
    outer = Boundary.rectangle(0, 0, 10, 10, boundary_type=BoundaryType.OUTER)
    bset = BoundarySet(boundaries=(outer,))
    assert bset.outer is outer
    assert bset.contains_point(5, 5)
    assert not bset.contains_point(-1, -1)


def test_boundary_set_with_hide():
    outer = Boundary.rectangle(0, 0, 10, 10, boundary_type=BoundaryType.OUTER)
    hole = Boundary.rectangle(3, 3, 7, 7, boundary_type=BoundaryType.HIDE)
    bset = BoundarySet(boundaries=(outer, hole))

    assert bset.contains_point(1, 1)
    assert not bset.contains_point(5, 5)   # 구멍 내부


def test_boundary_set_effective_area():
    outer = Boundary.rectangle(0, 0, 10, 10, boundary_type=BoundaryType.OUTER)
    hole = Boundary.rectangle(3, 3, 7, 7, boundary_type=BoundaryType.HIDE)
    bset = BoundarySet(boundaries=(outer, hole))
    assert math.isclose(bset.effective_area, 100.0 - 16.0)


def test_boundary_set_duplicate_outer():
    outer1 = Boundary.rectangle(0, 0, 10, 10, name="O1", boundary_type=BoundaryType.OUTER)
    outer2 = Boundary.rectangle(0, 0, 10, 10, name="O2", boundary_type=BoundaryType.OUTER)
    with pytest.raises(ValueError):
        BoundarySet(boundaries=(outer1, outer2))


