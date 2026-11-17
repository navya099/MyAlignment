# corridor/corridor_builder.py
from __future__ import annotations

from myalignment.corridor.baseline import CorridorBaseline
from myalignment.corridor.corridor import Corridor
from myalignment.corridor.region import CorridorRegion


class CorridorBuilder:
    """Corridor 선언적 빌더."""
    def __init__(self, name: str = "Corridor1"):
        self._name = name
        self._baselines: list[CorridorBaseline] = []
        self._regions: list[CorridorRegion] = []

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
        assembly_name: str,
        frequency: float = 10.0,
    ) -> "CorridorBuilder":
        self._regions.append(
            CorridorRegion(
                name=name,
                start_station=start_station,
                end_station=end_station,
                assembly_name=assembly_name,
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