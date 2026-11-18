from myalignment.grading.site import SiteBuilder, GradingGroupBuilder
from myalignment.grading.grading import Grading
from myalignment.grading.footprint import Footprint, FootprintVertex
from myalignment.grading.criteria_distance import SlopeToDistance
from myalignment.grading.criteria_elevation import SlopeToElevation
from myalignment.grading.criteria_surface import SlopeToSurface
from myalignment.grading.criteria import Slope, SlopeFormat, ProjectionType
from myalignment.grading.target_context import TargetContext

# 부지 경계선 (발자국)
building_footprint = Footprint(
    name="건물외곽",
    vertices=(
        FootprintVertex(0, 0, 100),
        FootprintVertex(50, 0, 100),
        FootprintVertex(50, 30, 100),
        FootprintVertex(0, 30, 100),
    ),
    is_closed=True,
)

# 지표면 (가상)
class MySurface:
    def elevation_at(self, x, y):
        return 95.0   # 평탄 지표면

target_ctx = TargetContext(surface=MySurface())

# Criteria 3종 예시
criteria_to_surface = SlopeToSurface(
    slope=Slope(value=2.0, format=SlopeFormat.RATIO),   # 1:2
    projection=ProjectionType.OUTSIDE,
)

# 그레이딩 3개 (각각 다른 Criteria)
g1 = Grading(name="사면_Surface", footprint=building_footprint, criteria=criteria_to_surface, target_context=target_ctx)

# 그룹으로 묶기
group = (
    GradingGroupBuilder("건물부지")
    .add_grading(g1)
    .build()
)

# 부지 생성
site = (
    SiteBuilder("A부지")
    .add_grading_group(group)
    .build()
)

# 자연 지표선 조회
daylight_lines = group.daylight_lines
print(f"자연 지표선 {len(daylight_lines)}개")
for dl in daylight_lines:
    print(f"  {dl.point} 표고={dl.elevation:.2f}, 거리={dl.distance:.2f}")

print(f"전체 자연 지표선 길이: {site.total_daylight_length:.2f} m")