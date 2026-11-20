
import math

import pytest

from cadgeom import Point2d

from myalignment.turnout.turnout import Turnout
from myalignment.turnout.type import (
    TurnoutSide,
    TurnoutType,
)
from myalignment.turnout.scissors_crossover import (
    ScissorsCrossover,
)


class MockAlignment:
    def __init__(self, name, y):
        self.name = name
        self.y = y

    def point_at(self, station):
        return Point2d(station, self.y)

    def tangent_at(self, station):
        return 0.0


def make_scissors(distance=5.0, delta=None, side1=None, side2=None):
    tt = TurnoutType(
        name="1/12",
        frog_number=12,
        lead_length=30,
        radius=300,
    )

    theta = tt.frog_angle
    if delta is None:
        delta = (
            2 * tt.run
            + (distance - 2 * tt.rise)
            / math.tan(theta)
        )

    if side1 is None:
        side1 = TurnoutSide.LEFT
    if side2 is None:
        side2 = TurnoutSide.RIGHT

    sta1 = sta3 = 100.0
    sta2 = sta4 = 100.0 + delta

    def turnout(n, source, sta, side):
        return Turnout(
            name=f"T{n}",
            turnout_type=tt,
            source_alignment_name=source,
            branch_alignment_name=f"C{n}",
            station_on_source=sta,
            side=side,
        )

    scissors = ScissorsCrossover(
        name="SC1",
        turnout1=turnout(1, "A1", sta1, side1),
        turnout2=turnout(2, "A1", sta2, side1),
        turnout3=turnout(3, "A2", sta3, side2),
        turnout4=turnout(4, "A2", sta4, side2),
        source_alignment1_name="A1",
        source_alignment2_name="A2",
    )

    return scissors, MockAlignment("A1", 0), MockAlignment("A2", distance)


def test_scissors_valid_geometry():
    scissors, a1, a2 = make_scissors()

    geom = scissors.compute_geometry(a1, a2)

    assert geom.is_valid, geom.error_message
    assert geom.diamond_center is not None
    assert geom.diamond_center.y == pytest.approx(2.5)
    assert geom.connecting_lengths[0] > 0
    assert geom.connecting_lengths[1] > 0


def test_scissors_diamond_center():
    scissors, a1, a2 = make_scissors()

    geom = scissors.compute_geometry(a1, a2)

    assert geom.is_valid, geom.error_message

    center_x = (
        scissors.turnout1.station_on_source
        + scissors.turnout2.station_on_source
    ) / 2

    assert geom.diamond_center.x == pytest.approx(
        center_x, abs=1e-3
    )


def test_scissors_station_mismatch():
    scissors, a1, a2 = make_scissors(
        delta=120.0
    )

    geom = scissors.compute_geometry(a1, a2)

    assert not geom.is_valid
    assert "접선 불연속" in geom.error_message


def test_scissors_wrong_direction():
    scissors, a1, a2 = make_scissors(
        side1=TurnoutSide.RIGHT
    )

    geom = scissors.compute_geometry(a1, a2)

    assert not geom.is_valid
    assert "분기 방향" in geom.error_message


def test_scissors_distance_insufficient():
    scissors, a1, a2 = make_scissors(
        distance=1.0
    )

    geom = scissors.compute_geometry(a1, a2)

    assert not geom.is_valid


def test_scissors_with_geometry():
    scissors, a1, a2 = make_scissors()
    geom = scissors.compute_geometry(a1, a2)

    updated = scissors.with_geometry(geom)

    assert updated.is_valid
    assert updated.geometry is geom
    assert updated.total_connecting_length > 0
