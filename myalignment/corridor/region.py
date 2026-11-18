# corridor/region.py
from __future__ import annotations
from dataclasses import dataclass, field
import math

from myalignment.assembly.assembly import Assembly
from myalignment.cant.curve import CantCurve, CantPivotMethod
from myalignment.target.mapping import TargetMapping


@dataclass(frozen=True, slots=True)
class CorridorRegion:
    """
    코리더 영역 (불변).

    어셈블리가 적용되는 측점 범위.
    """
    name: str = ""
    start_station: float = 0.0
    end_station: float = 0.0
    assembly: Assembly | None = None
    frequency: float = 10.0  # 측점 간격 (m)
    target_mapping: TargetMapping = field(default_factory=TargetMapping.empty)
    # Region에 CantCurve 참조 (선택)
    cant_curve: CantCurve | None = None

    def __post_init__(self):
        if self.end_station < self.start_station:
            raise ValueError(f"end < start: {self.end_station} < {self.start_station}")
        if self.frequency <= 0:
            raise ValueError(f"frequency > 0 필요: {self.frequency}")

    @property
    def length(self) -> float:
        return self.end_station - self.start_station

    @property
    def station_count(self) -> int:
        """영역 내 샘플 측점 수."""
        return int(self.length / self.frequency) + 1

    def sample_stations(self) -> list[float]:
        """영역 내 샘플 측점 리스트."""
        n = self.station_count
        return [
            self.start_station + self.length * i / (n - 1)
            for i in range(n)
        ] if n > 1 else [self.start_station]

    def cross_section_at(self, station: float):
        points, links = self.assembly.generate_cross_section(self.target_mapping)
        if self.cant_curve is not None:
            cant = self.cant_curve.cant_at(station)
            if cant is not None:
                # 캔트 커브의 피벗 방식과 임계 측점 정보를 함께 전달
                points = self._apply_cant(points, cant, self.cant_curve.pivot_method)
        return points, links

    def _apply_cant(self, points, cant, pivot_method: CantPivotMethod, gauge: float = 1.435) -> list:
        """
        철도 캔트(Superelevation) 및 피벗 방식에 따라 횡단면 점들의 표고를 조정합니다.

        Args:
            points: 단면 점 리스트 (offset, elevation 속성 보유)
            cant: CantCriticalStation 객체 (left_rail_delta, right_rail_delta 포함)
            pivot_method: 회전 중심축 기준 (CENTERLINE, LEFT_RAIL, RIGHT_RAIL)
            gauge: 궤간 (표준궤 기본 1.435m)
        """
        left_delta = getattr(cant, "left_rail_delta", 0.0)
        right_delta = getattr(cant, "right_rail_delta", 0.0)

        if abs(left_delta) < 1e-6 and abs(right_delta) < 1e-6:
            return points

        half_gauge = gauge / 2.0

        # 1. 피벗 방식에 따른 기준 변위 및 경사도(Rotation Slope) 계산
        if pivot_method == CantPivotMethod.CENTERLINE:
            # 센터라인(offset = 0) 표고는 변하지 않음 (delta = 0)
            # 좌우 레일 구간별 구배 계산
            left_slope = left_delta / (-half_gauge)  # 음수 오프셋 방향 구배
            right_slope = right_delta / half_gauge  # 양수 오프셋 방향 구배

            updated_points = []
            for pt in points:
                offset = getattr(pt, "offset", getattr(pt, "x", 0.0))
                elevation = getattr(pt, "elevation", getattr(pt, "z", 0.0))

                # 위치에 따라 선형 보간하여 표고 변위 적용
                if offset < 0:
                    delta_z = offset * (left_delta / -half_gauge)
                elif offset > 0:
                    delta_z = offset * (right_delta / half_gauge)
                else:
                    delta_z = 0.0

                new_elevation = elevation + delta_z
                updated_points.append(self._update_point_elevation(pt, new_elevation))
            return updated_points

        elif pivot_method == CantPivotMethod.LEFT_RAIL:
            # 좌측 레일(offset = -half_gauge)을 고정축(delta = 0)으로 회전
            # 전체 단면의 회전 경사각(slope) 산출
            total_tilt = right_delta - left_delta
            rotation_slope = total_tilt / gauge

            updated_points = []
            for pt in points:
                offset = getattr(pt, "offset", getattr(pt, "x", 0.0))
                elevation = getattr(pt, "elevation", getattr(pt, "z", 0.0))

                # 좌측 레일 위치(-half_gauge)를 기준으로 한 상대 오프셋에 경사 적용
                relative_offset = offset - (-half_gauge)
                delta_z = left_delta + relative_offset * rotation_slope

                new_elevation = elevation + delta_z
                updated_points.append(self._update_point_elevation(pt, new_elevation))
            return updated_points

        elif pivot_method == CantPivotMethod.RIGHT_RAIL:
            # 우측 레일(offset = +half_gauge)을 고정축으로 회전
            total_tilt = right_delta - left_delta
            rotation_slope = total_tilt / gauge

            updated_points = []
            for pt in points:
                offset = getattr(pt, "offset", getattr(pt, "x", 0.0))
                elevation = getattr(pt, "elevation", getattr(pt, "z", 0.0))

                # 우측 레일 위치(+half_gauge)를 기준으로 한 상대 오프셋에 경사 적용
                relative_offset = offset - half_gauge
                delta_z = right_delta + relative_offset * rotation_slope

                new_elevation = elevation + delta_z
                updated_points.append(self._update_point_elevation(pt, new_elevation))
            return updated_points

        return points

    def _update_point_elevation(self, pt, new_elevation: float):
        """불변 객체(frozen dataclass)의 표고를 갱신한 새 객체 반환"""
        from dataclasses import replace
        if hasattr(pt, "elevation"):
            return replace(pt, elevation=new_elevation)
        elif hasattr(pt, "z"):
            return replace(pt, z=new_elevation)
        return pt

    def with_targets(self, mapping: TargetMapping) -> "CorridorRegion":
        """Target 매핑 갱신한 새 Region."""
        from dataclasses import replace
        return replace(self, target_mapping=mapping)