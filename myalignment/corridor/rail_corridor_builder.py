from __future__ import annotations

from myalignment.alignment.alignment import Alignment
from myalignment.assembly.assembly import Assembly
from myalignment.cant.curve import CantCurve
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.target.mapping import TargetMapping


class RailCorridorBuilder(CorridorBuilder):
    """철도 기준선과 캔트가 적용되는 코리더 영역을 구성한다."""

    def __init__(self, name: str = "RailCorridor"):
        super().__init__(name)

    def add_rail_baseline(
        self,
        alignment: Alignment,
        profile_name: str,
        start_station: float,
        end_station: float,
    ) -> RailCorridorBuilder:
        if not getattr(alignment, "is_rail", False):
            raise ValueError(f"'{alignment.name}'은 Rail Alignment가 아닙니다.")
        self.add_baseline(
            alignment.name, alignment.name, profile_name, start_station, end_station
        )
        return self

    def add_rail_region(
        self,
        name: str,
        start_station: float,
        end_station: float,
        assembly: Assembly,
        cant_curve: CantCurve | None = None,
        frequency: float = 5.0,
        targets: TargetMapping | None = None,
        *,
        baseline_name: str | None = None,
    ) -> RailCorridorBuilder:
        self.add_region_with_assembly(
            name, start_station, end_station, assembly, frequency, targets,
            cant_curve=cant_curve, baseline_name=baseline_name,
        )
        return self
