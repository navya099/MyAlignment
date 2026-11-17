# corridor/corridor.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterator

from myalignment.corridor.baseline import CorridorBaseline
from myalignment.corridor.region import CorridorRegion


@dataclass(frozen=True, slots=True)
class Corridor:
    """
    코리더 (불변).

    C3D의 Corridor와 호환.
    - 기준선(Baseline) + 영역(Region) + 어셈블리(Assembly) 조합.
    - 3D 표면/피처라인/수량 산출의 기반.
    """
    name: str = ""
    baselines: tuple[CorridorBaseline, ...] = field(default_factory=tuple)
    regions: tuple[CorridorRegion, ...] = field(default_factory=tuple)

    def __post_init__(self):
        # 영역 정렬 검증
        for i in range(len(self.regions) - 1):
            if self.regions[i].start_station > self.regions[i + 1].start_station:
                raise ValueError(f"영역 순서 오류: [{i}]")

    # ---- 조회 ----
    @property
    def start_station(self) -> float:
        return self.regions[0].start_station if self.regions else 0.0

    @property
    def end_station(self) -> float:
        return self.regions[-1].end_station if self.regions else 0.0

    @property
    def length(self) -> float:
        return self.end_station - self.start_station if self.regions else 0.0

    def region_at(self, station: float) -> CorridorRegion | None:
        """측점이 속한 영역."""
        for r in self.regions:
            if r.start_station <= station <= r.end_station:
                return r
        return None

    def region_by_name(self, name: str) -> CorridorRegion | None:
        for r in self.regions:
            if r.name == name:
                return r
        return None

    def total_surface_area(self) -> float:
        """총 표면적 (근사) — 영역 길이 × 어셈블리 폭."""
        # 실제로는 어셈블리 폭 정보 필요
        return sum(r.length for r in self.regions)

    # ---- 불변 변환 ----
    def add_region(self, region: CorridorRegion) -> "Corridor":
        """새 영역 추가한 새 코리더."""
        new_list = list(self.regions) + [region]
        new_list.sort(key=lambda r: r.start_station)
        return Corridor(
            name=self.name,
            baselines=self.baselines,
            regions=tuple(new_list),
        )

    def __repr__(self) -> str:
        return (
            f"Corridor('{self.name}', "
            f"baselines={len(self.baselines)}, "
            f"regions={len(self.regions)}, "
            f"len={self.length:.1f}m)"
        )