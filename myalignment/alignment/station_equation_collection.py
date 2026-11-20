from __future__ import annotations

from bisect import bisect_right
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
import math

from myalignment.alignment.station_equation import StationEquation
from myalignment.alignment.station_equation_type import StationEquationType


@dataclass(frozen=True, slots=True)
class StationEquationCollection:
    """원시 측점 순으로 정렬된 방정식 집합."""

    equations: tuple[StationEquation, ...] = ()
    _raw_stations: tuple[float, ...] = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        equations = tuple(self.equations)
        stations = tuple(eq.raw_station_back for eq in equations)
        if any(a >= b for a, b in zip(stations, stations[1:])):
            raise ValueError("Station equations must have distinct, increasing raw stations")
        object.__setattr__(self, "equations", equations)
        object.__setattr__(self, "_raw_stations", stations)

    def __len__(self) -> int:
        return len(self.equations)

    def __iter__(self) -> Iterator[StationEquation]:
        return iter(self.equations)

    def get_at_raw(self, raw_station: float, tol: float = 1e-6) -> StationEquation | None:
        return next((eq for eq in self if abs(eq.raw_station_back - raw_station) < tol), None)

    def equations_after(self, raw_station: float) -> tuple[StationEquation, ...]:
        return self.equations[bisect_right(self._raw_stations, raw_station):]

    def add(self, equation: StationEquation) -> StationEquationCollection:
        equations = sorted((*self.equations, equation), key=lambda eq: eq.raw_station_back)
        return replace(self, equations=tuple(equations))

    def remove_at_raw(self, raw_station: float, tol: float = 1e-6) -> StationEquationCollection:
        return replace(self, equations=tuple(eq for eq in self if abs(eq.raw_station_back - raw_station) >= tol))

    def remove_at_index(self, index: int) -> StationEquationCollection:
        if not 0 <= index < len(self):
            raise IndexError(f"방정식 인덱스 범위 초과: {index}")
        return replace(self, equations=self.equations[:index] + self.equations[index + 1:])

    def raw_to_display(self, station: float) -> float:
        if not math.isfinite(station):
            raise ValueError("raw station must be finite")
        index = bisect_right(self._raw_stations, station)
        if index == 0:
            return station
        eq = self.equations[index - 1]
        return eq.station_ahead + eq.equation_type.sign * (station - eq.raw_station_back)

    def display_to_raw(
        self, station: float, start: float = -math.inf, end: float = math.inf,
    ) -> tuple[float, ...]:
        """표시 측점에 대응하는 원시 측점 후보를 진행 순서대로 반환한다."""
        if not math.isfinite(station):
            raise ValueError("display station must be finite")
        upper_limits = (*self._raw_stations, math.inf)
        candidates = []
        if start <= station <= end and station < upper_limits[0]:
            candidates.append(station)
        for eq, upper in zip(self, upper_limits[1:]):
            raw = eq.raw_station_back + eq.equation_type.sign * (station - eq.station_ahead)
            if start <= raw <= end and eq.raw_station_back <= raw < upper:
                candidates.append(raw)
        return tuple(candidates)

    def reversed(self, start: float, end: float) -> StationEquationCollection:
        """역방향 원시 측점에 표시 구간을 재배치한다. 경계에서는 새 진행 방향의 값을 사용한다."""
        if not self or end <= start:
            return self
        segments = []
        previous = None
        for eq in self:
            if start < eq.raw_station_back < end:
                segments.append((eq.raw_station_back, previous, eq.comment))
            if eq.raw_station_back >= end:
                break
            previous = eq
        segments.append((end, previous, previous.comment if previous else ""))

        equations = []
        for raw, active, comment in reversed(segments):
            display = raw
            direction = StationEquationType.DECREASING
            if active is not None:
                display = active.station_ahead + active.equation_type.sign * (raw - active.raw_station_back)
                if active.equation_type is StationEquationType.DECREASING:
                    direction = StationEquationType.INCREASING
            equations.append(StationEquation(start + (end - raw), display, direction, comment))
        return StationEquationCollection(tuple(equations))

    def __repr__(self) -> str:
        return f"StationEquationCollection(n={len(self)})"
