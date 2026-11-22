import math

from cadgeom import Point2d
import pytest

from myalignment.alignment.alignment import Alignment
from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.alignment.intersection import intersect_ray_with_spiral_entity
from myalignment.enitity.arc_entity import ArcEntity
from myalignment.enitity.entity_collection import AlignmentEntityCollection
from myalignment.enitity.spiral_entity import SpiralEntity
from myalignment.enum.spiraltype import SpiralType
from myalignment.utils.curvedirection import CurveDirection


def _line(start, end, station=0):
    return AlignmentBuilder().with_pi_coords([start, end]).with_start_station(station).build()


def _single(entity):
    return Alignment(entities=AlignmentEntityCollection((entity,)))


def _stations(a, b):
    points = a.intersection_with(b)
    assert all(point.offset == 0 for point in points)
    return [point.station for point in points]


def test_finite_lines_cross_between_sample_stations_in_both_orders():
    horizontal = _line((0, 0), (100, 0), station=1000)
    vertical = _line((73, -13), (73, 7), station=20)
    assert _stations(horizontal, vertical) == pytest.approx([1073])
    assert _stations(vertical, horizontal) == pytest.approx([33])


def test_collinear_intersection_returns_only_finite_overlap_boundaries():
    horizontal = _line((0, 0), (100, 0))
    assert _stations(horizontal, _line((120, 0), (150, 0))) == []
    assert _stations(horizontal, _line((120, 0), (73, 0))) == pytest.approx([73, 100])
    assert _stations(horizontal, _line((100, 0), (150, 0))) == pytest.approx([100])
    assert _stations(horizontal, _line((73, 1), (73, 7))) == []
    assert _stations(horizontal, _line((20, 0), (50, 0))) == pytest.approx([20, 50])


def test_element_join_intersection_is_returned_once():
    axis = AlignmentBuilder().with_pi_coords([(0, 0), (30, 0), (60, 30)]).build()
    passing = _line((30, -5), (30, 5))
    assert _stations(axis, passing) == pytest.approx([30])


@pytest.mark.parametrize("reversed_direction", [False, True])
def test_spiral_ray_tangent_and_endpoints(reversed_direction):
    base = SpiralEntity.create(
        Point2d(220000, 410000), 0.4, 60, 20, SpiralType.Clothoid, CurveDirection.LEFT, 100,
    )
    curve = base.reversed() if reversed_direction else base
    for station in (107.37, curve.end_station):
        p = curve.point_at(station)
        angle = curve.tangent_at(station)
        direction = (math.cos(angle), math.sin(angle))
        origin = Point2d(p.x - 5 * direction[0], p.y - 5 * direction[1])
        hits = intersect_ray_with_spiral_entity(origin, angle, curve)
        assert [s for _, s in hits] == pytest.approx([station], abs=1e-7)

        line = _line((origin.x, origin.y), (p.x + 2 * direction[0], p.y + 2 * direction[1]))
        assert _stations(line, _single(curve)) == pytest.approx([5], abs=1e-7)

    point = curve.point_at(107.37)
    angle = curve.tangent_at(107.37)
    delta = -1e-4 if reversed_direction else 1e-4
    # 곡선은 접선의 같은 쪽에 있으므로 반대편으로 옮긴 직선과 만나지 않는다.
    origin = Point2d(point.x + delta * math.sin(angle), point.y - delta * math.cos(angle))
    assert not intersect_ray_with_spiral_entity(origin, angle, curve)


def _arc_through(contact, azimuth, radius, angle_before=0.3, delta=0.6):
    cx = contact.x - radius * math.sin(azimuth)
    cy = contact.y + radius * math.cos(azimuth)
    start_azimuth = azimuth - angle_before
    start = Point2d(cx + radius * math.sin(start_azimuth), cy - radius * math.cos(start_azimuth))
    return ArcEntity.create(start, start_azimuth, radius, delta, CurveDirection.LEFT)


def test_circle_tangency_and_arc_range_are_respected():
    first = _arc_through(Point2d(0, 0), 0, 50)
    second = _arc_through(Point2d(0, 0), math.pi, 20)
    assert _stations(_single(first), _single(second)) == pytest.approx([15])
    assert _stations(_single(second), _single(first)) == pytest.approx([6])
    assert _stations(_single(first), _single(first.reversed())) == pytest.approx([0, 30])
    assert _stations(_single(first), _line((-10, 100), (10, 100))) == []


def test_spiral_and_arc_tangent_in_element_interior():
    spiral = SpiralEntity.create(
        Point2d(0, 0), 0.5, 60, 20, SpiralType.Clothoid, CurveDirection.LEFT,
    )
    station = 7.37
    arc = _arc_through(spiral.point_at(station), spiral.tangent_at(station), 20)
    assert _stations(_single(spiral), _single(arc)) == pytest.approx([station], abs=1e-7)
    assert _stations(_single(arc), _single(spiral)) == pytest.approx([6], abs=1e-7)


def test_two_spirals_cross_and_return_their_own_stations():
    a = SpiralEntity.create(Point2d(0, 0), 0, 50, 20, SpiralType.Clothoid, CurveDirection.LEFT)
    b = SpiralEntity.create(Point2d(0, 0), 1.4, 70, 25, SpiralType.Clothoid, CurveDirection.RIGHT, 25)
    sa, sb = 8.2, 41.7
    contact, local = a.point_at(sa), b.point_at(sb)
    b = b.with_start(Point2d(contact.x - local.x, contact.y - local.y), b.start_station)
    assert _stations(_single(a), _single(b)) == pytest.approx([sa], abs=1e-7)
    assert _stations(_single(b), _single(a)) == pytest.approx([sb], abs=1e-7)


def test_two_spirals_tangent_between_span_boundaries():
    a = SpiralEntity.create(Point2d(0, 0), 0, 50, 20, SpiralType.Clothoid, CurveDirection.LEFT)
    sa, sb = 8.2, 16.7
    azimuth = a.tangent_at(sa)
    local_curve = SpiralEntity.create(Point2d(0, 0), 0, 70, 25, SpiralType.Clothoid, CurveDirection.RIGHT)
    start_azimuth = azimuth - local_curve.tangent_at(sb)
    b = SpiralEntity.create(Point2d(0, 0), start_azimuth, 70, 25, SpiralType.Clothoid, CurveDirection.RIGHT)
    contact, local = a.point_at(sa), b.point_at(sb)
    b = b.with_start(Point2d(contact.x - local.x, contact.y - local.y), b.start_station)
    assert _stations(_single(a), _single(b)) == pytest.approx([sa], abs=1e-7)
    assert _stations(_single(b), _single(a)) == pytest.approx([sb], abs=1e-7)


def test_distance_to_alignment_when_normal_overlaps_target_line():
    axis = _line((0, 0), (100, 0))
    assert axis.distance_to_alignment(73, _line((73, 5), (73, 10))) == pytest.approx((5, 0))
    assert axis.distance_to_alignment(73, _line((73, -2), (73, 3))) == pytest.approx((0, 2))


def test_line_arc_secant_returns_only_hits_on_the_finite_line():
    radius = 10
    arc = ArcEntity.create(Point2d(-radius, radius), -math.pi / 2, radius, math.pi, CurveDirection.LEFT)
    whole = _line((-12, 5), (12, 5))
    positive_only = _line((0, 5), (12, 5))
    x = math.sqrt(75)
    assert _stations(whole, _single(arc)) == pytest.approx([12 - x, 12 + x])
    assert _stations(positive_only, _single(arc)) == pytest.approx([x])
    assert _stations(_single(arc), positive_only) == pytest.approx([5 * math.pi * radius / 6])
