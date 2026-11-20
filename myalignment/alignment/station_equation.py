from dataclasses import dataclass
import math

from myalignment.alignment.station_equation_type import StationEquationType


@dataclass(frozen=True, slots=True)
class StationEquation:
    """원시 측점에서 시작하는 표시 측점과 진행 방향."""

    raw_station_back: float = 0.0
    station_ahead: float = 0.0
    equation_type: StationEquationType = StationEquationType.INCREASING
    comment: str = ""

    def __post_init__(self):
        if not math.isfinite(self.raw_station_back):
            raise ValueError("raw_station_back must be finite")
        if not math.isfinite(self.station_ahead):
            raise ValueError("station_ahead must be finite")
        if not isinstance(self.equation_type, StationEquationType):
            raise ValueError("invalid station equation type")

    @property
    def delta(self) -> float:
        return self.station_ahead - self.raw_station_back

    def __repr__(self) -> str:
        return (
            f"StationEquation(Raw={self.raw_station_back:.2f}, "
            f"Ahead={self.station_ahead:.2f}, {self.equation_type.value})"
        )
