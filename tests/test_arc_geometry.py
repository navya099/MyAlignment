import pytest

from myalignment.geometry.arc_geometry import ArcGeometry
import math

from myalignment.utils import CurveDirection


def test_arc_length():
    g = ArcGeometry(_radius=100.0, _delta=math.pi/2, direction=CurveDirection.LEFT)
    assert math.isclose(g.length, 100.0 * math.pi/2)


def test_arc_reversed_preserves_delta():
    """앞서 curvegeometry.reversed() 버그 회귀 방지."""
    g = ArcGeometry(_radius=100.0, _delta=math.pi/3, direction=CurveDirection.LEFT)
    g2 = g.reversed()
    assert math.isclose(g2.delta, g.delta)   # ← 핵심: delta 보존
    assert g2.direction == CurveDirection.RIGHT


def test_arc_invalid_direction():
    with pytest.raises(ValueError):
        ArcGeometry(_radius=100.0, _delta=0.5, direction=CurveDirection.NULL)