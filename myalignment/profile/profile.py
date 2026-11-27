# profile/profile.py
from __future__ import annotations
from collections.abc import Iterable
import csv
from dataclasses import dataclass, field, replace
import math
from pathlib import Path
from typing import TYPE_CHECKING, Self

from myalignment.profile._input import ProfilePoint, ProfilePVI, _point_tangents, _pvi_entities
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
        cls, points: Iterable[ProfilePoint], *, name: str = "Profile1",
        profile_type: ProfileType = ProfileType.EG,
    ) -> Self:
        """오름차순 (원시 측점, 표고) 행을 접선으로 연결한다."""
        entities = ProfileEntityCollection(tuple(_point_tangents(points)))
        return cls(name=name, profile_type=profile_type, entities=entities)

    @classmethod
    def from_pvis(
        cls, pvis: Iterable[ProfilePVI], *, name: str = "Profile1", profile_type: ProfileType = ProfileType.FG,
    ) -> Self:
        """PVI 측점·표고와 선택한 포물선 길이로 접선과 종곡선을 생성한다."""
        entities = ProfileEntityCollection(tuple(_pvi_entities(pvis)))
        return cls(name=name, profile_type=profile_type, entities=entities)

    @classmethod
    def from_csv(
        cls, path: str | Path, *, name: str = "Profile1", profile_type: ProfileType | None = None,
        station_column: str = "station", elevation_column: str = "elevation",
        curve_length_column: str | None = None, length_in_column: str | None = None,
        length_out_column: str | None = None,
        delimiter: str = ",", encoding: str = "utf-8-sig",
    ) -> Self:
        """측점·표고 열과 선택한 종곡선 길이 열을 읽는다."""
        if (length_in_column is None) != (length_out_column is None):
            raise ValueError("length_in_column and length_out_column must be set together")
        curve_columns = tuple(
            column for column in (curve_length_column, length_in_column, length_out_column) if column is not None
        )
        columns = (station_column, elevation_column, *curve_columns)
        if not all(columns) or len(set(columns)) != len(columns):
            raise ValueError("CSV column names must be distinct and nonempty")
        with Path(path).open(encoding=encoding, newline="") as stream:
            reader = csv.DictReader(stream, delimiter=delimiter)
            header = reader.fieldnames or []
            for column in columns:
                if header.count(column) != 1:
                    raise ValueError(f"CSV must contain exactly one {column!r} column")
            if curve_columns:
                def pvis():
                    for index, row in enumerate(reader, start=1):
                        total = (row[curve_length_column] or "").strip() if curve_length_column is not None else ""
                        left = (row[length_in_column] or "").strip() if length_in_column is not None else ""
                        right = (row[length_out_column] or "").strip() if length_out_column is not None else ""
                        if left or right:
                            if total or not (left and right):
                                raise ValueError(f"Profile row {index}: specify a total length or both curve lengths")
                            spec = (left, right)
                        else:
                            spec = total or None
                        yield row[station_column], row[elevation_column], spec

                return cls.from_pvis(pvis(), name=name, profile_type=profile_type or ProfileType.FG)
            return cls.from_points(
                ((row[station_column], row[elevation_column]) for row in reader),
                name=name, profile_type=profile_type or ProfileType.EG,
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

    def add_points(self, points: Iterable[ProfilePoint]) -> Self:
        """오름차순 (원시 측점, 표고) 행을 일괄 접선으로 추가한다."""
        self._entities.extend(_point_tangents(points))
        return self

    def add_pvis(self, pvis: Iterable[ProfilePVI]) -> Self:
        """PVI 목록의 접선과 종곡선을 기존 빌더에 추가한다."""
        self._entities.extend(_pvi_entities(pvis))
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
