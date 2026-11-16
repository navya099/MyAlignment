# tests/geometry/test_line_geometry.py
import math

from cadgeom import Point2d

from myalignment.geometry.line_geometry import LineGeometry


def test_point_at():
    g = LineGeometry(_length=100.0, start_azimuth=0.0)
    p = g.point_at(50.0)
    assert math.isclose(p.x, 50.0)
    assert math.isclose(p.y, 0.0)


def test_point_at_offset_left():
    """offset < 0 → 좌측(y+)"""
    g = LineGeometry(_length=100.0, start_azimuth=0.0)
    p = g.point_at(50.0, offset=-5.0)
    assert math.isclose(p.x, 50.0)
    assert math.isclose(p.y, +5.0)   # y축 반전


def test_project_on_line():
    g = LineGeometry(_length=100.0, start_azimuth=0.0)
    pr = g.project_at(Point2d(50.0, 5.0))
    assert math.isclose(pr.station, 50.0)
    assert math.isclose(pr.offset, -5.0)   # y=+5 → offset=-5 (좌)
    assert math.isclose(pr.distance, 5.0)
    assert pr.is_on_entity


def test_project_out_of_range():
    g = LineGeometry(_length=100.0, start_azimuth=0.0)
    pr = g.project_at(Point2d(150.0, 0.0))
    assert math.isclose(pr.station, 100.0)
    assert not pr.is_on_entity


def test_reversed_returns_new():
    g = LineGeometry(_length=100.0, start_azimuth=0.0)
    g2 = g.reversed()
    assert g2 is not g
    assert g.start_azimuth == 0.0
    assert math.isclose(g2.start_azimuth, math.pi)
    assert g2.length == g.length


# tests/geometry/test_arc_geometry.py





