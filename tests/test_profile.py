# tests/profile/test_profile.py
import math
import pytest

from myalignment.profile.profile import ProfileBuilder
from myalignment.profile.profile_asymmetric_parabola import ProfileAsymmetricParabola
from myalignment.profile.profile_symmetric_parabola import ProfileSymmetricParabola
from myalignment.profile.profileentitycollection import ProfileEntityCollection
from myalignment.profile.profiletangent import ProfileTangent
from myalignment.profile.profiletype import ProfileType


def test_tangent_elevation():
    t = ProfileTangent.create(
        start_station=0, end_station=100,
        start_elevation=10, end_elevation=20,
    )
    assert math.isclose(t.grade, 0.1)
    assert math.isclose(t.elevation_at(50), 15.0)


def test_symmetric_parabola_crest():
    """정점 (crest) 포물선: G1=+2%, G2=-2%, L=200."""
    p = ProfileSymmetricParabola.create(
        pvi_station=100, pvi_elevation=50,
        grade_in=+0.02, grade_out=-0.02, curve_length=200,
    )
    # VPC(0) / VPT(200): 접선 연장 표고 = 50 - 2 = 48
    assert math.isclose(p.elevation_at(0), 48.0, abs_tol=1e-6)
    assert math.isclose(p.elevation_at(200), 48.0, abs_tol=1e-6)
    # PVI station(100): 포물선 중앙 = 48 + 2 - 1 = 49
    assert math.isclose(p.elevation_at(100), 49.0, abs_tol=1e-6)
    # start/end_elevation == VPC/VPT 접선 연장값
    assert math.isclose(p.start_elevation, 48.0, abs_tol=1e-9)
    assert math.isclose(p.end_elevation, 48.0, abs_tol=1e-9)
    assert math.isclose(
        p.start_elevation, p.elevation_at(p.start_station), abs_tol=1e-9
    )
    assert math.isclose(
        p.end_elevation, p.elevation_at(p.end_station), abs_tol=1e-9
    )
    # 구배
    assert math.isclose(p.grade_at(0), +0.02, abs_tol=1e-6)
    assert math.isclose(p.grade_at(200), -0.02, abs_tol=1e-6)
    # PVI station에서 구배 = (G_in + G_out)/2 = 0
    assert math.isclose(p.grade_at(100), 0.0, abs_tol=1e-6)
    # K = 200 / (-0.02 - 0.02) = -5000
    assert math.isclose(p.k_value, -5000.0)


def test_collection_continuity():
    t1 = ProfileTangent.create(0, 100, 10, 20)
    t2 = ProfileTangent.create(100, 200, 20, 30)
    col = ProfileEntityCollection(entities=(t1, t2))
    assert math.isclose(col.length, 200.0)


def test_collection_discontinuity_raises():
    t1 = ProfileTangent.create(0, 100, 10, 20)
    t2 = ProfileTangent.create(100, 200, 25, 30)
    with pytest.raises(ValueError):
        ProfileEntityCollection(entities=(t1, t2))


def test_builder():
    p = (
        ProfileBuilder("FG", ProfileType.FG)
        .add_tangent(0, 100, 10, 20)
        .add_tangent(100, 200, 20, 30)
        .build()
    )
    assert p.name == "FG"
    assert p.profile_type == ProfileType.FG
    assert math.isclose(p.length, 200.0)
    assert math.isclose(p.elevation_at(50), 15.0)


def test_max_grade_signs():
    p = (
        ProfileBuilder()
        .add_tangent(0, 100, 10, 15)    # +5%
        .add_tangent(100, 200, 15, 10)  # -5%
        .build()
    )
    assert math.isclose(p.max_slope, 0.05)
    assert math.isclose(p.min_slope, -0.05)
    assert math.isclose(p.max_abs_slope, 0.05)


def test_reversed():
    p = (
        ProfileBuilder()
        .add_tangent(0, 100, 10, 20)
        .add_tangent(100, 200, 20, 30)
        .build()
    )
    r = p.reversed()
    assert math.isclose(r.start_station, p.start_station)
    assert math.isclose(r.length, p.length)
    assert math.isclose(r.elevation_at(r.start_station), 30.0)
    assert math.isclose(r.elevation_at(r.end_station), 10.0)


