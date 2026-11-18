# grading/grading_group.py
from __future__ import annotations
from dataclasses import dataclass, field
import math

from myalignment.grading.grading import Grading
from myalignment.grading.criteria import DaylightResult


@dataclass(frozen=True, slots=True)
class GradingGroup:
    """
    그레이딩 그룹 (불변).

    C3D의 Grading Group과 호환.
    - 여러 Grading을 묶어 하나의 지표면으로 통합.
    - 토공량(Cut/Fill) 계산 단위.
    """
    name: str = ""
    gradings: tuple[Grading, ...] = field(default_factory=tuple)

    def __post_init__(self):
        if not self.gradings:
            raise ValueError("Grading이 없습니다.")

    @property
    def daylight_lines(self) -> tuple[DaylightResult, ...]:
        """전체 그레이딩의 자연 지표선."""
        result = []
        for g in self.gradings:
            result.extend(g.compute_daylight_lines())
        return tuple(result)

    @property
    def total_daylight_length(self) -> float:
        """
        자연 지표선 총 길이.

        인접 자연 지표선 사이의 거리 합산.
        """
        lines = self.daylight_lines
        if len(lines) < 2:
            return 0.0
        total = 0.0
        for i in range(len(lines) - 1):
            p1 = lines[i].point
            p2 = lines[i + 1].point
            total += math.hypot(p2.x - p1.x, p2.y - p1.y)
        return total

    def add(self, grading: Grading) -> "GradingGroup":
        """새 Grading 추가한 새 그룹."""
        return GradingGroup(
            name=self.name,
            gradings=self.gradings + (grading,),
        )

    def with_name(self, name: str) -> "GradingGroup":
        from dataclasses import replace
        return replace(self, name=name)