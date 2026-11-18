from myalignment.surface.breakline_vertex import BreaklineVertex
from myalignment.surface.tin_surface_builder import TinSurfaceBuilder
from myalignment.surface.boundary import Boundary
from myalignment.surface.breakline import Breakline
from myalignment.surface.breakline_type import BreaklineType

# TIN + Boundary + Breakline 통합
surface = (
    TinSurfaceBuilder("도로지형")
    # 격자 지형 (평탄)
    .add_grid(0, 100, 0, 100, nx=51, ny=51,
              elevation_func=lambda x, y: 100.0)
    # 외곽 경계
    .add_outer_boundary(Boundary.rectangle(0, 0, 100, 100))
    # 도로 Breakline (중앙)
    .add_breakline_coords(
        [(0, 50, 105), (50, 50, 105), (100, 50, 105)],
        name="도로중심선",
        breakline_type=BreaklineType.STANDARD,
    )
    # 능선 Breakline (곡선)
    .add_breakline_coords(
        [(10, 10, 110), (30, 20, 115), (50, 30, 120), (70, 20, 115), (90, 10, 110)],
        name="능선",
        breakline_type=BreaklineType.STANDARD,
    )
    # 수직 벽 (성토 경계)
    .add_breakline(
        Breakline(
            name="옹벽",
            breakline_type=BreaklineType.WALL,
            vertices=(
                BreaklineVertex(0, 80, 100),
                BreaklineVertex(100, 80, 100),
            ),
            right_elevations=(95, 95),   # 우측 표고 낮음
        )
    )
    .build()
)

print(f"TIN: {len(surface.points)}점, {len(surface.triangles)}삼각형")
print(f"Breakline: {len(surface.breaklines)}개, 총 {surface.breaklines.total_length():.1f}m")
print(f"유효 면적: {surface.area_2d:,.1f}m²")

# 표고 조회 (Breakline 위/밖)
print(f"\n(50, 50) 도로 위: {surface.elevation_at(50, 50):.2f}m")
print(f"(50, 30) 능선 위: {surface.elevation_at(50, 30):.2f}m")
print(f"(50, 70) 일반: {surface.elevation_at(50, 70):.2f}m")