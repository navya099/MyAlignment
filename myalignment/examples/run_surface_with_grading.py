from myalignment.surface.tin_surface_builder import TinSurfaceBuilder
from myalignment.surface.tin_surface import TinSurface
from myalignment.grading.criteria_surface import SlopeToSurface
from myalignment.grading.criteria import Slope, SlopeFormat, ProjectionType
from myalignment.grading.target_context import TargetContext
from myalignment.grading.footprint import Footprint, FootprintVertex
from myalignment.grading.grading import Grading
from myalignment.grading.site import SiteBuilder, GradingGroupBuilder

# 1) 원지형 Surface
existing = (
    TinSurfaceBuilder("원지형")
    .add_points([
        (0, 0, 100), (100, 0, 105), (100, 100, 110), (0, 100, 105),
    ])
    .build()
)

# 2) 계획 Surface (평탄)
design = (
    TinSurfaceBuilder("계획지형")
    .add_points([
        (0, 0, 95), (100, 0, 95), (100, 100, 95), (0, 100, 95),
    ])
    .build()
)

# 3) 토공량 계산
cut, fill = existing.volume_between(design)
print(f"Cut: {cut:,.1f} m³")
print(f"Fill: {fill:,.1f} m³")

# 4) Grading (Surface Target)
footprint = Footprint(
    vertices=(
        FootprintVertex(20, 20, 95),
        FootprintVertex(80, 20, 95),
        FootprintVertex(80, 80, 95),
        FootprintVertex(20, 80, 95),
    ),
    is_closed=True,
)

criteria = SlopeToSurface(
    slope=Slope(value=2.0, format=SlopeFormat.RATIO),
    projection=ProjectionType.OUTSIDE,
)

grading = Grading(
    name="건물부지_사면",
    footprint=footprint,
    criteria=criteria,
    target_context=TargetContext(surface=existing),
)

group = GradingGroupBuilder("건물부지").add_grading(grading).build()
site = SiteBuilder("A부지").add_grading_group(group).build()

# 5) 지표면 표고/경사 조회
x, y = 50, 50
print(f"위치 ({x}, {y}) 표고: {existing.elevation_at(x, y):.2f} m")
A, B, slope_pct = existing.slope_at(x, y)
print(f"경사: {slope_pct:.1f}% (∂z/∂x={A:.3f}, ∂z/∂y={B:.3f})")