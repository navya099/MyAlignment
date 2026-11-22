import math

from cadgeom import Point2d
import pytest

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.enitity.arc_entity import ArcEntity
from myalignment.enitity.spiral_entity import SpiralEntity
from myalignment.enum.spiraltype import SpiralType
from myalignment.exception.alignment_error import InvalidGeometryError
from myalignment.utils import CurveDirection


@pytest.mark.parametrize("direction", [1, -1])
@pytest.mark.parametrize("entry_exit", [(0, 0), (10, 16), (0, 16), (10, 0)])
def test_pi_alignment_preserves_endpoints_tangency_and_reversed_path(direction, entry_exit):
    entry, exit = entry_exit
    alignment = (
        AlignmentBuilder().with_pi_coords([(0, 0), (100, 0), (100, direction * 100)])
        .with_start_station(1025).with_radii([None, 30, None])
        .with_spiral_lengths([0, entry, 0], [0, exit, 0]).build()
    )
    assert alignment.entities.start_coord == Point2d(0, 0)
    assert alignment.entities.end_coord.distance_to(Point2d(100, direction * 100)) < 1e-10
    for first, second in zip(alignment.entities, alignment.entities[1:]):
        assert first.end_coord.distance_to(second.start_coord) < 1e-10
        assert math.remainder(first.end_azimuth - second.start_azimuth, math.tau) == pytest.approx(0, abs=1e-10)
    if not entry and not exit:
        arc = alignment.entities[1]
        assert arc.start_coord.distance_to(Point2d(70, 0)) < 1e-10
        assert arc.end_coord.distance_to(Point2d(100, direction * 30)) < 1e-10
        assert alignment.length == pytest.approx(140 + 15 * math.pi)
    reversed_alignment = alignment.reversed_alignment()
    for i in range(21):
        offset = i * alignment.length / 20
        original = alignment.point_at(alignment.start_station + offset)
        reversed_point = reversed_alignment.point_at(reversed_alignment.end_station - offset)
        assert original.distance_to(reversed_point) < 1e-9


@pytest.mark.parametrize("direction", [CurveDirection.LEFT, CurveDirection.RIGHT])
@pytest.mark.parametrize("offset", [-2, 0, 2])
def test_arc_and_spiral_station_offset_round_trip(direction, offset):
    start = Point2d(220000, 410000)
    arc = ArcEntity.create(start, .7, 40, .8, direction, 100)
    spiral = SpiralEntity.create(start, .7, 200, 40, SpiralType.Clothoid, direction, 100)
    for entity in (arc, spiral, spiral.reversed()):
        station = 117.31
        point = entity.point_at(station, offset)
        projected = entity.project(point)
        assert projected.station == pytest.approx(station, abs=2e-7)
        assert projected.offset == pytest.approx(offset, abs=1e-9)
        assert projected.distance == pytest.approx(abs(offset), abs=1e-9)


def test_adjacent_pi_curves_reject_overlapping_tangent_requirements():
    builder = (
        AlignmentBuilder().with_pi_coords([(0, 0), (100, 0), (100, 50), (200, 50)])
        .with_radii([None, 30, 30, None])
    )
    with pytest.raises(InvalidGeometryError, match="중첩"):
        builder.build()
