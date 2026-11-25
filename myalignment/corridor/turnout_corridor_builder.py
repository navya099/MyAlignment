from __future__ import annotations

import math
from typing import TYPE_CHECKING

from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.turnout.geometry import TurnoutGeometryCalculator

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.assembly.assembly import Assembly
    from myalignment.corridor.corridor import Corridor
    from myalignment.turnout.turnout import Turnout


class TurnoutCorridorBuilder:
    """본선 및 분기선에 명시적인 기준선과 영역을 생성한다."""

    @classmethod
    def build(
        cls,
        main_alignment: Alignment,
        branch_alignment: Alignment,
        turnout: Turnout,
        main_assembly: Assembly,
        branch_assembly: Assembly,
        turnout_length: float = 60.0,
        frequency: float = 5.0,
        *,
        turnout_assembly: Assembly | None = None,
    ) -> Corridor:
        """본선의 PS부터 PF 뒤까지를 턴아웃 영역으로 구분한다.

        turnout_length는 PF 뒤의 표시 구간 길이다. 영역 끝은 본선
        범위에서 잘린다. 별도 단면이 없으면 본선 어셈블리를 유지한다.
        """
        if not math.isfinite(turnout_length) or turnout_length < 0:
            raise ValueError("turnout_length must be finite and nonnegative")
        if (not branch_alignment.name or branch_alignment.name == main_alignment.name
                or branch_alignment.name != turnout.branch_alignment_name):
            raise ValueError("branch alignment must match the turnout branch name")
        geometry = TurnoutGeometryCalculator.calculate(main_alignment, turnout, extension=0)
        if not geometry.is_valid:
            raise ValueError(geometry.error_message)

        builder = CorridorBuilder(f"Turnout Corridor — {turnout.name}")
        builder.add_baseline_from_alignment(main_alignment, main_alignment.fg_profile)
        builder.add_baseline_from_alignment(branch_alignment, branch_alignment.fg_profile)
        ps = geometry.ps_station
        end = min(main_alignment.end_station, geometry.pf_station + turnout_length)
        for name, start, stop, assembly in (
            ("Main before turnout", main_alignment.start_station, ps, main_assembly),
            ("Turnout", ps, end, turnout_assembly if turnout_assembly is not None else main_assembly),
            ("Main after turnout", end, main_alignment.end_station, main_assembly),
        ):
            if start < stop:
                builder.add_region(name, start, stop, assembly, frequency, baseline_name=main_alignment.name)
        builder.add_region(
            "Branch", branch_alignment.start_station, branch_alignment.end_station,
            branch_assembly, frequency, baseline_name=branch_alignment.name,
        )
        return builder.build()
