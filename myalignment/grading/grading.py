# grading/grading.py
from __future__ import annotations
from dataclasses import dataclass, field
import math

from myalignment.grading.criteria import GradingCriteria, DaylightResult
from myalignment.grading.footprint import Footprint
from myalignment.grading.target_context import TargetContext


@dataclass(frozen=True, slots=True)
class Grading:
    """
    개별 그레이딩 (불변).

    C3D의 Grading과 호환.
    - 발자국(footprint) + 경사기준(criteria) + 목표(target) → 자연 지표선.
    """
    name: str = ""
    footprint: Footprint = None
    criteria: GradingCriteria = None
    target_context: TargetContext = field(default_factory=TargetContext)

    def __post_init__(self):
        if self.footprint is None:
            raise ValueError("footprint가 None입니다.")
        if self.criteria is None:
            raise ValueError("criteria가 None입니다.")

    def compute_daylight_lines(self):
        results = []
        directions = self.footprint.vertex_outward_normals()  # ← 정점별
        for i, vertex in enumerate(self.footprint.vertices):
            result = self.criteria.compute_daylight(
                footprint_point=vertex.point_2d,
                footprint_elevation=vertex.elevation,
                direction=directions[i],
                target_context=self.target_context,
            )
            if result is not None:
                results.append(result)
        return tuple(results)