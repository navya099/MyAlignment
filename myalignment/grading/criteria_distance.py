# grading/criteria_distance.py
from __future__ import annotations
from dataclasses import dataclass
import math

from cadgeom import Point2d

from myalignment.grading.criteria import GradingCriteria, DaylightResult


@dataclass(frozen=True, slots=True)
class SlopeToDistance(GradingCriteria):
    """
    특정 거리까지 경사 투영 (C3D Slope to Distance).
    """
    target_distance: float = 0.0

    def __post_init__(self):
        GradingCriteria.__post_init__(self)
        if self.target_distance <= 0:
            raise ValueError(f"target_distance > 0 필요: {self.target_distance}")

    def compute_daylight(self, footprint_point, footprint_elevation, direction, target_context):
        dx = math.cos(direction)
        dy = math.sin(direction)
        # 내리막 기준 표고 변화
        delta_elev = -self.target_distance / self.slope.ratio

        return DaylightResult(
            point=Point2d(
                footprint_point.x + dx * self.target_distance,
                footprint_point.y + dy * self.target_distance,
            ),
            elevation=footprint_elevation + delta_elev,
            distance=self.target_distance,
        )