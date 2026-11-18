# grading/site.py
from __future__ import annotations
from dataclasses import dataclass, field, replace
import math

from myalignment.grading.grading_group import GradingGroup


@dataclass(frozen=True, slots=True)
class Site:
    """
    부지 (불변).

    C3D의 Site와 호환.
    - Alignment와 독립적으로 지형을 관리.
    - 여러 Grading Group 소유.
    """
    name: str = "Site1"
    grading_groups: tuple[GradingGroup, ...] = field(default_factory=tuple)
    metadata: dict = field(default_factory=dict)

    # ---- 조회 ----
    def group_by_name(self, name: str) -> GradingGroup | None:
        for g in self.grading_groups:
            if g.name == name:
                return g
        return None

    @property
    def total_daylight_length(self) -> float:
        """전체 자연 지표선 총 길이."""
        return sum(g.total_daylight_length for g in self.grading_groups)

    # ---- 불변 변환 ----
    def add_group(self, group: GradingGroup) -> "Site":
        return replace(
            self,
            grading_groups=self.grading_groups + (group,),
        )

    def with_name(self, name: str) -> "Site":
        return replace(self, name=name)


# ================================================================
# 빌더
# ================================================================
class SiteBuilder:
    """Site 선언적 빌더."""

    def __init__(self, name: str = "Site1"):
        self._name = name
        self._groups: list[GradingGroup] = []

    def add_grading_group(self, group: GradingGroup) -> "SiteBuilder":
        self._groups.append(group)
        return self

    def build(self) -> Site:
        return Site(
            name=self._name,
            grading_groups=tuple(self._groups),
        )


class GradingGroupBuilder:
    """GradingGroup 선언적 빌더."""

    def __init__(self, name: str = "GradingGroup1"):
        self._name = name
        self._gradings: list[Grading] = []

    def add_grading(self, grading: Grading) -> "GradingGroupBuilder":
        self._gradings.append(grading)
        return self

    def build(self) -> GradingGroup:
        return GradingGroup(
            name=self._name,
            gradings=tuple(self._gradings),
        )