# tests/quantity/test_shape.py
import math
import pytest
from myalignment.assembly.point import AssemblyPoint
from myalignment.assembly.codes import ShapeCode
from myalignment.quantity.shape import Shape


def test_shape_area_rectangle():
    # 5×3 사각형
    pts = (
        AssemblyPoint(x=0, z=0),
        AssemblyPoint(x=5, z=0),
        AssemblyPoint(x=5, z=3),
        AssemblyPoint(x=0, z=3),
    )
    s = Shape(code=ShapeCode.PAVEMENT, points=pts)
    assert math.isclose(s.area, 15.0)


def test_shape_area_triangle():
    pts = (
        AssemblyPoint(x=0, z=0),
        AssemblyPoint(x=4, z=0),
        AssemblyPoint(x=0, z=3),
    )
    s = Shape(code=ShapeCode.PAVEMENT, points=pts)
    assert math.isclose(s.area, 6.0)


def test_shape_perimeter():
    pts = (
        AssemblyPoint(x=0, z=0),
        AssemblyPoint(x=5, z=0),
        AssemblyPoint(x=5, z=3),
        AssemblyPoint(x=0, z=3),
    )
    s = Shape(code=ShapeCode.PAVEMENT, points=pts)
    assert math.isclose(s.perimeter, 16.0)


def test_shape_invalid_less_than_3():
    with pytest.raises(ValueError):
        Shape(code=ShapeCode.PAVEMENT, points=(AssemblyPoint(x=0, z=0),))


def test_shape_centroid():
    pts = (
        AssemblyPoint(x=0, z=0),
        AssemblyPoint(x=4, z=0),
        AssemblyPoint(x=4, z=4),
        AssemblyPoint(x=0, z=4),
    )
    s = Shape(code=ShapeCode.PAVEMENT, points=pts)
    cx, cz = s.centroid
    assert math.isclose(cx, 2.0, abs_tol=1e-6)
    assert math.isclose(cz, 2.0, abs_tol=1e-6)




