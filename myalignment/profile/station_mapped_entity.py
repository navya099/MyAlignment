from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from myalignment.profile.profileentity import ProfileEntity

if TYPE_CHECKING:
    from myalignment.alignment.offset_station_map import OffsetStationMap


@dataclass(frozen=True, slots=True)
class StationMappedProfileEntity(ProfileEntity):
    """오프셋 측점에서 원본 종단의 표고와 구배를 평가한다."""

    _source: ProfileEntity = field(kw_only=True, repr=False)
    _stations: OffsetStationMap = field(kw_only=True, repr=False)
    _direction: int = field(default=1, kw_only=True)
    _shift: float = field(default=0.0, kw_only=True)

    @classmethod
    def from_entity(cls, entity: ProfileEntity, stations: OffsetStationMap) -> StationMappedProfileEntity:
        return cls(
            entity_id=entity.entity_id, entity_type=entity.entity_type,
            start_station=stations.forward(entity.start_station),
            end_station=stations.forward(entity.end_station),
            start_elevation=entity.start_elevation, end_elevation=entity.end_elevation,
            _source=entity, _stations=stations,
        )

    def _to_source(self, station: float) -> float:
        return self._stations.backward(self._direction * (self._clamp_station(station) - self._shift))

    def _from_source(self, station: float) -> float:
        return self._direction * self._stations.forward(station) + self._shift

    def elevation_at(self, station: float) -> float:
        return self._source.elevation_at(self._to_source(station))

    def grade_at(self, station: float) -> float:
        mapped = self._direction * (self._clamp_station(station) - self._shift)
        at_source_end = mapped >= self._stations.forward(self._source.end_station)
        rate = self._stations.inverse_rate(mapped, outgoing=not at_source_end)
        return self._direction * rate * self._source.grade_at(self._to_source(station))

    @property
    def pvi_station(self) -> float:
        return self._from_source(self._source.pvi_station)

    @property
    def pvi_elevation(self) -> float:
        return self._source.pvi_elevation

    @property
    def k_value(self) -> float:
        change = self.end_grade - self.start_grade
        return self.length / change if change else float("inf")

    def pvi_stations(self) -> tuple[float, ...]:
        stations = getattr(self._source, "pvi_stations", None)
        return tuple(self._from_source(s) for s in stations()) if stations else ()

    def extremum_station(self) -> float | None:
        extremum = getattr(self._source, "extremum_station", None)
        station = extremum() if extremum else None
        return self._from_source(station) if station is not None else None

    def reversed(self, total_length: float) -> StationMappedProfileEntity:
        return replace(
            self, start_station=total_length - self.end_station,
            end_station=total_length - self.start_station,
            start_elevation=self.end_elevation, end_elevation=self.start_elevation,
            _direction=-self._direction, _shift=total_length - self._shift,
        )
