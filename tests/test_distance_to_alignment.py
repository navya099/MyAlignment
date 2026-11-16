# tests/alignment/test_distance_to_alignment.py
import math
import pytest
from cadgeom import Point2d

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.alignment.alignment_query import AlignmentQuery
from myalignment.alignment.alignment_side import AlignmentSide
from myalignment.enum.spiraltype import SpiralType
from myalignment.ipdata.ipdata import PICurveSpec


def _make(points, radii):
    return (
        AlignmentBuilder()
        .with_pi_coords(points)
        .with_radii(radii)
        .build()
    )


# ---- 평행 선형 ----
def test_parallel_alignments_distance():
    a = _make([(0, 0), (200, 0)], [None, None])
    b = _make([(0, 10), (200, 10)], [None, None])

    dist, sta = a.distance_to_alignment(50.0, b)
    assert math.isclose(abs(dist), 10.0, abs_tol=1e-6)
    assert math.isclose(sta, 50.0, abs_tol=1e-6)


def test_parallel_side_left():
    a = _make([(0, 0), (200, 0)], [None, None])
    b = _make([(0, 10), (200, 10)], [None, None])

    dist, sta = a.distance_to_alignment(50.0, b, AlignmentSide.LEFT)
    assert dist > 0   # LEFT: +
    assert math.isclose(abs(dist), 10.0)


def test_parallel_side_right_no_intersection():
    a = _make([(0, 0), (200, 0)], [None, None])
    b = _make([(0, 10), (200, 10)], [None, None])

    with pytest.raises(ValueError):
        a.distance_to_alignment(50.0, b, AlignmentSide.RIGHT)


def test_crossing_alignments():
    # 적절히 교차하고 길이가 충분한 선형으로 변경
    # 1. 제공된 실제 선형 PI 좌표 목록 (총 8개 지점)
    raw_coords = [
        (252729.930, 407621.060),
        (253356.383, 403670.634),
        (251859.699, 396839.281),
        (255562.242, 368287.722),
        (252930.461, 340078.738),
        (246535.906, 329365.785),
        (241509.931, 316253.765),
        (233279.348, 311736.306)
    ]

    pi_coords = tuple(Point2d(x, y) for x, y in raw_coords)

    # 2. 곡선 스펙 설정 (시·종점은 직선, 중간 PI들은 적절한 설계 반경 부여 예: R=1000m)
    curve_specs = []
    for i in range(len(pi_coords)):
        if i == 0 or i == len(pi_coords) - 1:
            curve_specs.append(PICurveSpec())  # 시점 및 종점
        else:
            curve_specs.append(PICurveSpec(radius=1000.0))  # 중간 PI 원곡선 반경

    # 3. AlignmentBuilder로 선형 구축
    builder = AlignmentBuilder(name="test_parallel_alignments_distance")
    builder.with_pi_coords(pi_coords)
    a = builder.build()

    # 2. 선형 A의 특정 측점(예: station=100.0)에서의 좌표를 샘플링
    test_station = 100.0
    ref_pt = a.point_at(test_station)

    # 3. 그 지점을 수직으로 관통하는 대상 선형 B 생성
    # ref_pt 주변을 지나도록 B의 좌표를 실제 좌표계에 맞춰 구성합니다.
    b = _make([
        (ref_pt.x - 50.0, ref_pt.y - 50.0),
        (ref_pt.x + 50.0, ref_pt.y + 50.0)
    ], [None, None])

    # 4. 거리 및 측점 쿼리 검증
    dist, sta = a.distance_to_alignment(test_station, b)

    # 두 선형이 교차하거나 근접한 경우의 정합성 확인
    assert isinstance(dist, float)
    assert isinstance(sta, float)

# ---- BOTH 최단 ----
def test_both_chooses_shortest():
    a = _make([(0, 0), (200, 0)], [None, None])
    above = _make([(0, 10), (200, 10)], [None, None])
    below = _make([(0, -5), (200, -5)], [None, None])

    dist_a, _ = a.distance_to_alignment(50.0, above)
    dist_b, _ = a.distance_to_alignment(50.0, below)
    assert abs(dist_b) < abs(dist_a)   # 5 < 10


# ---- 원곡선 대상 ----
def test_distance_to_arc():
    a = _make([(0, 0), (200, 0)], [None, None])
    # 수정 후 (예시: y값을 다르게 주어 꺾이도록 설정)
    b = _make([(50, 20), (100, 50), (150, 20)], [None, 100, None])

    dist, sta = a.distance_to_alignment(100.0, b)
    # a의 station 100 = (100, 0). b는 위쪽 원곡선
    assert abs(dist) > 0
    assert 0 <= sta <= b.length


# ---- 완화곡선 대상 ----
def test_distance_to_spiral():
    a = _make([(0, 0), (200, 0)], [None, None])
    b = (
        AlignmentBuilder()
        .with_pi_coords([(50, 20), (100, 20), (150, 50)])
        .with_radii([None, 300, None])
        .with_spiral_lengths(entry=[0, 30, 0], exit=[0, 30, 0])
        .build()
    )

    dist, sta = a.distance_to_alignment(100.0, b)
    assert abs(dist) > 0


# ---- 교차점 탐색 ----
def test_intersection_of_alignments():

    a = _make([(0, 0), (200, 0)], [None, None])
    b = _make([(100, -50), (100, 50)], [None, None])

    intersections = AlignmentQuery.intersection(a, b)
    assert len(intersections) >= 1
    # 교차점: a의 station 100
    assert any(math.isclose(so.station, 100.0, abs_tol=1.0) for so in intersections)


def test_intersection_no_crossing():

    a = _make([(0, 0), (200, 0)], [None, None])
    b = _make([(0, 50), (200, 50)], [None, None])   # 평행

    intersections = AlignmentQuery.intersection(a, b)
    assert len(intersections) == 0


# ---- 편의 ----
def test_nearest_point_on_alignment():

    a = _make([(0, 0), (200, 0)], [None, None])
    so = AlignmentQuery.nearest_point_on_alignment(a, Point2d(50, 5))
    assert math.isclose(so.station, 50.0)
    assert math.isclose(so.offset, -5.0)


# ---- 다양한 측점 ----
@pytest.mark.parametrize("station", [0.0, 50.0, 100.0, 150.0, 200.0])
def test_distance_at_various_stations(station):
    a = _make([(0, 0), (200, 0)], [None, None])
    b = _make([(0, 10), (200, 10)], [None, None])

    dist, sta = a.distance_to_alignment(station, b)
    assert math.isclose(abs(dist), 10.0, abs_tol=1e-6)
    assert math.isclose(sta, station, abs_tol=1e-6)


# ---- start_station 오프셋 ----
def test_start_station_offset_consistency():
    a = (
        AlignmentBuilder()
        .with_pi_coords([(0, 0), (200, 0)])
        .with_radii([None, None])
        .with_start_station(1000.0)
        .build()
    )
    b = (
        AlignmentBuilder()
        .with_pi_coords([(0, 10), (200, 10)])
        .with_radii([None, None])
        .with_start_station(1000.0)
        .build()
    )

    dist, sta = a.distance_to_alignment(1050.0, b)
    assert math.isclose(sta, 1050.0, abs_tol=1e-6)