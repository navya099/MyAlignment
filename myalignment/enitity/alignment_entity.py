# entity/alignment_entity.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import math
from typing import Self

from cadgeom import Point2d

from myalignment.core.projection_result import ProjectionResult
from myalignment.core.station_offset import StationOffsetPoint
from myalignment.enum.alignmententitytype import AlignmentEntityType
from myalignment.geometry.geometry_base import Geometry
from myalignment.utils.utils import generate_entity_id


@dataclass(frozen=True, slots=True)
class AlignmentEntity(ABC):
    """
    선형의 단일 기하 요소 (불변).

    C3D의 AlignmentEntity와 호환.
    - 로컬 기하(`geometry`)를 월드 좌표계로 감쌉니다.
    - `start_coord` + `start_azimuth`가 로컬→월드 변환 기준.

    Attributes:
        entity_id: 고유 식별자 (UUID 기반).
        entity_type: C3D AlignmentEntityType.
        geometry: 로컬 기하 (Line/Arc/Spiral).
        start_station: 선형 시작 기준 누적 측점 (m).
        start_coord: Entity 시작점의 월드 좌표.
        start_azimuth: Entity 시작 접선의 월드 방위각 (rad).
    """
    entity_id: int = field(default_factory=generate_entity_id)
    entity_type: AlignmentEntityType = AlignmentEntityType.Line
    geometry: Geometry = None
    start_station: float = 0.0
    start_coord: Point2d = field(default_factory=lambda: Point2d(0, 0))
    start_azimuth: float = 0.0

    def __post_init__(self):
        if self.geometry is None:
            raise ValueError("geometry가 None입니다.")
        if not self.geometry.is_valid:
            raise ValueError(f"유효하지 않은 geometry: {self.geometry}")
        if not math.isfinite(self.start_station):
            raise ValueError(f"start_station이 유한하지 않음: {self.start_station}")
        if not math.isfinite(self.start_azimuth):
            raise ValueError(f"start_azimuth가 유한하지 않음: {self.start_azimuth}")

    # ---- 필수 속성 ----
    @property
    def length(self) -> float:
        """Entity 길이 (m)."""
        return self.geometry.length

    @property
    def end_station(self) -> float:
        """Entity 끝 측점 (m)."""
        return self.start_station + self.length

    @property
    def end_coord(self) -> Point2d:
        """Entity 끝점의 월드 좌표."""
        return self.point_at(self.end_station)

    @property
    def end_azimuth(self) -> float:
        """Entity 끝 접선의 월드 방위각 (rad)."""
        return self.tangent_at(self.end_station)

    # ---- 월드 좌표 계산 ----
    @property
    def _geometry_rotation(self) -> float:
        # Geometry.point_at() already applies the geometry's start azimuth.
        return self.start_azimuth - self.geometry.start_azimuth

    def point_at(self, station: float, offset: float = 0.0) -> Point2d:
        """주어진 측점의 월드 좌표."""
        s = self._to_local_s(station)
        local_pt = self.geometry.point_at(s, offset)
        return self._local_to_world(local_pt, self._geometry_rotation, self.start_coord)

    def tangent_at(self, station: float) -> float:
        """주어진 측점의 월드 접선 방위각 (rad)."""
        s = self._to_local_s(station)
        return self.geometry.tangent_at(s) + self._geometry_rotation

    def project(self, point: Point2d) -> ProjectionResult:
        """월드 점을 Entity에 투영."""
        # 월드 → 로컬 좌표 변환
        local_pt = self._world_to_local(point, self._geometry_rotation, self.start_coord)
        # 로컬 기하에 투영
        local_pr = self.geometry.project_at(local_pt)
        # 로컬 station → 월드 station
        world_station = self.start_station + local_pr.station
        # 투영점 로컬 → 월드
        world_proj = self._local_to_world(local_pr.point, self._geometry_rotation, self.start_coord)
        return ProjectionResult(
            point=world_proj,
            station=world_station,
            offset=local_pr.offset,
            distance=local_pr.distance,
            tangent=local_pr.tangent + self._geometry_rotation,
            is_on_entity=local_pr.is_on_entity,
        )

    def station_offset_at(self, point: Point2d) -> StationOffsetPoint:
        """월드 점 → 측점/횡거."""
        pr = self.project(point)
        return pr.to_station_offset()

    # ---- 불변 변환 ----
    @abstractmethod
    def reversed(self) -> Self:
        """뒤집힌 새 Entity 반환."""
        ...

    @abstractmethod
    def offset_by(self, distance: float) -> Self:
        """평행 이동한 새 Entity 반환."""
        ...

    def with_start(self, start_coord: Point2d, start_station: float) -> Self:
        """시작점/측점 재배치한 새 Entity 반환."""
        return self._replace(start_coord=start_coord, start_station=start_station)

    @abstractmethod
    def _replace(self, **kwargs) -> Self:
        """dataclass replace 헬퍼."""
        ...

    # ---- 헬퍼 ----
    def _to_local_s(self, station: float) -> float:
        """월드 station → 로컬 s (0 ~ length)."""
        s = station - self.start_station
        if s < -1e-6 or s > self.length + 1e-6:
            raise ValueError(
                f"station {station}이 Entity 범위를 벗어남 "
                f"[{self.start_station}, {self.end_station}]"
            )
        return max(0.0, min(self.length, s))

    @staticmethod
    def _local_to_world(local_pt: Point2d, azimuth: float, origin: Point2d) -> Point2d:
        """로컬 좌표(회전만 적용) → 월드 좌표."""
        ca, sa = math.cos(azimuth), math.sin(azimuth)
        return Point2d(
            origin.x + local_pt.x * ca - local_pt.y * sa,
            origin.y + local_pt.x * sa + local_pt.y * ca,
        )

    @staticmethod
    def _world_to_local(world_pt: Point2d, azimuth: float, origin: Point2d) -> Point2d:
        """월드 좌표 → 로컬 좌표 (역회전)."""
        dx = world_pt.x - origin.x
        dy = world_pt.y - origin.y
        ca, sa = math.cos(azimuth), math.sin(azimuth)
        return Point2d(dx * ca + dy * sa, -dx * sa + dy * ca)

    def contains_station(self, station: float) -> bool:
        """주어진 측점이 Entity 범위 내인지."""
        return self.start_station <= station <= self.end_station