# entity/entity_collection.py
from __future__ import annotations
from dataclasses import dataclass, field, replace
import math

from cadgeom import Point2d

from myalignment.core.projection_result import ProjectionResult
from myalignment.enitity.alignment_entity import AlignmentEntity
from myalignment.ipdata.ipdata import PIInput


@dataclass(frozen=True, slots=True)
class AlignmentEntityCollection:
    """
    선형의 Entity 시퀀스 (불변).

    - Entity들은 시작점이 일치하고 측점이 연속되도록 정렬됩니다.
    - 생성 후 절대 변경되지 않습니다.
    """
    entities: tuple[AlignmentEntity, ...] = field(default_factory=tuple)
    _pi_input: PIInput | None = field(default=None, repr=False, compare=False, kw_only=True)

    def __post_init__(self):
        self._validate_continuity()

    # ---- 검증 ----
    def _validate_continuity(self):
        """Entity들이 연속(끝점=다음 시작점, 측점 연속)인지 검증."""
        for i in range(len(self.entities) - 1):
            a, b = self.entities[i], self.entities[i + 1]

            # 측점 연속
            if not math.isclose(a.end_station, b.start_station, abs_tol=1e-6):
                raise ValueError(
                    f"Entity[{i}] end_sta({a.end_station}) ≠ "
                    f"Entity[{i + 1}] start_sta({b.start_station})"
                )

            # 좌표 연속
            if a.end_coord.distance_to(b.start_coord) > 1e-6:
                raise ValueError(
                    f"Entity[{i}] end_coord와 Entity[{i + 1}] start_coord 불일치"
                )

    # ---- 집계 속성 ----
    @property
    def start_station(self) -> float:
        return self.entities[0].start_station if self.entities else 0.0

    @property
    def end_station(self) -> float:
        return self.entities[-1].end_station if self.entities else 0.0

    @property
    def start_coord(self) -> Point2d:
        return self.entities[0].start_coord if self.entities else Point2d(0, 0)

    @property
    def end_coord(self) -> Point2d:
        """컬렉션 전체의 끝점 월드 좌표."""
        return self.entities[-1].end_coord if self.entities else Point2d(0, 0)

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
    def entity_at_station(self, station: float) -> AlignmentEntity:
        """주어진 측점이 속한 Entity."""
        for e in self.entities:
            if e.start_station <= station <= e.end_station:
                return e
        # Reversing the order of summed lengths can shift the endpoint by a few ulps.
        if self.entities:
            for entity, endpoint in ((self.entities[0], self.start_station), (self.entities[-1], self.end_station)):
                if math.isfinite(station) and abs(station - endpoint) <= min(1e-6, 8 * math.ulp(endpoint)):
                    return entity
        raise ValueError(f"station {station}이 Entity 범위 밖")

    def point_at(self, station: float, offset: float = 0.0) -> Point2d:
        """측점 좌표."""
        return self.entity_at_station(station).point_at(station, offset)

    def tangent_at(self, station: float) -> float:
        """측점 접선 방위각."""
        return self.entity_at_station(station).tangent_at(station)

    def project(self, point: Point2d) -> ProjectionResult:
        """월드 점을 가장 가까운 Entity에 투영."""
        candidates = [e.project(point) for e in self.entities]
        if not candidates:
            raise ValueError("Entity가 없습니다.")
        return min(candidates, key=lambda pr: pr.distance)

    # ---- 불변 변환 ----
    def reversed(self) -> "AlignmentEntityCollection":
        """전체 시퀀스를 뒤집은 새 컬렉션."""
        if not self.entities:
            return AlignmentEntityCollection()

        reversed_entities = []
        # 뒤에서부터 reversed + 재배치
        running_station = self.start_station
        for e in reversed(self.entities):
            rev = e.reversed()
            # start_station 재설정
            new_e = rev._replace(
                start_station=running_station,
                start_coord=rev.start_coord,
            )
            reversed_entities.append(new_e)
            running_station += new_e.length

        pi_input = self._pi_input
        if pi_input is not None:
            pi_input = replace(
                pi_input,
                pi_coords=pi_input.pi_coords[::-1],
                curve_specs=tuple(
                    replace(spec, entry_length=spec.exit_length, exit_length=spec.entry_length)
                    for spec in reversed(pi_input.curve_specs)
                ),
            )
        return AlignmentEntityCollection(tuple(reversed_entities), _pi_input=pi_input)

    def offset_by(self, distance: float) -> "AlignmentEntityCollection":
        """전체 시퀀스를 평행 이동한 새 컬렉션."""
        return AlignmentEntityCollection(
            entities=tuple(e.offset_by(distance) for e in self.entities)
        )
