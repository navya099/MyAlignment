from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Protocol

from myalignment.enitity.entity_collection import AlignmentEntityCollection


class StationMap(Protocol):
    def forward(self, station: float) -> float: ...
    def backward(self, station: float) -> float: ...
    def inverse_rate(self, station: float, *, outgoing: bool) -> float: ...


@dataclass(frozen=True, slots=True)
class EditStationMap:
    """편집 전후 대응 요소의 경계 사이에서 측점을 선형 보간한다."""

    source: tuple[float, ...]
    target: tuple[float, ...]

    @classmethod
    def between(cls, source: AlignmentEntityCollection, target: AlignmentEntityCollection):
        if [type(e) for e in source] == [type(e) for e in target]:
            checkpoints = [(a.end_station, b.end_station) for a, b in zip(source, target)]
        else:
            def geometry_key(entity):
                a, b = entity.start_coord, entity.end_coord
                return type(entity), a.x, a.y, b.x, b.y, entity.length

            matches = SequenceMatcher(
                None, [geometry_key(e) for e in source], [geometry_key(e) for e in target],
                autojunk=False,
            )
            checkpoints = []
            for i, j, length in matches.get_matching_blocks():
                for a, b in zip(source[i:i + length], target[j:j + length]):
                    checkpoints.extend(((a.start_station, b.start_station), (a.end_station, b.end_station)))

        pairs = [(source.start_station, target.start_station)]
        for a, b in sorted(set(checkpoints)):
            if pairs[-1][0] < a < source.end_station and pairs[-1][1] < b < target.end_station:
                pairs.append((a, b))
        pairs.append((source.end_station, target.end_station))
        old, new = zip(*pairs)
        return cls(old, new)

    @staticmethod
    def _interpolate(station, source, target):
        index = bisect_left(source, station)
        if index < len(source) and source[index] == station:
            return target[index]
        if index == 0 or index == len(source):
            end = 0 if index == 0 else -1
            return target[end] + (station - source[end])
        fraction = (station - source[index - 1]) / (source[index] - source[index - 1])
        return target[index - 1] + fraction * (target[index] - target[index - 1])

    def forward(self, station: float) -> float:
        return self._interpolate(station, self.source, self.target)

    def backward(self, station: float) -> float:
        return self._interpolate(station, self.target, self.source)

    def inverse_rate(self, station: float, *, outgoing: bool) -> float:
        search = bisect_right if outgoing else bisect_left
        index = search(self.target, station)
        if index == 0 or index == len(self.target):
            return 1.0
        return (self.source[index] - self.source[index - 1]) / (self.target[index] - self.target[index - 1])
