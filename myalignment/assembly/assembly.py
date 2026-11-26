# assembly/assembly.py
from __future__ import annotations
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from myalignment.assembly.codes import PointCode
from myalignment.assembly.link import AssemblyLink
from myalignment.assembly.point import AssemblyPoint
from myalignment.assembly.subassembly import Subassembly
from myalignment.target.mapping import TargetMapping

if TYPE_CHECKING:
    from myalignment.assembly.conditional.conditional_subassembly import ConditionalSubassembly
    from myalignment.assembly.section_context import SectionContext


@dataclass(frozen=True, slots=True)
class Assembly:
    """
    어셈블리 — 횡단면 템플릿 (불변).

    C3D의 Assembly와 호환.
    - 기준점(centerline)에서 좌/우로 서브어셈블리 배치.
    - 최종 접점/링크/형상 반환.
    """
    name: str = "Assembly1"
    left_subassemblies: tuple[Subassembly, ...] = field(default_factory=tuple)
    right_subassemblies: tuple[Subassembly, ...] = field(default_factory=tuple)

    center_subassembly: Subassembly | None = None

    @property
    def has_conditional(self) -> bool:
        """조건부 배치가 있는지 확인한다."""
        from myalignment.assembly.conditional.conditional_subassembly import ConditionalSubassembly

        return any(isinstance(sub, ConditionalSubassembly) for sub in (
            self.center_subassembly, *self.left_subassemblies, *self.right_subassemblies,
        ))

    @property
    def uses_section_context(self) -> bool:
        """측점별 횡단값을 참조하는 서브어셈블리가 있는지 확인한다."""
        return any(sub.uses_section_context for sub in (
            self.center_subassembly, *self.left_subassemblies, *self.right_subassemblies,
        ) if sub is not None)

    @property
    def has_station_binding(self) -> bool:
        return any(sub.has_station_binding for sub in (
            self.center_subassembly, *self.left_subassemblies, *self.right_subassemblies,
        ) if sub is not None)

    def generate_cross_section(
            self,
            target_mapping: TargetMapping | None = None, *,
            context: SectionContext | None = None,
            ) -> tuple[tuple[AssemblyPoint, ...], tuple[AssemblyLink, ...]]:
        """
        어셈블리 전체의 횡단면 생성 (로컬 좌표).

        Returns:
            (points, links) — 기준점 원점 기준.
        """
        all_points: list[AssemblyPoint] = []
        all_links: list[AssemblyLink] = []

        # 기준점 (centerline)
        center = AssemblyPoint(code=PointCode.CENTERLINE, x=0.0, z=0.0)
        all_points.append(center)

        left_origin = right_origin = (0.0, 0.0)
        if self.center_subassembly is not None:
            points, links = self.center_subassembly._place_with_context(
                0.0, 0.0, 1, target_mapping, context
            )
            for point in points:
                if not self._point_exists(all_points, point):
                    all_points.append(point)
            all_links.extend(links)
            if points:
                left = min(points, key=lambda p: p.x)
                right = max(points, key=lambda p: p.x)
                left_origin = (left.x, left.z)
                right_origin = (right.x, right.z)

        # 우측 배치 (side=+1)
        self._place_side(
            subassemblies=self.right_subassemblies,
            side_sign=+1,
            origin=right_origin,
            points=all_points,
            links=all_links,
            target_mapping=target_mapping,
            context=context,
        )

        # 좌측 배치 (side=-1)
        self._place_side(
            subassemblies=self.left_subassemblies,
            side_sign=-1,
            origin=left_origin,
            points=all_points,
            links=all_links,
            target_mapping=target_mapping,
            context=context,
        )

        return tuple(all_points), tuple(all_links)

    def _place_side(
            self,
            subassemblies: tuple[Subassembly, ...],
            side_sign: int,
            origin: tuple[float, float],
            points: list,
            links: list,
            target_mapping: TargetMapping | None,
            context: SectionContext | None,
    ):
        current_x, current_z = origin

        for sub in subassemblies:
            placed_points, placed_links = sub._place_with_context(
                current_x, current_z, side_sign, target_mapping, context,
            )

            for p in placed_points:
                if not self._point_exists(points, p):
                    points.append(p)

            links.extend(placed_links)

            if placed_points:
                # side_sign 방향으로 가장 먼 점
                if side_sign > 0:
                    last = max(placed_points, key=lambda p: p.x)
                else:
                    last = min(placed_points, key=lambda p: p.x)
                current_x = last.x
                current_z = last.z

    @staticmethod
    def _point_exists(points, p) -> bool:
        for existing in points:
            if abs(existing.x - p.x) < 1e-9 and abs(existing.z - p.z) < 1e-9:
                return True
        return False


# ================================================================
# 빌더
# ================================================================
class AssemblyBuilder:
    """Assembly 선언적 빌더."""

    def __init__(self, name: str = "Assembly1"):
        self._name = name
        self._left: list[Subassembly] = []
        self._center: Subassembly | None = None
        self._right: list[Subassembly] = []

    def add_center(self, sub: Subassembly) -> "AssemblyBuilder":
        """양쪽에 걸친 서브어셈블리를 기준점에 한 번 배치."""
        if self._center is not None:
            raise ValueError("중심 서브어셈블리는 하나만 배치할 수 있습니다")
        self._center = sub
        return self

    def add_right(self, sub: Subassembly) -> "AssemblyBuilder":
        self._right.append(sub)
        return self

    def add_left(self, sub: Subassembly) -> "AssemblyBuilder":
        self._left.append(sub)
        return self

    def add_both(self, sub_factory) -> "AssemblyBuilder":
        """좌/우 대칭 서브어셈블리 추가 (factory 함수)."""
        self._right.append(sub_factory(side=+1))
        self._left.append(sub_factory(side=-1))
        return self

    def add_conditional(self, side: str, conditional: ConditionalSubassembly) -> AssemblyBuilder:
        """조건부 서브어셈블리를 좌측, 우측 또는 양쪽에 추가한다."""
        from myalignment.assembly.conditional.conditional_subassembly import ConditionalSubassembly

        if side not in ("left", "right", "both"):
            raise ValueError("side must be left, right, or both")
        if not isinstance(conditional, ConditionalSubassembly):
            raise TypeError("conditional must be a ConditionalSubassembly")
        if side in ("left", "both"):
            self.add_left(replace(conditional, side=-1))
        if side in ("right", "both"):
            self.add_right(replace(conditional, side=1))
        return self

    def build(self) -> Assembly:
        return Assembly(
            name=self._name,
            center_subassembly=self._center,
            left_subassemblies=tuple(self._left),
            right_subassemblies=tuple(self._right),
        )