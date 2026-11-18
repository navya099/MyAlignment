# grading/criteria_elevation.py
from __future__ import annotations
from dataclasses import dataclass
import math

from cadgeom import Point2d

from myalignment.grading.criteria import GradingCriteria, DaylightResult, Slope


@dataclass(frozen=True, slots=True)
class SlopeToElevation(GradingCriteria):
    """
    특정 표고까지 경사 투영 (C3D Slope to Elevation).
    """
    target_elevation: float = 0.0

    def compute_daylight(self, footprint_point, footprint_elevation, direction, target_context):
        delta_elev = abs(self.target_elevation - footprint_elevation)
        if delta_elev < 1e-9:
            return DaylightResult(
                point=footprint_point,
                elevation=footprint_elevation,
                distance=0.0,
            )

        # 수평 거리 = 표고차 × slope_ratio
        distance = delta_elev * self.slope.ratio
        dx = math.cos(direction)
        dy = math.sin(direction)

        return DaylightResult(
            point=Point2d(
                footprint_point.x + dx * distance,
                footprint_point.y + dy * distance,
            ),
            elevation=self.target_elevation,
            distance=distance,
        )