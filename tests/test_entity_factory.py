# tests/entity/test_entity_factory.py
import math
import pytest

from myalignment.enitity.entity_factory import build_alignment_entities
from myalignment.enitity.line_entity import LineEntity
from myalignment.enitity.spiral_entity import SpiralEntity
from myalignment.enum.spiraltype import SpiralType
from myalignment.exception.alignment_error import NotEnoughPIPointError, InvalidGeometryError


def test_straight_only():
    """직선만 (모든 radius=None)."""
    col = build_alignment_entities(
        coords=[(0, 0), (100, 0), (200, 0)],
        radii=[None, None, None],
    )
    assert len(col) == 2   # 두 개의 LineEntity
    assert all(isinstance(e, LineEntity) for e in col)
    assert math.isclose(col.length, 200.0)


def test_single_arc():
    """단일 원곡선 (PI 1개)."""
    col = build_alignment_entities(
        coords=[(0, 0), (100, 0), (200, 100)],
        radii=[None, 200, None],
    )
    # Line + Arc + Line
    types = [type(e).__name__ for e in col]
    assert "ArcEntity" in types
    assert col.length > 0


def test_symmetric_spiral():
    """대칭 완화곡선 (SCS)."""
    col = build_alignment_entities(
        coords=[(0, 0), (100, 0), (200, 100)],
        radii=[None, 300, None],
        spiral_type=SpiralType.Clothoid,
        entry_lengths=[0, 30, 0],
        exit_lengths=[0, 30, 0],
    )
    types = [type(e).__name__ for e in col]
    # Line + Spiral + Arc + Spiral + Line
    assert types.count("SpiralEntity") == 2
    assert "ArcEntity" in types


def test_asymmetric_spiral():
    """비대칭 완화곡선."""
    col = build_alignment_entities(
        coords=[(0, 0), (100, 0), (200, 100)],
        radii=[None, 300, None],
        spiral_type=SpiralType.Clothoid,
        entry_lengths=[0, 20, 0],
        exit_lengths=[0, 40, 0],
    )
    spirals = [e for e in col if isinstance(e, SpiralEntity)]
    assert len(spirals) == 2
    assert math.isclose(spirals[0].length, 20.0)
    assert math.isclose(spirals[1].length, 40.0)


def test_continuity():
    """생성된 Entity 시퀀스의 연속성."""
    col = build_alignment_entities(
        coords=[(0, 0), (100, 0), (200, 100)],
        radii=[None, 200, None],
        entry_lengths=[0, 30, 0],
        exit_lengths=[0, 30, 0],
    )
    for i in range(len(col) - 1):
        e1, e2 = col[i], col[i + 1]
        assert e1.end_coord.distance_to(e2.start_coord) < 1e-6
        assert math.isclose(e1.end_station, e2.start_station, abs_tol=1e-6)


def test_not_enough_pi():
    with pytest.raises(NotEnoughPIPointError):
        build_alignment_entities(coords=[(0, 0)], radii=[None])


def test_duplicate_pi():
    with pytest.raises(Exception):
        build_alignment_entities(
            coords=[(0, 0), (100, 0), (100, 0)],
            radii=[None, 200, None],
        )


def test_invalid_radius():
    with pytest.raises(InvalidGeometryError):
        build_alignment_entities(
            coords=[(0, 0), (100, 0), (200, 0)],   # 일직선
            radii=[None, 200, None],
        )


def test_spiral_type_affects_geometry():
    """Clothoid vs JapaneseCubic → 좌표 차이."""
    col_c = build_alignment_entities(
        coords=[(0, 0), (100, 0), (200, 100)],
        radii=[None, 300, None],
        spiral_type=SpiralType.Clothoid,
        entry_lengths=[0, 30, 0],
        exit_lengths=[0, 30, 0],
    )
    col_j = build_alignment_entities(
        coords=[(0, 0), (100, 0), (200, 100)],
        radii=[None, 300, None],
        spiral_type=SpiralType.JapaneseCubic,
        entry_lengths=[0, 30, 0],
        exit_lengths=[0, 30, 0],
    )
    # 끝점이 미묘하게 달라야 함
    assert col_c.end_coord.distance_to(col_j.end_coord) > 1e-9


def test_start_station_offset():
    """start_station != 0."""
    col = build_alignment_entities(
        coords=[(0, 0), (100, 0), (200, 0)],
        radii=[None, None, None],
        start_station=1000.0,
    )
    assert math.isclose(col.start_station, 1000.0)
    assert math.isclose(col.end_station, 1200.0)