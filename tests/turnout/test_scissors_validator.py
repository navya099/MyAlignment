
import math

import pytest

from cadgeom import Point2d

from myalignment.turnout.scissors_validator import (
    ScissorsCrossoverValidator as Validator,
)


class MockAlignment:
    def __init__(
        self,
        y_offset=0.0,
        x_start=0.0,
        azimuth=0.0,
    ):
        self.y_offset = y_offset
        self.x_start = x_start
        self.azimuth = azimuth

    def point_at(self, station):
        return Point2d(
            self.x_start + station,
            self.y_offset,
        )

    def tangent_at(self, station):
        return self.azimuth


def test_valid_scissors():
    a1 = MockAlignment(y_offset=0)
    a2 = MockAlignment(y_offset=5)

    valid, error = Validator.validate(
        a1, a2,
        (30, 30, 30, 30),
        (100, 200, 100, 200),
    )

    assert valid, error


def test_different_station_origins():
    a1 = MockAlignment(y_offset=0)
    a2 = MockAlignment(
        y_offset=5,
        x_start=-1000,
    )

    valid, error = Validator.validate(
        a1, a2,
        (30, 30, 30, 30),
        (100, 200, 1100, 1200),
    )

    assert valid, error


def test_station_order_error():
    a1 = MockAlignment(y_offset=0)
    a2 = MockAlignment(y_offset=5)

    valid, error = Validator.validate(
        a1, a2,
        (30, 30, 30, 30),
        (200, 100, 100, 200),
    )

    assert not valid
    assert "순서" in error


def test_invalid_lead_length():
    a1 = MockAlignment(y_offset=0)
    a2 = MockAlignment(y_offset=5)

    valid, error = Validator.validate(
        a1, a2,
        (30, -1, 30, 30),
        (100, 200, 100, 200),
    )

    assert not valid
    assert "리드 길이" in error


def test_parallel_error():
    a1 = MockAlignment(y_offset=0)
    a2 = MockAlignment(
        y_offset=5,
        azimuth=math.radians(2),
    )

    valid, error = Validator.validate(
        a1, a2,
        (30, 30, 30, 30),
        (100, 200, 100, 200),
    )

    assert not valid
    assert "평행" in error


def test_diamond_intersection():
    p1 = Point2d(0, 0)
    p2 = Point2d(10, 10)
    p3 = Point2d(0, 10)
    p4 = Point2d(10, 0)

    diamond = Validator._segments_intersection_point(
        p1, p2, p3, p4
    )

    assert diamond is not None
    assert diamond.x == pytest.approx(5.0)
    assert diamond.y == pytest.approx(5.0)


def test_no_intersection():
    p1 = Point2d(0, 0)
    p2 = Point2d(10, 0)
    p3 = Point2d(0, 5)
    p4 = Point2d(10, 5)

    assert Validator._segments_intersection_point(
        p1, p2, p3, p4
    ) is None


def test_endpoint_touch_not_intersection():
    p1 = Point2d(0, 0)
    p2 = Point2d(10, 10)
    p3 = Point2d(10, 10)
    p4 = Point2d(20, 0)

    assert Validator._segments_intersection_point(
        p1, p2, p3, p4
    ) is None


def test_nan_station_rejected():
    a1 = MockAlignment(y_offset=0)
    a2 = MockAlignment(y_offset=5)

    valid, error = Validator.validate(
        a1, a2,
        (30, 30, 30, 30),
        (float("nan"), 200, 100, 200),
    )

    assert not valid
    assert "유한" in error
