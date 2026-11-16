from cadgeom import Point2d
import math
from myalignment.enitity.arc_entity import ArcEntity
from myalignment.utils import CurveDirection


def test_arc_create_from_bc_ec():
    # BC=(0,0), EC=(100,0), R=100, LEFT → 반원 (delta=π)
    e = ArcEntity.create_from_bc_ec(
        bc=Point2d(0, 0),
        ec=Point2d(100, 100),
        radius=100,
        direction=CurveDirection.LEFT,
    )
    assert e.length > 0


def test_arc_reversed_preserves_length():
    """reversed 시 length 보존."""
    e = ArcEntity.create(
        start_coord=Point2d(0, 0),
        start_azimuth=0.0,
        radius=100,
        delta=math.pi / 3,
        direction=CurveDirection.LEFT,
    )
    e2 = e.reversed()
    assert math.isclose(e2.length, e.length)
    assert math.isclose(e2.geometry.delta, e.geometry.delta)