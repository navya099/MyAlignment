# profile/profile.py
from __future__ import annotations
from collections.abc import Iterable
import csv
from dataclasses import dataclass, field, replace
import math
from pathlib import Path
from typing import TYPE_CHECKING, Self

from myalignment.profile.label_set import ProfileLabelSet
from myalignment.profile.label_style import ProfileLabelStyle
from myalignment.profile.label_type import ProfileLabelType

from myalignment.profile.profile_asymmetric_parabola import ProfileAsymmetricParabola
from myalignment.profile.profile_symmetric_parabola import ProfileSymmetricParabola
from myalignment.profile.profileentity import ProfileEntity
from myalignment.profile.profileentitycollection import ProfileEntityCollection
from myalignment.profile.profiletangent import ProfileTangent
from myalignment.profile.profiletype import ProfileType
from myalignment.profile.station_mapped_entity import StationMappedProfileEntity

if TYPE_CHECKING:
    from myalignment.alignment.station_map import StationMap


def _point_tangents(points: Iterable[tuple[float | str, float | str]]) -> list[ProfileTangent]:
    tangents = []
    previous = None
    for index, row in enumerate(points, start=1):
        if isinstance(row, (str, bytes)):
            raise ValueError(f"Profile row {index}: expected a numeric station and elevation")
        try:
            station, elevation = row
            station, elevation = float(station), float(elevation)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError(f"Profile row {index}: expected a numeric station and elevation") from error
        if not math.isfinite(station) or not math.isfinite(elevation):
            raise ValueError(f"Profile row {index}: station and elevation must be finite")
        if previous is not None:
            if station <= previous[0]:
                raise ValueError(f"Profile row {index}: raw stations must be strictly increasing")
            tangents.append(ProfileTangent.create(previous[0], station, previous[1], elevation))
        previous = station, elevation
    if not tangents:
        raise ValueError("At least two profile points are required")
    return tangents


@dataclass(frozen=True, slots=True)
class Profile:
    """
    종단 프로파일 (C3D 호환).

    Attributes:
        name: 프로파일 이름.
        profile_type: FG(설계선) / EG(현황선).
        entities: 종단 요소 시퀀스 (불변).
    """
    name: str = "Profile1"
    profile_type: ProfileType = ProfileType.EG
    entities: ProfileEntityCollection = field(default_factory=ProfileEntityCollection)

    label_set: ProfileLabelSet = field(default_factory=ProfileLabelSet.standard, kw_only=True)

    @classmethod
    def from_points(
        cls, points: Iterable[tuple[float | str, float | str]], *, name: str = "Profile1",
        profile_type: ProfileType = ProfileType.EG,
    ) -> Self:
        """오름차순 (원시 측점, 표고) 행을 접선으로 연결한다."""
        entities = ProfileEntityCollection(tuple(_point_tangents(points)))
        return cls(name=name, profile_type=profile_type, entities=entities)

    @classmethod
    def from_csv(
        cls, path: str | Path, *, name: str = "Profile1", profile_type: ProfileType = ProfileType.EG,
        station_column: str = "station", elevation_column: str = "elevation",
        delimiter: str = ",", encoding: str = "utf-8-sig",
    ) -> Self:
        """헤더가 있는 CSV에서 원시 측점과 표고 열을 읽는다."""
        if not station_column or not elevation_column or station_column == elevation_column:
            raise ValueError("station_column and elevation_column must be distinct nonempty names")
        with Path(path).open(encoding=encoding, newline="") as stream:
            reader = csv.DictReader(stream, delimiter=delimiter)
            header = reader.fieldnames or []
            for column in (station_column, elevation_column):
                if header.count(column) != 1:
                    raise ValueError(f"CSV must contain exactly one {column!r} column")
            return cls.from_points(
                ((row[station_column], row[elevation_column]) for row in reader),
                name=name, profile_type=profile_type,
            )

    def with_label_set(self, label_set: ProfileLabelSet) -> "Profile":
        return replace(self, label_set=label_set)

    def with_label_style(self, label_type: ProfileLabelType, style: ProfileLabelStyle) -> "Profile":
        return self.with_label_set(self.label_set.with_style(label_type, style))

    # ---- 기본 속성 ----
    @property
    def start_station(self) -> float:
        return self.entities.start_station

    @property
    def end_station(self) -> float:
        return self.entities.end_station

    @property
    def length(self) -> float:
        return self.entities.length

    @property
    def is_valid(self) -> bool:
        return len(self.entities) > 0

    # ---- 조회 ----
    def elevation_at(self, station: float) -> float:
        """종단 요소에서 주어진 측점의 표고를 구한다.

        Raises:
            ValueError: 측점을 포함하는 종단 요소가 없을 때.
        """
        return self.entities.elevation_at(station)

    def grade_at(self, station: float) -> float:
        """종단 요소에서 주어진 측점의 구배를 소수 비율로 반환한다. 0.02는 2%다.

        Raises:
            ValueError: 측점을 포함하는 종단 요소가 없을 때.
        """
        return self.entities.grade_at(station)

    # ---- 집계 ----
    @property
    def max_slope(self) -> float:
        return self.entities.max_grade

    @property
    def min_slope(self) -> float:
        return self.entities.min_grade

    @property
    def max_abs_slope(self) -> float:
        return self.entities.max_abs_grade

    @property
    def max_elevation(self) -> float:
        return self.entities.max_elevation

    @property
    def min_elevation(self) -> float:
        return self.entities.min_elevation

    @property
    def pvi_count(self) -> int:
        return self.entities.pvi_count

    # ---- 불변 변환 ----
    def reversed(self) -> "Profile":
        """전체 길이 기준으로 뒤집힌 새 프로파일."""
        return self._reversed_about(self.start_station + self.end_station)

    def _reversed_about(self, station_sum: float) -> "Profile":
        return replace(
            self,
            entities=ProfileEntityCollection(
                entities=tuple(
                    e.reversed(station_sum) for e in reversed(self.entities.entities)
                )
            ),
        )

    def _map_stations(self, stations: "StationMap") -> "Profile":
        return self.with_entities(ProfileEntityCollection(tuple(
            StationMappedProfileEntity.from_entity(entity, stations) for entity in self.entities
        )))

    def with_entities(self, entities: ProfileEntityCollection) -> "Profile":
        return replace(self, entities=entities)


