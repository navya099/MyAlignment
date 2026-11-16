# tests/geometry/test_spiral_geometry.py
import pytest

from myalignment.enum.spiraltype import SpiralType
from myalignment.geometry.spiral_geometry import SpiralParams, SpiralGeometry
from myalignment.utils import CurveDirection
import math

def test_spiral_type_required():
    with pytest.raises(ValueError):
        SpiralParams(radius=100, length=50, spiral_type=SpiralType.OffsetInvalidSpiralType)


def test_japanese_vs_clothoid_differ():
    """3차 vs 5차 → 좌표가 달라야 함."""
    p_j = SpiralParams(radius=300, length=50, spiral_type=SpiralType.JapaneseCubic)
    p_c = SpiralParams(radius=300, length=50, spiral_type=SpiralType.Clothoid)
    g_j = SpiralGeometry(params=p_j, direction=CurveDirection.LEFT)
    g_c = SpiralGeometry(params=p_c, direction=CurveDirection.LEFT)

    pt_j = g_j.point_at(50.0)
    pt_c = g_c.point_at(50.0)
    assert not math.isclose(pt_j.x, pt_c.x, abs_tol=1e-6) or \
           not math.isclose(pt_j.y, pt_c.y, abs_tol=1e-6)