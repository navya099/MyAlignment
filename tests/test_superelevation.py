# tests/superelevation/test_superelevation.py
import math
import pytest

from myalignment.superelevation.collection import SuperelevationCollection
from myalignment.superelevation.critical_station import SuperelevationCriticalStation, CrossSegmentType, \
    TransitionRegionType
from myalignment.superelevation.curve import SuperelevationCurve, PivotMethod


def test_critical_station():
    cs = SuperelevationCriticalStation(
        station=100.0,
        region_type=TransitionRegionType.FULL_SUPERELEVATION,
    )
    cs = cs.with_slope(CrossSegmentType.LEFT_OUT_LANE, 0.04)
    assert cs.get_slope(CrossSegmentType.LEFT_OUT_LANE) == 0.04
    assert cs.get_slope(CrossSegmentType.RIGHT_OUT_LANE) is None


def test_superelevation_curve():
    cs1 = SuperelevationCriticalStation(station=0.0, region_type=TransitionRegionType.NORMAL)
    cs2 = SuperelevationCriticalStation(station=50.0, region_type=TransitionRegionType.FULL_SUPERELEVATION)
    curve = SuperelevationCurve(
        name="곡선1",
        start_station=0.0,
        end_station=100.0,
        pivot_method=PivotMethod.CENTER_BASELINE,
        critical_stations=(cs1, cs2),
    )
    assert curve.length == 100.0
    assert curve.critical_station_at(30.0).station == 50.0


def test_collection():
    cs = SuperelevationCriticalStation(station=0.0)
    curve = SuperelevationCurve(name="C1", start_station=0.0, end_station=100.0, critical_stations=(cs,))
    col = SuperelevationCollection(curves=(curve,))
    assert len(col) == 1
    assert col.curve_at_station(50.0) is curve
    assert col.curve_at_station(150.0) is None
