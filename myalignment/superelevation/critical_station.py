# superelevation/critical_station.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import math


class TransitionRegionType(Enum):
    """전이 영역 타입 (C3D 호환)."""
    NORMAL = "정상"
    TRANSITION_IN = "편구배 진입"
    FULL_SUPERELEVATION = "완전 편구배"
    TRANSITION_OUT = "편구배 진출"


class CrossSegmentType(Enum):
    """횡단면 세그먼트 타입 (C3D 호환)."""
    LEFT_OUT_SHOULDER = "좌측 외측 갓길"
    LEFT_OUT_LANE = "좌측 외측 차로"
    LEFT_IN_LANE = "좌측 내측 차로"
    LEFT_IN_SHOULDER = "좌측 내측 갓길"
    RIGHT_IN_SHOULDER = "우측 내측 갓길"
    RIGHT_IN_LANE = "우측 내측 차로"
    RIGHT_OUT_LANE = "우측 외측 차로"
    RIGHT_OUT_SHOULDER = "우측 외측 갓길"


@dataclass(frozen=True, slots=True)
class SuperelevationCriticalStation:
    """
    편구배 임계 측점 (불변).

    C3D의 SuperelevationCriticalStation과 호환.
    - 전이 영역 내 특정 측점에서의 횡단면 기울기.
    """
    station: float = 0.0
    region_type: TransitionRegionType = TransitionRegionType.NORMAL
    slopes: dict[CrossSegmentType, float] = field(default_factory=dict)

    def __post_init__(self):
        if not math.isfinite(self.station):
            raise ValueError(f"station이 유한하지 않음: {self.station}")

    def get_slope(self, segment_type: CrossSegmentType) -> float | None:
        """특정 세그먼트의 기울기 (없으면 None)."""
        return self.slopes.get(segment_type)

    def with_slope(self, segment_type: CrossSegmentType, slope: float) -> "SuperelevationCriticalStation":
        """기울기 추가/변경한 새 임계 측점."""
        new_slopes = {**self.slopes, segment_type: slope}
        return SuperelevationCriticalStation(
            station=self.station,
            region_type=self.region_type,
            slopes=new_slopes,
        )

    def __repr__(self) -> str:
        return (
            f"CriticalStation(sta={self.station:.3f}, "
            f"region={self.region_type.name}, slopes={len(self.slopes)}개)"
        )