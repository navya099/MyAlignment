# corridor/corridor_builder.py
from __future__ import annotations

import math
from typing import TYPE_CHECKING, Self

from myalignment.assembly.assembly import Assembly
from myalignment.cant.curve import CantCurve
from myalignment.corridor.baseline import CorridorBaseline
from myalignment.corridor.corridor import Corridor
from myalignment.corridor.region import CorridorRegion
from myalignment.target.mapping import TargetMapping

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.profile.profile import Profile


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
            *,
            cant_curve: CantCurve | None = None,
        baseline_name: str | None = None,
    ) -> "CorridorBuilder":
        self._regions.append(
            CorridorRegion(
                name=name,
                start_station=start_station,
                end_station=end_station,
                assembly=assembly,
                frequency=frequency,
                target_mapping=targets or TargetMapping.empty(),
                cant_curve=cant_curve,
                baseline_name=baseline_name,
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

    def add_baseline_from_alignment(
        self,
        alignment: Alignment,
        profile: Profile | None = None,
        *,
        name: str | None = None,
        start_station: float | None = None,
        end_station: float | None = None,
    ) -> Self:
        """선형과 선택한 종단에서 기준선 이름과 원시 측점 범위를 정한다.

        범위를 생략하면 선형 전체를 사용한다. 종단이 주어지면 종단이
        기준선 범위를 포함해야 한다. 표면 추출에는 선형 매핑을 전달하고,
        선형에 연결하지 않은 종단은 종단 매핑으로 전달한다.
        """
        baseline_name = alignment.name if name is None else name
        if not baseline_name or not alignment.name or not alignment.is_valid:
            raise ValueError("유효한 선형과 기준선 이름이 필요합니다.")
        if any(baseline.name == baseline_name for baseline in self._baselines):
            raise ValueError(f"기준선 이름이 이미 사용 중입니다: {baseline_name!r}")

        start = alignment.start_station if start_station is None else start_station
        end = alignment.end_station if end_station is None else end_station
        if not (
            math.isfinite(start) and math.isfinite(end)
            and alignment.start_station <= start <= end <= alignment.end_station
        ):
            raise ValueError(f"{baseline_name!r}: 선형의 측점 범위를 확인하세요.")

        if profile is not None:
            if not profile.name or not profile.is_valid or not (
                profile.start_station <= start <= end <= profile.end_station
            ):
                raise ValueError(f"{baseline_name!r}: 종단 이름과 측점 범위를 확인하세요.")
            if any(candidate.name == profile.name and candidate != profile for candidate in alignment.profiles):
                raise ValueError(f"{baseline_name!r}: 같은 이름으로 연결된 다른 종단이 있습니다.")

        self.add_baseline(baseline_name, alignment.name, profile.name if profile is not None else "", start, end)
        return self

    def add_region(
        self,
        name: str,
        start_station: float,
        end_station: float,
        assembly,
        frequency: float = 10.0,
        *,
        baseline_name: str | None = None,
    ) -> "CorridorBuilder":
        return self.add_region_with_assembly(
            name, start_station, end_station, assembly, frequency,
            baseline_name=baseline_name,
        )

    def build(self) -> Corridor:
        sorted_regions = sorted(self._regions, key=lambda r: r.start_station)
        return Corridor(
            name=self._name,
            baselines=tuple(self._baselines),
            regions=tuple(sorted_regions),
        )
