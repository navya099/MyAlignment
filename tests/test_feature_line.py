# tests/featureline/test_feature_line.py
import math
import pytest
from myalignment.featureline.feature_line import FeatureLine
from myalignment.featureline.builder import FeatureLineBuilder
from myalignment.featureline.vertex import FeatureLinePointType


def test_length_2d_3d():
    fl = (
        FeatureLineBuilder("테스트")
        .add_coords([(0, 0, 100), (10, 0, 100), (10, 10, 110)])
        .build()
    )
    assert math.isclose(fl.length_2d, 20.0)
    expected_3d = 10.0 + math.sqrt(100 + 100)
    assert math.isclose(fl.length_3d, expected_3d, abs_tol=1e-6)


def test_grades():
    fl = (
        FeatureLineBuilder()
        .add_coords([(0, 0, 100), (10, 0, 105)])   # +5%
        .build()
    )
    assert math.isclose(fl.max_grade, 0.5)
    assert math.isclose(fl.min_grade, 0.5)


def test_points_by_type():
    fl = (
        FeatureLineBuilder()
        .add_pi_point(0, 0, 100)
        .add_elevation_point(5, 0, 102)
        .add_pi_point(10, 0, 105)
        .build()
    )
    assert fl.pi_points_count == 2
    assert fl.elevation_points_count == 1
    assert fl.points_count == 3


def test_grade_in_out():
    fl = (
        FeatureLineBuilder()
        .add_coords([(0, 0, 100), (10, 0, 105), (20, 0, 103)])
        .build()
    )
    # 두 번째 점 진입: (105-100)/10 = 0.5
    assert math.isclose(fl.grade_in_at_point(1), 0.5)
    # 두 번째 점 진출: (103-105)/10 = -0.2
    assert math.isclose(fl.grade_out_at_point(1), -0.2)


def test_elevation_at_xy():
    fl = (
        FeatureLineBuilder()
        .add_coords([(0, 0, 100), (10, 0, 110)])
        .build()
    )
    assert math.isclose(fl.elevation_at_xy(5, 0), 105.0)
    assert fl.elevation_at_xy(5, 1) is None


def test_assign_elevations_from_surface():
    class MockSurface:
        def elevation_at(self, x, y):
            return 100 + x

    fl = (
        FeatureLineBuilder()
        .add_coords([(0, 0, 0), (10, 0, 0)])
        .build()
    )
    updated = fl.assign_elevations_from_surface(MockSurface())
    assert math.isclose(updated.vertices[0].z, 100.0)
    assert math.isclose(updated.vertices[1].z, 110.0)
    # 원본 불변
    assert math.isclose(fl.vertices[0].z, 0.0)


def test_to_breakline():
    fl = (
        FeatureLineBuilder()
        .add_coords([(0, 0, 100), (10, 0, 110)])
        .build()
    )
    bl = fl.to_breakline()
    assert bl.name == fl.name
    assert len(bl.vertices) == 2


def test_reversed():
    fl = (
        FeatureLineBuilder()
        .add_coords([(0, 0, 100), (10, 0, 110)])
        .build()
    )
    r = fl.reversed()
    assert math.isclose(r.vertices[0].z, 110.0)
    assert math.isclose(r.vertices[1].z, 100.0)
