from __future__ import annotations

import math
from typing import TYPE_CHECKING

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.turnout.geometry import TurnoutGeometryCalculator

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.rail.rail_alignment import RailAlignment
    from myalignment.turnout.turnout import Turnout


class TurnoutAlignmentBuilder:
    """턴아웃 곡선 끝점(PC)에 접하는 분기 선형을 생성한다."""

    @classmethod
    def build_branch(
        cls, main_alignment: Alignment, turnout: Turnout, branch_length: float = 200.0,
        *, start_station: float = 0.0,
    ) -> RailAlignment:
        """PC에서 분기 접선 방향으로 지정한 길이의 철도 선형을 만든다."""
        if not math.isfinite(branch_length) or branch_length <= 0 or not math.isfinite(start_station):
            raise ValueError("branch_length must be positive and both inputs must be finite")
        if not turnout.branch_alignment_name or turnout.branch_alignment_name == main_alignment.name:
            raise ValueError("turnout requires a distinct branch alignment name")
        geometry = TurnoutGeometryCalculator.calculate(main_alignment, turnout, extension=0)
        if not geometry.is_valid:
            raise ValueError(geometry.error_message)

        start = geometry.pc_point
        azimuth = geometry.branch_azimuth
        end = (start.x + branch_length * math.cos(azimuth), start.y + branch_length * math.sin(azimuth))
        return (
            AlignmentBuilder(turnout.branch_alignment_name).with_pi_coords([start, end])
            .with_start_station(start_station).as_rail_alignment(gauge=geometry.gauge).build()
        )
