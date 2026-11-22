from bisect import bisect_left
from dataclasses import dataclass, field

from myalignment.enitity.entity_collection import AlignmentEntityCollection
from myalignment.geometry.spiral_geometry import SpiralGeometry


@dataclass(frozen=True, slots=True)
class OffsetStationMap:
    """원본 기하와 평행 기하의 대응 측점."""

    source: AlignmentEntityCollection
    target: AlignmentEntityCollection
    _source_ends: tuple[float, ...] = field(init=False, repr=False)
    _target_ends: tuple[float, ...] = field(init=False, repr=False)

    def __post_init__(self):
        if len(self.source) != len(self.target):
            raise ValueError("원본과 오프셋의 요소 개수가 일치해야 합니다.")
        object.__setattr__(self, "_source_ends", tuple(e.end_station for e in self.source))
        object.__setattr__(self, "_target_ends", tuple(e.end_station for e in self.target))

    def forward(self, station: float) -> float:
        return self._map(station, self.source, self.target, self._source_ends)

    def backward(self, station: float) -> float:
        return self._map(station, self.target, self.source, self._target_ends)

    def inverse_rate(self, station: float, *, outgoing: bool) -> float:
        """오프셋 측점에서 원본 측점으로의 변화율."""
        if station < self.target.start_station or station > self.target.end_station:
            return 1.0
        index = min(bisect_left(self._target_ends, station), len(self.target) - 1)
        if outgoing and index + 1 < len(self.target) and station == self._target_ends[index]:
            index += 1
        source, target = self.source[index], self.target[index]
        local = max(0.0, min(target.length, station - target.start_station))
        if not isinstance(target.geometry, SpiralGeometry):
            return source.length / target.length if target.length else 1.0
        h = min(1e-3, target.length / 100)
        start, end = max(0.0, local - h), min(target.length, local + h)
        a = self._local_station(start, target, source)
        b = self._local_station(end, target, source)
        return (b - a) / (end - start)

    @staticmethod
    def _map(station, source, target, ends):
        if station <= source.start_station:
            return target.start_station + (station - source.start_station)
        if station >= source.end_station:
            return target.end_station + (station - source.end_station)
        index = bisect_left(ends, station)
        a, b = source[index], target[index]
        if station == a.end_station:
            return b.end_station
        return b.start_station + OffsetStationMap._local_station(station - a.start_station, a, b)

    @staticmethod
    def _local_station(station, source, target):
        if isinstance(source.geometry, SpiralGeometry):
            return target.geometry._offset_station(source.geometry._base_station(station))
        return station * (target.length / source.length)
