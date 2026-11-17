# assembly/assembly.py
from __future__ import annotations
from dataclasses import dataclass, field
import math

from myalignment.assembly.codes import PointCode
from myalignment.assembly.link import AssemblyLink
from myalignment.assembly.point import AssemblyPoint
from myalignment.assembly.subassembly import Subassembly
from myalignment.target.mapping import TargetMapping


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

    def generate_cross_section(
            self,
            target_mapping: TargetMapping | None = None,
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

        # 우측 배치 (side=+1)
        self._place_side(
            subassemblies=self.right_subassemblies,
            side_sign=+1,
            origin=(0.0, 0.0),
            points=all_points,
            links=all_links,
            target_mapping=target_mapping
        )

        # 좌측 배치 (side=-1)
        self._place_side(
            subassemblies=self.left_subassemblies,
            side_sign=-1,
            origin=(0.0, 0.0),
            points=all_points,
            links=all_links,
            target_mapping=target_mapping
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
    ):
        current_x, current_z = origin

        for sub in subassemblies:
            placed_points, placed_links = sub.place_at(
                origin_x=current_x,
                origin_z=current_z,
                side_sign=side_sign,
                target_mapping=target_mapping
            )

            for p in placed_points:
                if not self._point_exists(points, p):
                    points.append(p)

            links.extend(placed_links)

            if placed_points:
                last = placed_points[-1]
                current_x = last.x  # ← 수정: side_sign 곱 제거
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
        self._right: list[Subassembly] = []

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

    def build(self) -> Assembly:
        return Assembly(
            name=self._name,
            left_subassemblies=tuple(self._left),
            right_subassemblies=tuple(self._right),
        )