# tests/surface/profiling_surface.py
import cProfile
import io
import pstats
import time

from myalignment.surface.tin_surface_builder import TinSurfaceBuilder
from myalignment.surface.boundary import Boundary


def build_surface():
    return (
        TinSurfaceBuilder("계획부지")
        .add_grid(0, 100, 0, 100, nx=51, ny=51,
                  elevation_func=lambda x, y: 100 + 0.1 * x)
        .add_outer_boundary(Boundary.rectangle(0, 0, 100, 100, name="부지경계"))
        .add_hide_boundary(Boundary.circle(30, 30, 10, n_segments=32, name="연못"))
        .add_hide_boundary(Boundary.rectangle(60, 60, 80, 80, name="건물"))
        .build()
    )


if __name__ == "__main__":
    # 시간 측정
    t0 = time.perf_counter()
    surface = build_surface()
    t1 = time.perf_counter()
    print(f"build_surface: {(t1 - t0) * 1000:.2f} ms "
          f"(points={len(surface.points)}, triangles={len(surface.triangles)})")

    # 프로파일링
    profiler = cProfile.Profile()
    profiler.enable()
    build_surface()
    profiler.disable()
    s = io.StringIO()
    pstats.Stats(profiler, stream=s).sort_stats("cumulative").print_stats(15)
    print(s.getvalue())