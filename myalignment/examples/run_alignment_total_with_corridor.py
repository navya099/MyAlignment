from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.superelevation.critical_station import SuperelevationCriticalStation, TransitionRegionType
from myalignment.superelevation.curve import SuperelevationCurve, PivotMethod

# 편구배 데이터
se_curve = SuperelevationCurve(
    name="R=800 곡선",
    start_station=200,
    end_station=400,
    pivot_method=PivotMethod.CENTER_BASELINE,
    critical_stations=(
        SuperelevationCriticalStation(station=200, region_type=TransitionRegionType.NORMAL),
        SuperelevationCriticalStation(station=250, region_type=TransitionRegionType.TRANSITION_IN),
        SuperelevationCriticalStation(station=300, region_type=TransitionRegionType.FULL_SUPERELEVATION),
        SuperelevationCriticalStation(station=350, region_type=TransitionRegionType.TRANSITION_OUT),
        SuperelevationCriticalStation(station=400, region_type=TransitionRegionType.NORMAL),
    ),
)

# 코리더
corridor = (
    CorridorBuilder("본선코리더")
    .add_baseline("BL1", "본선", "설계선", 0, 1000)
    .add_region("일반구간", 0, 200, "표준단면", frequency=10)
    .add_region("곡선구간", 200, 400, "편구배단면", frequency=5)
    .add_region("일반구간2", 400, 1000, "표준단면", frequency=10)
    .build()
)

# 선형 통합
alignment = (
    AlignmentBuilder("본선")
    .with_pi_coords([(0, 0), (500, 0), (1000, 200)])
    .with_radii([None, 800, None])
    .with_corridor(corridor)
    .with_superelevation_curve(se_curve)
    .build()
)

print(f"코리더: {alignment.primary_corridor}")
print(f"편구배 곡선: {alignment.superelevation.curve_at_station(300)}")