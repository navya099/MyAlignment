# tests/alignment/test_alignment.py
import math
import pytest
from cadgeom import Point2d

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.profile.profile import Profile
from myalignment.profile.profiletype import ProfileType
from myalignment.structure.bridge import Bridge


def test_builder_straight():
    a = (
        AlignmentBuilder("Test")
        .with_pi_coords([(0, 0), (100, 0), (200, 0)])
        .with_radii([None, None, None])
        .build()
    )
    assert a.name == "Test"
    assert math.isclose(a.length, 200.0)
    assert a.start_station == 0.0
    assert a.end_station == 200.0


def test_builder_with_arc():
    a = (
        AlignmentBuilder("Test")
        .with_pi_coords([(0, 0), (100, 0), (200, 100)])
        .with_radii([None, 200, None])
        .build()
    )
    types = [type(e).__name__ for e in a.entities]
    assert "ArcEntity" in types


def test_builder_with_spiral():
    a = (
        AlignmentBuilder("Test")
        .with_pi_coords([(0, 0), (100, 0), (200, 100)])
        .with_radii([None, 300, None])
        .with_spiral_lengths(entry=[0, 30, 0], exit=[0, 30, 0])
        .build()
    )
    types = [type(e).__name__ for e in a.entities]
    assert types.count("SpiralEntity") == 2


def test_point_at():
    a = (
        AlignmentBuilder()
        .with_pi_coords([(0, 0), (100, 0)])
        .with_radii([None, None])
        .build()
    )
    p = a.point_at(50.0)
    assert p.distance_to(Point2d(50, 0)) < 1e-6


def test_station_offset_of():
    a = (
        AlignmentBuilder()
        .with_pi_coords([(0, 0), (100, 0)])
        .with_radii([None, None])
        .build()
    )
    so = a.station_offset_of(Point2d(50, 5))
    assert math.isclose(so.station, 50.0)
    assert math.isclose(so.offset, -5.0)


def test_start_station_offset():
    a = (
        AlignmentBuilder()
        .with_pi_coords([(0, 0), (100, 0)])
        .with_radii([None, None])
        .with_start_station(1000.0)
        .build()
    )
    assert math.isclose(a.start_station, 1000.0)
    assert math.isclose(a.end_station, 1100.0)


def test_transaction_update_pi():
    a = (
        AlignmentBuilder()
        .with_pi_coords([(0, 0), (100, 0), (200, 100)])
        .with_radii([None, 200, None])
        .build()
    )
    original_len = a.length

    with a.modify() as tx:
        tx.update_pi_and_radius(index=1, point=Point2d(100, 50), radius=300)
    new_a = tx.result

    # 원본 불변
    assert math.isclose(a.length, original_len)
    # 새 객체 생성
    assert new_a is not a


def test_transaction_rename():
    a = AlignmentBuilder("Old").with_pi_coords([(0, 0), (100, 0)]).with_radii([None, None]).build()
    with a.modify() as tx:
        tx.rename("New")
    assert tx.result.name == "New"
    assert a.name == "Old"   # 원본 불변


def test_offset_alignment():
    a = (
        AlignmentBuilder()
        .with_pi_coords([(0, 0), (100, 0)])
        .with_radii([None, None])
        .build()
    )
    a2 = a.offset_alignment(-5.0)   # 좌측 5m
    p = a2.point_at(50.0)
    assert p.distance_to(Point2d(50, 5)) < 1e-6


def test_reversed_alignment():
    a = (
        AlignmentBuilder()
        .with_pi_coords([(0, 0), (100, 0)])
        .with_radii([None, None])
        .build()
    )
    a2 = a.reversed_alignment()
    assert math.isclose(a2.start_station, a.start_station)
    assert math.isclose(a2.length, a.length)
    # 시작점이 원래 끝점
    assert a2.point_at(a2.start_station).distance_to(Point2d(100, 0)) < 1e-6


def test_profile_integration():

    fg = Profile(name="FG", profile_type=ProfileType.FG)

    a = (
        AlignmentBuilder()
        .with_pi_coords([(0, 0), (100, 0)])
        .with_radii([None, None])
        .with_profile(fg)
        .build()
    )
    assert a.fg_profile is fg
    assert a.grades_count == 0   # PVI 없음


def test_structure_integration():

    bridge = Bridge.create("교량1", 50, 150)
    a = (
        AlignmentBuilder()
        .with_pi_coords([(0, 0), (200, 0)])
        .with_radii([None, None])
        .with_structure(bridge)
        .build()
    )
    assert a.bridge_count == 1
    assert a.tunnel_count == 0