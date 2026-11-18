# 철도 선형 생성
from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.cant.curve import CantCurve, CantPivotMethod, CantCriticalStation
from myalignment.corridor.region import CorridorRegion

# 철도 선형 생성 (체이닝 및 .build() 정상 작동)
rail = (
    AlignmentBuilder("본선")
    .with_pi_coords([(0, 0), (500, 0), (1000, 200)])
    .with_radii([None, 800, None])
    .as_rail_alignment(gauge=1.435)   # 설정 메서드 (return self)
    .build()                        # 최종 빌드
)

# 캔트 곡선 추가
cant = CantCurve(
    name="R=800 곡선부",
    start_station=200, end_station=400,
    pivot_method=CantPivotMethod.LEFT_RAIL,
    critical_stations=(
        CantCriticalStation(station=200, cant_value=0),
        CantCriticalStation(station=300, cant_value=0.105, is_full_cant=True),
        CantCriticalStation(station=400, cant_value=0),
    ),
)
rail = rail.with_cant_curve(cant) if hasattr(rail, "with_cant_curve") else rail  # 필요시 처리
