# corridor/baseline.py
from __future__ import annotations
from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class CorridorBaseline:
    """
    코리더 기준선 (불변).

    Alignment + Profile 조합.
    """
    name: str = ""
    alignment_name: str = ""
    profile_name: str = ""
    start_station: float = 0.0
    end_station: float = 0.0

    def __post_init__(self):
        if self.end_station < self.start_station:
            raise ValueError(f"end < start: {self.end_station} < {self.start_station}")

    @property
    def length(self) -> float:
        return self.end_station - self.start_station