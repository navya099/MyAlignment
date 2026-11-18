# grading/criteria_surface.py
from __future__ import annotations
from dataclasses import dataclass
import math

from cadgeom import Point2d

from myalignment.grading.criteria import (
    GradingCriteria, DaylightResult, ProjectionType, Slope
)


@dataclass(frozen=True, slots=True)
class SlopeToSurface(GradingCriteria):
    """
    지표면까지 경사 투영 (C3D Slope to Surface).
    """

    def compute_daylight(self, footprint_point, footprint_elevation, direction, target_context):
        if target_context.surface is None:
            return None

        dx = math.cos(direction)
        dy = math.sin(direction)
        slope_ratio = self.slope.ratio

        max_dist = 1000.0
        step = 1.0

        prev_diff = None
        for i in range(1, int(max_dist / step) + 1):
            d = i * step
            virtual_elev = footprint_elevation - d / slope_ratio
            px = footprint_point.x + dx * d
            py = footprint_point.y + dy * d
            surface_elev = target_context.surface.elevation_at(px, py)
            diff = virtual_elev - surface_elev

            if prev_diff is not None and prev_diff * diff <= 0:
                # 이분법: prev_diff를 기준으로
                lo, hi = (i - 1) * step, i * step
                for _ in range(30):
                    mid = (lo + hi) / 2
                    v_e = footprint_elevation - mid / slope_ratio
                    mpx = footprint_point.x + dx * mid
                    mpy = footprint_point.y + dy * mid
                    s_e = target_context.surface.elevation_at(mpx, mpy)
                    mid_diff = v_e - s_e
                    if mid_diff * prev_diff <= 0:  # ← prev_diff 사용
                        hi = mid
                    else:
                        lo = mid
                final_d = (lo + hi) / 2
                return DaylightResult(
                    point=Point2d(
                        footprint_point.x + dx * final_d,
                        footprint_point.y + dy * final_d,
                    ),
                    elevation=footprint_elevation - final_d / slope_ratio,
                    distance=final_d,
                )
            prev_diff = diff

        return None