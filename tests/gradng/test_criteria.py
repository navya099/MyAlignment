# tests/grading/test_criteria.py
from cadgeom import Point2d

from myalignment.grading.criteria_elevation import SlopeToElevation
from myalignment.grading.criteria_distance import SlopeToDistance
from myalignment.grading.criteria import ProjectionType, SlopeFormat, Slope
from myalignment.grading.target_context import TargetContext
import math


def test_slope_to_elevation():
    """표고 10m 하강, 1:2 경사 → 거리 20m."""
    criteria = SlopeToElevation(
        slope=Slope(value=2.0, format=SlopeFormat.RATIO),
        target_elevation=90.0,   # 100 → 90
    )
    result = criteria.compute_daylight(
        footprint_point=Point2d(0, 0),
        footprint_elevation=100.0,
        direction=0.0,   # +x 방향
        target_context=TargetContext(),
    )

    assert math.isclose(result.distance, 20.0)
    assert math.isclose(result.elevation, 90.0)
    assert math.isclose(result.point.x, 20.0)


def test_slope_to_distance():
    """거리 30m, 1:2 경사 → 표고 -15m."""
    criteria = SlopeToDistance(
        slope=Slope(value=2.0, format=SlopeFormat.RATIO),
        target_distance=30.0,
    )
    result = criteria.compute_daylight(
        footprint_point=Point2d(0, 0),
        footprint_elevation=100.0,
        direction=math.pi / 2,   # +y 방향
        target_context=TargetContext(),
    )
    assert math.isclose(result.distance, 30.0)
    assert math.isclose(result.elevation, 85.0)
    assert math.isclose(result.point.y, 30.0)