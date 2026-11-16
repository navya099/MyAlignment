import pytest
from cadgeom import Point2d
import math

from myalignment.enitity.entity_collection import AlignmentEntityCollection
from myalignment.enitity.line_entity import LineEntity


def test_continuity_validation():
    e1 = LineEntity.create(Point2d(0, 0), Point2d(100, 0), start_station=0.0)
    e2 = LineEntity.create(Point2d(100, 0), Point2d(200, 0), start_station=100.0)
    AlignmentEntityCollection(entities=(e1, e2))   # OK


def test_discontinuity_raises():
    e1 = LineEntity.create(Point2d(0, 0), Point2d(100, 0), start_station=0.0)
    e2 = LineEntity.create(Point2d(150, 0), Point2d(250, 0), start_station=100.0)
    with pytest.raises(ValueError):
        AlignmentEntityCollection(entities=(e1, e2))


def test_project_across_entities():
    e1 = LineEntity.create(Point2d(0, 0), Point2d(100, 0), start_station=0.0)
    e2 = LineEntity.create(Point2d(100, 0), Point2d(200, 0), start_station=100.0)
    col = AlignmentEntityCollection(entities=(e1, e2))

    pr = col.project(Point2d(150.0, 3.0))
    assert math.isclose(pr.station, 150.0)
    assert math.isclose(pr.distance, 3.0)