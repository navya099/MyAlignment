import math
import pytest
from cadgeom import Point2d

from myalignment.enitity.line_entity import LineEntity


def test_create_from_coords():
    e = LineEntity.create(
        start_coord=Point2d(0, 0),
        end_coord=Point2d(100, 0),
        start_station=0.0,
    )
    assert math.isclose(e.length, 100.0)
    assert math.isclose(e.end_station, 100.0)
    assert e.end_coord.distance_to(Point2d(100, 0)) < 1e-6


def test_point_at():
    e = LineEntity.create(Point2d(0, 0), Point2d(100, 0), start_station=10.0)
    p = e.point_at(60.0)   # station=60 → 로컬 s=50
    assert math.isclose(p.x, 50.0)
    assert math.isclose(p.y, 0.0)


def test_project():
    e = LineEntity.create(Point2d(0, 0), Point2d(100, 0), start_station=10.0)
    pr = e.project(Point2d(60.0, 5.0))  # x=60.0 -> 로컬 s=60.0
    assert math.isclose(pr.station, 70.0)   # 10 + 60 = 70.0
    assert math.isclose(pr.offset, -5.0)    # y=+5 → 좌(-)
    assert math.isclose(pr.distance, 5.0)


def test_reversed():
    e = LineEntity.create(Point2d(0, 0), Point2d(100, 0))
    e2 = e.reversed()
    assert e2 is not e
    assert e2.start_coord.distance_to(Point2d(100, 0)) < 1e-6
    assert math.isclose(e2.start_azimuth, math.pi)
    # 원본 불변
    assert e.start_coord.distance_to(Point2d(0, 0)) < 1e-6


def test_offset_by():
    e = LineEntity.create(Point2d(0, 0), Point2d(100, 0))
    e2 = e.offset_by(-5.0)   # 좌측 5m
    assert e2.start_coord.distance_to(Point2d(0, 5)) < 1e-6
    assert e2.end_coord.distance_to(Point2d(100, 5)) < 1e-6