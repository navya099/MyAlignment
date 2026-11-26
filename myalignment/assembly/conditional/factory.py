from __future__ import annotations

from dataclasses import dataclass
import math

from myalignment.assembly.assembly import Assembly, AssemblyBuilder
from myalignment.assembly.conditional.builder import ConditionalSubassemblyBuilder
from myalignment.assembly.conditional.condition import Condition
from myalignment.assembly.conditional.condition_type import ConditionType
from myalignment.assembly.conditional.conditional_subassembly import ConditionalSubassembly
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.assembly.subassemblies.ditch import VShapeDitch
from myalignment.assembly.subassemblies.side_slope import SideSlope
from myalignment.assembly.subassembly import Subassembly


def _validate_dimensions(*values):
    if any(not math.isfinite(value) or value <= 0 for value in values):
        raise ValueError("assembly dimensions must be finite and positive")


@dataclass(frozen=True, slots=True)
class _CutDitchSlope(Subassembly):
    name: str = "CutDitchSlope"
    ditch: VShapeDitch = VShapeDitch()
    slope: SideSlope = SideSlope(is_cut=True)

    @property
    def target_parameters(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((*self.ditch.target_parameters, *self.slope.target_parameters)))

    def generate_geometry(self, target_mapping=None):
        ditch_points, ditch_links = self.ditch.generate_geometry(target_mapping)
        end = ditch_points[-1]
        slope_points, slope_links = self.slope.place_at(end.x, end.z, 1, target_mapping)
        return ditch_points + slope_points, ditch_links + slope_links


class ConditionalAssemblyFactory:
    """도로 절토·성토 및 배수 조건을 위한 어셈블리를 만든다."""

    @classmethod
    def road_with_cut_fill(
        cls, lane_width: float = 3.5, fill_slope_ratio: float = 1.5,
        cut_slope_ratio: float = 1.2, cut_ditch_width: float = 1.5,
    ) -> Assembly:
        """절토는 배수로와 상향 사면, 성토는 하향 사면을 배치한다."""
        _validate_dimensions(lane_width, fill_slope_ratio, cut_slope_ratio, cut_ditch_width)
        fill = SideSlope(slope_ratio=fill_slope_ratio, name="FillSlope")
        cut = _CutDitchSlope(
            ditch=VShapeDitch(width=cut_ditch_width, name="CutDitch"),
            slope=SideSlope(slope_ratio=cut_slope_ratio, name="CutSlope", is_cut=True),
        )
        conditional = ConditionalSubassembly.cut_fill(fill, cut)
        return (
            AssemblyBuilder("성토절토단면")
            .add_both(lambda side: BasicLane(width=lane_width, side=side))
            .add_conditional("both", conditional)
            .build()
        )

    @classmethod
    def road_with_drainage(
        cls, lane_width: float = 3.5, ditch_width: float = 1.5, ditch_depth: float = 0.5,
    ) -> Assembly:
        """종단 구배의 절댓값이 2%를 넘을 때 배수로를 배치한다."""
        _validate_dimensions(lane_width, ditch_width, ditch_depth)
        conditional = (
            ConditionalSubassemblyBuilder("Drainage")
            .add_branch(Condition(ConditionType.GRADE_THRESHOLD, 0.02, context_key="absolute_grade"),
                        VShapeDitch(width=ditch_width, depth=ditch_depth))
            .else_(BasicLane(width=1.0, slope=0.0, name="Flat"))
            .build()
        )
        return (
            AssemblyBuilder("배수조건단면")
            .add_both(lambda side: BasicLane(width=lane_width, side=side))
            .add_conditional("both", conditional)
            .build()
        )
