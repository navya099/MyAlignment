# corridor/region.py
from __future__ import annotations
from dataclasses import dataclass, field
import math


@dataclass(frozen=True, slots=True)
class CorridorRegion:
    """
    코리더 영역 (불변).

    어셈블리가 적용되는 측점 범위.
    """
    name: str = ""
    start_station: float = 0.0
    end_station: float = 0.0
    assembly_name: str = ""
    frequency: float = 10.0  # 측점 간격 (m)

    def __post_init__(self):
        if self.end_station < self.start_station:
            raise ValueError(f"end < start: {self.end_station} < {self.start_station}")
        if self.frequency <= 0:
            raise ValueError(f"frequency > 0 필요: {self.frequency}")

    @property
    def length(self) -> float:
        return self.end_station - self.start_station

    @property
    def station_count(self) -> int:
        """영역 내 샘플 측점 수."""
        return int(self.length / self.frequency) + 1

    def sample_stations(self) -> list[float]:
        """영역 내 샘플 측점 리스트."""
        n = self.station_count
        return [
            self.start_station + self.length * i / (n - 1)
            for i in range(n)
        ] if n > 1 else [self.start_station]