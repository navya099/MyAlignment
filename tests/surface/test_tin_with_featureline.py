# tests/surface/test_tin_with_featureline.py
from myalignment.featureline.builder import FeatureLineBuilder
from myalignment.surface.tin_surface_builder import TinSurfaceBuilder
import math

def test_feature_line_as_breakline():
    fl = (
        FeatureLineBuilder("능선")
        .add_coords([(0, 5, 120), (10, 5, 120)])
        .build()
    )
    surface = (
        TinSurfaceBuilder()
        .add_grid(0, 10, 0, 10, nx=11, ny=11, elevation_func=lambda x, y: 100)
        .add_feature_line_as_breakline(fl)
        .build()
    )
    # 능선 위 표고 = 120
    assert math.isclose(surface.elevation_at(5, 5), 120.0, abs_tol=1e-6)