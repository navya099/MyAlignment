"""Grading과 통합 테스트."""
from cadgeom import Point2d

from myalignment.surface.tin_surface import TinSurface
from myalignment.grading.criteria_surface import SlopeToSurface
from myalignment.grading.criteria import Slope, SlopeFormat, ProjectionType
from myalignment.grading.target_context import TargetContext
from myalignment.grading.footprint import Footprint, FootprintVertex
from myalignment.grading.grading import Grading
import math


def test_slope_to_surface():
    """Surface Target을 이용한 사면 계산."""
    surface = TinSurface.from_points([
        (-100, -100, 95),
        (200, -100, 95),
        (200, 200, 95),
        (-100, 200, 95),
    ])
    ctx = TargetContext(surface=surface)

    criteria = SlopeToSurface(
        slope=Slope(value=2.0, format=SlopeFormat.RATIO),
        projection=ProjectionType.OUTSIDE,
    )

    result = criteria.compute_daylight(
        footprint_point=Point2d(0, 0),
        footprint_elevation=100.0,
        direction=math.pi,
        target_context=ctx,
    )

    assert result is not None
    assert math.isclose(result.distance, 10.0, abs_tol=0.1)
    assert math.isclose(result.elevation, 95.0, abs_tol=0.1)