# profile/profile_entity_collection.py
from __future__ import annotations
from dataclasses import dataclass, field
import math

from myalignment.profile.profileentity import ProfileEntity


@dataclass(frozen=True, slots=True)
class ProfileEntityCollection:
    """종단 요소 시퀀스 (불변, station/표고 연속 보장)."""
    entities: tuple[ProfileEntity, ...] = field(default_factory=tuple)

    def __post_init__(self):
        self._validate_continuity()

    def _validate_continuity(self):
        for i in range(len(self.entities) - 1):
            a, b = self.entities[i], self.entities[i + 1]
            if not math.isclose(a.end_station, b.start_station, abs_tol=1e-6):
                raise ValueError(
                    f"Entity[{i}] end_sta({a.end_station}) ≠ "
                    f"Entity[{i+1}] start_sta({b.start_station})"
                )
            if not math.isclose(a.end_elevation, b.start_elevation, abs_tol=1e-6):
                raise ValueError(
                    f"Entity[{i}] end_elev({a.end_elevation}) ≠ "
                    f"Entity[{i+1}] start_elev({b.start_elevation})"
                )

    @property
    def start_station(self) -> float:
        return self.entities[0].start_station if self.entities else 0.0

    @property
    def end_station(self) -> float:
        return self.entities[-1].end_station if self.entities else 0.0

    @property
    def length(self) -> float:
        return self.end_station - self.start_station if self.entities else 0.0

    def __len__(self) -> int:
        return len(self.entities)

    def __iter__(self):
        return iter(self.entities)

    def __getitem__(self, idx):
        return self.entities[idx]

    # ---- 조회 ----
    def entity_at_station(self, station: float) -> ProfileEntity:
        for e in self.entities:
            if e.contains_station(station):
                return e
        raise ValueError(f"station {station}이 Profile 범위 밖")

    def elevation_at(self, station: float) -> float:
        return self.entity_at_station(station).elevation_at(station)

    def grade_at(self, station: float) -> float:
        return self.entity_at_station(station).grade_at(station)

    # ---- 집계 ----
    @property
    def max_grade(self) -> float:
        grades = [e.start_grade for e in self.entities] + \
                 [e.end_grade for e in self.entities]
        return max(grades) if grades else 0.0

    @property
    def min_grade(self) -> float:
        grades = [e.start_grade for e in self.entities] + \
                 [e.end_grade for e in self.entities]
        return min(grades) if grades else 0.0

    @property
    def max_abs_grade(self) -> float:
        grades = [abs(e.start_grade) for e in self.entities] + \
                 [abs(e.end_grade) for e in self.entities]
        return max(grades) if grades else 0.0

    @property
    def max_elevation(self) -> float:
        """프로파일 전체 최대 표고 (파라볼라 내부 극값 포함)."""
        if not self.entities:
            return 0.0
        candidates: list[float] = []
        for e in self.entities:
            candidates.append(e.start_elevation)
            candidates.append(e.end_elevation)
            ext = getattr(e, "extremum_station", None)
            if callable(ext):
                sta = ext()
                if sta is not None:
                    candidates.append(e.elevation_at(sta))
        return max(candidates)

    @property
    def min_elevation(self) -> float:
        """프로파일 전체 최소 표고 (파라볼라 내부 극값 포함)."""
        if not self.entities:
            return 0.0
        candidates: list[float] = []
        for e in self.entities:
            candidates.append(e.start_elevation)
            candidates.append(e.end_elevation)
            ext = getattr(e, "extremum_station", None)
            if callable(ext):
                sta = ext()
                if sta is not None:
                    candidates.append(e.elevation_at(sta))
        return min(candidates)

    @property
    def pvi_count(self) -> int:
        """
        PVI(구배 변화점) 개수.
        - 파라볼라: 내부 PVI 1개
        - 인접 엔티티 경계 중 구배가 실제로 변하는 지점: PVI
        """
        if not self.entities:
            return 0
        stations: set[float] = set()
        for e in self.entities:
            getter = getattr(e, "pvi_stations", None)
            if callable(getter):
                stations.update(getter())
        for i in range(len(self.entities) - 1):
            a, b = self.entities[i], self.entities[i + 1]
            if not math.isclose(a.end_grade, b.start_grade, abs_tol=1e-9):
                stations.add(a.end_station)
        return len(stations)