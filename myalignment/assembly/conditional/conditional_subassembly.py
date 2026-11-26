from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import TYPE_CHECKING

from myalignment.assembly.conditional.branch import ConditionalBranch
from myalignment.assembly.conditional.condition import Condition
from myalignment.assembly.conditional.condition_type import ConditionType
from myalignment.assembly.parameter.parameterized import ParameterizedSubassembly
from myalignment.assembly.subassembly import Subassembly
from myalignment.target.target_type import TargetType

if TYPE_CHECKING:
    from myalignment.assembly.section_context import SectionContext
    from myalignment.target.mapping import TargetMapping


@dataclass(frozen=True, slots=True)
class ConditionalSubassembly(Subassembly):
    """현재 접점에서 처음 충족하는 분기의 형상을 배치한다."""

    uses_section_context = True

    name: str = "Conditional"
    branches: tuple[ConditionalBranch, ...] = ()
    surface_elevation: float | None = None
    base_elevation: float = 0.0
    surface_target_name: str = "TargetDTM"
    horizontal_target_name: str = "TargetOffset"

    def __post_init__(self):
        object.__setattr__(self, "branches", tuple(self.branches))
        if not self.branches or not self.branches[-1].is_else or any(b.is_else for b in self.branches[:-1]):
            raise ValueError("A single else branch is required at the end")
        if self.side not in (-1, 0, 1):
            raise ValueError("side must be -1, 0 or 1")
        if not math.isfinite(self.base_elevation) or (
            self.surface_elevation is not None and not math.isfinite(self.surface_elevation)
        ):
            raise ValueError("elevations must be finite")

    @property
    def has_station_binding(self) -> bool:
        return any(branch.subassembly.has_station_binding for branch in self.branches)

    @property
    def target_parameters(self) -> tuple[str, ...]:
        """분기 서브어셈블리의 타깃과 조건부 타깃 이름을 반환한다."""
        return tuple(dict.fromkeys((
            *self._target_parameters, self.surface_target_name, self.horizontal_target_name,
            *(name for branch in self.branches for name in branch.subassembly.target_parameters),
        )))

    def generate_geometry(self, target_mapping: TargetMapping | None = None, *, context: SectionContext | None = None):
        """원점에서 분기를 평가해 로컬 형상을 반환한다."""
        branch = self.selected_branch(target_mapping, context=context)
        subassembly = branch.subassembly
        if isinstance(subassembly, ConditionalSubassembly):
            return subassembly.generate_geometry(target_mapping, context=context)
        if isinstance(subassembly, ParameterizedSubassembly):
            return subassembly._geometry_at(
                subassembly.evaluated_parameters(context), target_mapping, context, 0.0, 0.0, subassembly.side or 1,
            )
        return subassembly.generate_geometry(target_mapping)

    def place_at(
        self, origin_x: float, origin_z: float, side_sign: int | None = None,
        target_mapping: TargetMapping | None = None, *, context: SectionContext | None = None,
    ):
        """현재 접점에서 선택한 분기를 같은 위치와 방향으로 배치한다."""
        sign = side_sign if side_sign is not None else self.side or 1
        branch = self.selected_branch(
            target_mapping, context=context, origin_x=origin_x, origin_z=origin_z, side_sign=sign,
        )
        return branch.subassembly._place_with_context(origin_x, origin_z, sign, target_mapping, context)

    def _place_with_context(self, origin_x, origin_z, side_sign, target_mapping, context):
        return self.place_at(origin_x, origin_z, side_sign, target_mapping, context=context)

    def selected_branch(
        self, target_mapping: TargetMapping | None = None, *, context: SectionContext | None = None,
        origin_x: float = 0.0, origin_z: float = 0.0, side_sign: int | None = None,
    ) -> ConditionalBranch:
        """주어진 배치 위치에서 선택되는 분기를 반환한다."""
        values = self._build_context(target_mapping, context, origin_x, origin_z, side_sign)
        return next(branch for branch in self.branches if branch.matches(values))

    def _build_context(self, mapping, context, offset, elevation, side):
        base = context.base_elevation if context is not None else None
        design = (self.base_elevation if base is None else base) + elevation
        surface = self.surface_elevation
        target_offset = None
        grade = context.grade if context is not None else None
        sign = side if side is not None else self.side or 1
        if context is not None and mapping is not None:
            terrain = mapping.get(self.surface_target_name)
            if terrain is not None and terrain.target_type is TargetType.SURFACE and context.surface_elevation_at is not None:
                sampled = context.surface_elevation_at(terrain.object_name, offset)
                if sampled is not None and math.isfinite(sampled):
                    surface = sampled
            horizontal = mapping.get(self.horizontal_target_name)
            if horizontal is not None and horizontal.target_type is TargetType.OFFSET:
                target_offset = context.target_offsets.get(horizontal.object_name)
        difference = surface - design if surface is not None else None
        return {
            **(context.values if context is not None else {}),
            "station": context.station if context is not None else None,
            "surface_elevation": surface, "base_elevation": design, "current_elevation": design,
            "elevation_diff": difference, "absolute_elevation_diff": abs(difference) if difference is not None else None,
            "offset": offset, "grade": grade, "absolute_grade": abs(grade) if grade is not None else None,
            "target_offset": target_offset,
            "target_reached": (sign * target_offset >= 0 and sign * (offset - target_offset) >= -1e-6
                               if target_offset is not None else None),
        }

    def with_surface_elevation(self, elev: float) -> ConditionalSubassembly:
        """외부 표고가 없을 때 사용할 표고를 설정한다."""
        return replace(self, surface_elevation=elev)

    @classmethod
    def cut_fill(
        cls, fill_subassembly: Subassembly, cut_subassembly: Subassembly, name: str = "CutFill",
    ) -> ConditionalSubassembly:
        """절토와 성토 분기를 만든다. 동일 표고나 표고 미확인은 else를 사용한다."""
        return cls(name=name, branches=(
            ConditionalBranch(cut_subassembly, Condition.cut_fill_condition(), "Cut"),
            ConditionalBranch(fill_subassembly, name="Fill"),
        ))

    @classmethod
    def slope_to_surface(
        cls, slope_subassembly: Subassembly, flat_subassembly: Subassembly, threshold: float = 0.5,
    ) -> ConditionalSubassembly:
        """접점과 지표면의 표고차 크기로 사면 또는 평탄 분기를 선택한다."""
        if threshold < 0:
            raise ValueError("threshold must be nonnegative")
        condition = Condition(ConditionType.SURFACE_ELEVATION, threshold, context_key="absolute_elevation_diff")
        return cls(name="SlopeToSurface", branches=(
            ConditionalBranch(slope_subassembly, condition, "Slope"),
            ConditionalBranch(flat_subassembly, name="Flat"),
        ))
