# tests/core/test_station_offset.py
import math
import pytest

from myalignment.core.station_offset import StationOffsetPoint


def test_immutable():
    p = StationOffsetPoint(100.0, 5.0)
    with pytest.raises(Exception):   # FrozenInstanceError
        p.station = 200.0


def test_validation():
    with pytest.raises(ValueError):
        StationOffsetPoint(float("nan"), 0.0)
    with pytest.raises(ValueError):
        StationOffsetPoint(0.0, float("inf"))


def test_distance():
    a = StationOffsetPoint(0.0, 0.0)
    b = StationOffsetPoint(30.0, 40.0)
    assert math.isclose(a.distance_to(b), 50.0)


def test_shifted():
    a = StationOffsetPoint(100.0, 5.0)
    b = a.shifted(10.0, -2.0)
    assert b.station == 110.0
    assert b.offset == 3.0


def test_signed_offset():
    assert StationOffsetPoint(0, -5).signed_offset() == -5
    assert StationOffsetPoint(0, 5).abs_offset() == 5