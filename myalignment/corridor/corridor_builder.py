# corridor/corridor_builder.py
from __future__ import annotations

from myalignment.assembly.assembly import Assembly
from myalignment.corridor.baseline import CorridorBaseline
from myalignment.corridor.corridor import Corridor
from myalignment.corridor.region import CorridorRegion
from myalignment.target.mapping import TargetMapping


class CorridorBuilder:
    """Corridor 선언적 빌더."""
    def __init__(self, name: str = "Corridor1"):
        self._name = name
        self._baselines: list[CorridorBaseline] = []
        self._regions: list[CorridorRegion] = []

    def add_region_with_assembly(
            self,
            name: str,
            start_station: float,
            end_station: float,
            assembly: Assembly,
            frequency: float = 10.0,
            targets: TargetMapping | None = None,
    ) -> "CorridorBuilder":
        self._regions.append(
            CorridorRegion(
                name=name,
                start_station=start_station,
                end_station=end_station,
                assembly=assembly,
                frequency=frequency,
                target_mapping=targets or TargetMapping.empty(),
            )
        )
        return self

    def add_baseline(
        self,
        name: str,
        alignment_name: str,
        profile_name: str,
        start_station: float,
        end_station: float,
    ) -> "CorridorBuilder":
        self._baselines.append(
            CorridorBaseline(
                name=name,
                alignment_name=alignment_name,
                profile_name=profile_name,
                start_station=start_station,
                end_station=end_station,
            )
        )
        return self

    def add_region(
        self,
        name: str,
        start_station: float,
        end_station: float,
        assembly,
        frequency: float = 10.0,
    ) -> "CorridorBuilder":
        self._regions.append(
            CorridorRegion(
                name=name,
                start_station=start_station,
                end_station=end_station,
                assembly=assembly,
                frequency=frequency,
            )
        )
        return self

    def build(self) -> Corridor:
        sorted_regions = sorted(self._regions, key=lambda r: r.start_station)
        return Corridor(
            name=self._name,
            baselines=tuple(self._baselines),
            regions=tuple(sorted_regions),
        )