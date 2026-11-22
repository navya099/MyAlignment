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


@pytest.mark.parametrize("turn", [1, -1])
@pytest.mark.parametrize("spirals", [(0, 0), (10, 16)])
@pytest.mark.parametrize("offset", [-5, 5])
def test_curved_alignment_offset_matches_original_normal(turn, spirals, offset):
    entry, exit_ = spirals
    axis = (
        AlignmentBuilder().with_pi_coords([(0, 0), (100, 0), (100, turn * 100)])
        .with_start_station(1000).with_radii([None, 30, None])
        .with_spiral_lengths([0, entry, 0], [0, exit_, 0]).build()
    )
    shifted = axis.offset_alignment(offset)
    assert shifted.start_station == axis.start_station
    assert shifted.length == pytest.approx(axis.length + offset * turn * math.pi / 2)
    for original, parallel in zip(axis.entities, shifted.entities):
        if isinstance(original, ArcEntity):
            assert parallel.geometry.radius == pytest.approx(30 + turn * offset)
        for fraction in (0, 0.13, 0.5, 0.87, 1):
            source = original.start_station + fraction * original.length
            point = original.point_at(source, offset)
            assert parallel.project(point).distance < 1e-8

    reversed_shifted = axis.reversed_alignment().offset_alignment(-offset)
    for i in range(21):
        distance = i * shifted.length / 20
        a = shifted.point_at(shifted.start_station + distance)
        b = reversed_shifted.point_at(reversed_shifted.end_station - distance)
        assert a.distance_to(b) < 1e-8


def test_polyline_offset_joins_corner_at_intersection_of_shifted_lines():
    axis = AlignmentBuilder().with_pi_coords([(0, 0), (10, 0), (10, 10)]).build()
    shifted = axis.offset_alignment(2)
    assert shifted.entities[0].end_coord == Point2d(12, -2)
    assert shifted.entities[1].start_coord == Point2d(12, -2)
    assert shifted.entities[1].start_station == pytest.approx(12)


def test_spiral_offset_carries_profile_elevation_to_parallel_point():
    from myalignment.profile.profile import ProfileBuilder

    builder = (
        AlignmentBuilder().with_pi_coords([(0, 0), (100, 0), (100, 100)])
        .with_radii([None, 30, None]).with_spiral_lengths([0, 10, 0], [0, 16, 0])
    )
    original = builder.build()
    profile = ProfileBuilder().add_tangent(0, original.end_station, 0, 100).build()
    original = builder.with_profile(profile).build()
    offset = original.offset_alignment(5)

    for i, entity in enumerate(original.entities):
        if not isinstance(entity, SpiralEntity):
            continue
        station = entity.start_station + 0.37 * entity.length
        point = entity.point_at(station, 5)
        shifted_station = offset.entities[i].project(point).station
        assert offset.profiles[0].elevation_at(shifted_station) == pytest.approx(
            profile.elevation_at(station), abs=1e-6,
        )
