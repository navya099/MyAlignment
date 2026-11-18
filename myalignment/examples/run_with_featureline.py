from myalignment.featureline.builder import FeatureLineBuilder
from myalignment.surface.tin_surface_builder import TinSurfaceBuilder
from myalignment.grading.footprint import Footprint

# 1) FeatureLine 생성 (도로 외곽선)
road_edge = (
    FeatureLineBuilder("도로외곽")
    .add_coords([
        (0, 0, 100), (50, 0, 102), (100, 0, 105),
    ])
    .with_site("A부지")
    .build()
)

# 2) Surface Breakline으로 사용
surface = (
    TinSurfaceBuilder("도로지형")
    .add_grid(-10, 110, -20, 20, nx=61, ny=21,
              elevation_func=lambda x, y: 100)
    .add_feature_line_as_breakline(road_edge)
    .build()
)

# 3) FeatureLine 위 표고 확인
print(f"FeatureLine 3D 길이: {road_edge.length_3d:.2f}m")
print(f"최대 구배: {road_edge.max_grade*100:.2f}%")
print(f"(50, 0) 표고: {surface.elevation_at(50, 0):.2f}m")

# 4) Grading Footprint로 변환
footprint = Footprint.from_feature_line(road_edge, name="도로부지")
print(f"Footprint 정점: {len(footprint.vertices)}개")

# 5) Surface 표고 할당 (역방향)
updated_fl = road_edge.assign_elevations_from_surface(surface)
print(f"갱신된 FeatureLine 첫 점 표고: {updated_fl.vertices[0].z:.2f}m")