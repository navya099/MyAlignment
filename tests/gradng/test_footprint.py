# tests/grading/test_footprint.py
from myalignment.grading.footprint import Footprint, FootprintVertex
import math

def test_footprint_length_open():
    fp = Footprint(
        vertices=(
            FootprintVertex(0, 0, 100),
            FootprintVertex(100, 0, 100),
            FootprintVertex(100, 100, 100),
        ),
        is_closed=False,
    )
    assert math.isclose(fp.length, 200.0)


def test_footprint_length_closed():
    fp = Footprint(
        vertices=(
            FootprintVertex(0, 0, 100),
            FootprintVertex(100, 0, 100),
            FootprintVertex(100, 100, 100),
            FootprintVertex(0, 100, 100),
        ),
        is_closed=True,
    )
    assert math.isclose(fp.length, 400.0)


def test_footprint_segments():
    fp = Footprint(
        vertices=(FootprintVertex(0, 0, 0), FootprintVertex(10, 0, 0)),
        is_closed=False,
    )
    segs = fp.segments()
    assert len(segs) == 1