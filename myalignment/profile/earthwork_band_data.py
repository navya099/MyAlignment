from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

DEPTH_TOLERANCE = 0.001


@dataclass(frozen=True, slots=True)
class EarthworkSample:
    """원시 측점의 계획고, 지반고와 절토·성토 깊이."""

    station: float = 0.0
    fg_elevation: float = 0.0
    eg_elevation: float = 0.0

    @property
    def diff(self) -> float:
        return self.fg_elevation - self.eg_elevation

    @property
    def cut(self) -> float:
        return max(0.0, -self.diff)

    @property
    def fill(self) -> float:
        return max(0.0, self.diff)

    @property
    def area_type(self) -> str:
        if self.cut > DEPTH_TOLERANCE:
            return "cut"
        if self.fill > DEPTH_TOLERANCE:
            return "fill"
        return "none"


@dataclass(frozen=True, slots=True)
class EarthworkBandData:
    """밴드 샘플과 일정 폭으로 환산한 절토·성토 추정 체적."""

    samples: tuple[EarthworkSample, ...] = ()
    total_cut_volume: float = 0.0
    total_fill_volume: float = 0.0

    def __len__(self) -> int:
        return len(self.samples)

    def __iter__(self) -> Iterator[EarthworkSample]:
        return iter(self.samples)

    @property
    def net_volume(self) -> float:
        """순 체적을 성토량에서 절토량을 뺀 값으로 반환한다."""
        return self.total_fill_volume - self.total_cut_volume

    def station_range(self) -> tuple[float, float]:
        if not self.samples:
            return 0.0, 0.0
        return self.samples[0].station, self.samples[-1].station
