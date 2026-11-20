
import pytest

from cadgeom import Point2d

from myalignment.turnout.scissors_type import (
    ScissorsCrossoverType,
)
from myalignment.turnout.scissors_geometry import (
    ScissorsCrossoverGeometry,
)


def test_scissors_type():
    assert len(ScissorsCrossoverType) == 3
    assert ScissorsCrossoverType.STANDARD.value == "standard"
    assert ScissorsCrossoverType.SYMMETRIC.value == "symmetric"
    assert ScissorsCrossoverType.ASYMMETRIC.value == "asymmetric"


def test_scissors_geometry():
    geom = ScissorsCrossoverGeometry(
        turnout1_station=100.0,
        turnout2_station=200.0,
        turnout3_station=100.0,
        turnout4_station=200.0,
        diamond_center=Point2d(150.0, 100.0),
        connecting_lengths=(10.0, 20.0, 30.0, 40.0),
    )

    assert geom.is_valid
    assert geom.total_connecting_length == 100.0
    assert geom.diamond_center.x == 150.0
    assert geom.diamond_center.y == 100.0


def test_scissors_invalid_without_message():
    with pytest.raises(ValueError):
        ScissorsCrossoverGeometry(is_valid=False)


def test_scissors_invalid_with_message():
    geom = ScissorsCrossoverGeometry(
        is_valid=False,
        error_message="기하 계산 실패",
    )

    assert not geom.is_valid
    assert geom.error_message == "기하 계산 실패"


def test_scissors_invalid_connection_length():
    with pytest.raises(ValueError):
        ScissorsCrossoverGeometry(
            connecting_lengths=(10.0, -1.0, 20.0, 30.0)
        )