# ================================================================
# 빌더 — 선언적 생성
# ================================================================
class ProfileBuilder:
    """Profile 선언적 빌더."""

    def __init__(
        self,
        name: str = "Profile1",
        profile_type: ProfileType = ProfileType.EG,
    ):
        self._name = name
        self._profile_type = profile_type
        self._entities: list[ProfileEntity] = []

    def add_tangent(
            self,
            start_station: float,
            end_station: float,
            start_elevation: float,
            end_elevation: float,
    ) -> "ProfileBuilder":
        self._entities.append(
            ProfileTangent.create(
                start_station=start_station,
                end_station=end_station,
                start_elevation=start_elevation,
                end_elevation=end_elevation,
            )
        )
        return self

    def add_points(self, points: Iterable[tuple[float | str, float | str]]) -> Self:
        """오름차순 (원시 측점, 표고) 행을 일괄 접선으로 추가한다."""
        self._entities.extend(_point_tangents(points))
        return self

    def add_symmetric_parabola(
            self,
            pvi_station: float,
            pvi_elevation: float,
            grade_in: float,
            grade_out: float,
            curve_length: float,
    ) -> "ProfileBuilder":
        self._entities.append(
            ProfileSymmetricParabola.create(
                pvi_station=pvi_station,
                pvi_elevation=pvi_elevation,
                grade_in=grade_in,
                grade_out=grade_out,
                curve_length=curve_length,
            )
        )
        return self

    def add_asymmetric_parabola(
            self,
            pvi_station: float,
            pvi_elevation: float,
            grade_in: float,
            grade_out: float,
            length_in: float,
            length_out: float,
    ) -> "ProfileBuilder":
        self._entities.append(
            ProfileAsymmetricParabola.create(
                pvi_station=pvi_station,
                pvi_elevation=pvi_elevation,
                grade_in=grade_in,
                grade_out=grade_out,
                length_in=length_in,
                length_out=length_out,
            )
        )
        return self

    def build(self, validate_grades: bool = False) -> Profile:
        col = ProfileEntityCollection(entities=tuple(self._entities))
        if validate_grades:
            for i in range(len(col) - 1):
                a, b = col[i], col[i + 1]
                if not math.isclose(a.end_grade, b.start_grade, abs_tol=1e-6):
                    raise ValueError(
                        f"구배 불연속: Entity[{i}].end_grade={a.end_grade} ≠ "
                        f"Entity[{i+1}].start_grade={b.start_grade}"
                    )
        return Profile(
            name=self._name,
            profile_type=self._profile_type,
            entities=col,
        )
