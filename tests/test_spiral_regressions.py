import pytest

from myalignment.enum.spiraltype import SpiralType
from myalignment.geometry.spiral_geometry import SpiralGeometry, SpiralParams
from myalignment.utils import CurveDirection


@pytest.mark.parametrize("kind", [
    SpiralType.Clothoid, SpiralType.JapaneseCubic, SpiralType.CubicParabola, SpiralType.SineHalfWave,
])
def test_spiral_left_and_right_positions_and_tangents_are_mirrored(kind):
    params = SpiralParams(radius=200, length=40, spiral_type=kind)
    left = SpiralGeometry(params=params, direction=CurveDirection.LEFT)
    right = SpiralGeometry(params=params, direction=CurveDirection.RIGHT)
    left_point, right_point = left.point_at(20), right.point_at(20)
    assert left_point.x == pytest.approx(right_point.x)
    assert left_point.y > 0
    assert left_point.y == pytest.approx(-right_point.y)
    assert left.tangent_at(20) == pytest.approx(-right.tangent_at(20))


def test_spiral_projection_recovers_rotated_centerline_station():
    spiral = SpiralGeometry(
        start_azimuth=.7, params=SpiralParams(radius=200, length=40, spiral_type=SpiralType.Clothoid),
        direction=CurveDirection.LEFT,
    )
    point = spiral.point_at(20)
    result = spiral.project_at(point)
    assert result.station == pytest.approx(20)
    assert result.distance == pytest.approx(0, abs=1e-9)
    assert result.point.distance_to(point) == pytest.approx(0, abs=1e-9)
    assert result.tangent == pytest.approx(spiral.tangent_at(20))