def test_reversed_tangent_parabola_mix():
    """Tangent-Parabola 혼합 프로파일의 반전 및 연속성."""
    # P의 VPC/VPT = 16 ∓ 0.02·100 = 14, 14
    p = (
        ProfileBuilder()
        .add_tangent(0, 100, 12, 14)       # +2%, 끝 14
        .add_symmetric_parabola(
            pvi_station=200, pvi_elevation=16,
            grade_in=0.02, grade_out=-0.02, curve_length=200,
        )   # VPC=100 elev=14, VPT=300 elev=14
        .add_tangent(300, 400, 14, 12)     # -2%
        .build()
    )
    r = p.reversed()
    assert math.isclose(r.length, p.length)
    assert math.isclose(
        r.elevation_at(r.start_station),
        p.elevation_at(p.end_station),
        abs_tol=1e-6,
    )
    assert math.isclose(
        r.elevation_at(r.end_station),
        p.elevation_at(p.start_station),
        abs_tol=1e-6,
    )

def test_asymmetric_parabola_basic():
    """비대칭 포물선: G1=+2%, G2=-3%, L_in=100, L_out=150."""
    p = ProfileAsymmetricParabola.create(
        pvi_station=200, pvi_elevation=50,
        grade_in=+0.02, grade_out=-0.03,
        length_in=100, length_out=150,
    )
    # VPC(100): 50 - 0.02·100 = 48
    assert math.isclose(p.elevation_at(100), 48.0, abs_tol=1e-9)
    # VPT(350): 50 + (-0.03)·150 = 45.5
    assert math.isclose(p.elevation_at(350), 45.5, abs_tol=1e-9)
    assert math.isclose(p.start_elevation, 48.0, abs_tol=1e-9)
    assert math.isclose(p.end_elevation, 45.5, abs_tol=1e-9)
    # 경계 구배 == G_in / G_out
    assert math.isclose(p.grade_at(100), +0.02, abs_tol=1e-9)
    assert math.isclose(p.grade_at(350), -0.03, abs_tol=1e-9)
    # PVI station 표고 = PVI_elev + k
    L = 250
    k = (-0.03 - 0.02) * 100 * 150 / (2 * L)
    assert math.isclose(p.elevation_at(200), 50.0 + k, abs_tol=1e-9)
    # PVI station 구배 = (G1·L_in + G2·L_out) / L
    expected_grade = (0.02 * 100 + (-0.03) * 150) / L
    assert math.isclose(p.grade_at(200), expected_grade, abs_tol=1e-9)
    # 표고/구배 연속 (PVI station)
    eps = 1e-6
    assert math.isclose(
        p.elevation_at(200 - eps), p.elevation_at(200 + eps), abs_tol=1e-5
    )
    assert math.isclose(
        p.grade_at(200 - eps), p.grade_at(200 + eps), abs_tol=1e-5
    )

def test_asymmetric_parabola_symmetric_case():
    """L_in == L_out 이면 대칭 포물선과 동일해야 함."""
    asym = ProfileAsymmetricParabola.create(
        pvi_station=100, pvi_elevation=50,
        grade_in=+0.02, grade_out=-0.02,
        length_in=100, length_out=100,
    )
    sym = ProfileSymmetricParabola.create(
        pvi_station=100, pvi_elevation=50,
        grade_in=+0.02, grade_out=-0.02, curve_length=200,
    )
    for sta in [0, 50, 100, 150, 200]:
        assert math.isclose(
            asym.elevation_at(sta), sym.elevation_at(sta), abs_tol=1e-9
        )
        assert math.isclose(
            asym.grade_at(sta), sym.grade_at(sta), abs_tol=1e-9
        )


def test_asymmetric_parabola_reversed():
    p = (
        ProfileBuilder()
        .add_tangent(0, 100, 12, 14)   # T1: +2%, 끝 14
        .add_asymmetric_parabola(
            pvi_station=200, pvi_elevation=16,
            grade_in=0.02, grade_out=-0.03,
            length_in=100, length_out=100,   # VPC=14, VPT=13
        )
        .add_tangent(300, 400, 13, 10)   # T2: -3%
        .build()
    )
    r = p.reversed()
    assert math.isclose(r.length, 400)
    # 경계 표고 반전 대칭
    assert math.isclose(
        r.elevation_at(r.start_station), p.elevation_at(p.end_station), abs_tol=1e-9
    )
    assert math.isclose(
        r.elevation_at(r.end_station), p.elevation_at(p.start_station), abs_tol=1e-9
    )
    # 경계 구배 반전 대칭
    assert math.isclose(r.grade_at(r.start_station), -p.grade_at(p.end_station), abs_tol=1e-9)
    assert math.isclose(r.grade_at(r.end_station), -p.grade_at(p.start_station), abs_tol=1e-9)