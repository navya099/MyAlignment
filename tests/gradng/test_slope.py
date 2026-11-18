# tests/grading/test_slope.py
import math
import pytest
from myalignment.grading.criteria import Slope, SlopeFormat
from myalignment.grading.footprint import Footprint, FootprintVertex


def test_slope_ratio_to_percent():
    s = Slope(value=2.0, format=SlopeFormat.RATIO)   # 1:2
    assert math.isclose(s.percent, 50.0)


def test_slope_percent_to_ratio():
    s = Slope(value=50.0, format=SlopeFormat.PERCENT)   # 50%
    assert math.isclose(s.ratio, 2.0)


def test_slope_degree_to_ratio():
    s = Slope(value=45.0, format=SlopeFormat.DEGREE)   # 45°
    assert math.isclose(s.ratio, 1.0, abs_tol=1e-6)


def test_slope_invalid():
    with pytest.raises(ValueError):
        Slope(value=0.0, format=SlopeFormat.RATIO)








# tests/grading/test_grading.py
from myalignment.grading.grading import Grading
from myalignment.grading.criteria_distance import SlopeToDistance
from myalignment.grading.criteria import Slope, SlopeFormat
from myalignment.grading.target_context import TargetContext


def test_grading_daylight_lines():
    fp = Footprint(
        vertices=(
            FootprintVertex(0, 0, 100),
            FootprintVertex(100, 0, 100),
        ),
        is_closed=False,
    )
    criteria = SlopeToDistance(
        slope=Slope(value=2.0, format=SlopeFormat.RATIO),
        target_distance=20.0,
    )
    g = Grading(
        name="사면1",
        footprint=fp,
        criteria=criteria,
        target_context=TargetContext(),
    )

    results = g.compute_daylight_lines()
    assert len(results) == 2
    for r in results:
        assert math.isclose(r.distance, 20.0)


