# geometry/line_geometry.py
from __future__ import annotations
from dataclasses import dataclass, field, replace
import math

from cadgeom import Point2d

from myalignment.core.projection_result import ProjectionResult
from myalignment.geometry.geometry_base import Geometry


@dataclass(frozen=True, slots=True)
class LineGeometry(Geometry):
    """
    직선 기하 요소 (로컬 좌표계).

    로컬 좌표계:
        - 시작점: (0, 0)
        - 진행 방향: x축 +
        - 길이: length
    """
    _length: float = 0.0
    _delta: tuple[float, float] | None = field(default=None, repr=False, kw_only=True)

    def __post_init__(self):
        if self._length < 0:
            raise ValueError(f"length는 ≥ 0이어야 함: {self._length}")
        if not math.isfinite(self.start_azimuth):
            raise ValueError(f"start_azimuth가 유한하지 않음: {self.start_azimuth}")

    @property
    def length(self) -> float:
        return self._length

    @property
    def unit_direction(self) -> tuple[float, float]:
        if self._delta is not None and self.length:
            return self._delta[0] / self.length, self._delta[1] / self.length
        return math.cos(self.start_azimuth), math.sin(self.start_azimuth)

    @property
    def coordinate_delta(self) -> tuple[float, float]:
        if self._delta is not None:
            return self._delta
        x, y = self.unit_direction
        return self.length * x, self.length * y

    @property
    def is_valid(self) -> bool:
        return self._length > 0 and math.isfinite(self.start_azimuth)

    def point_at(self, s: float, offset: float = 0.0) -> Point2d:
        """로컬 측점 s의 좌표. offset은 y축 방향(좌-/우+)."""
        s = self._check_s(s)
        # 로컬: x = s, y = -offset (좌-, 우+ → y 부호 반전)
        lx, ly = s, -offset
        return self._to_local_point(lx, ly)

    def tangent_at(self, s: float) -> float:
        """직선이므로 s와 무관하게 일정."""
        return self.start_azimuth

    def project_at(self, p: Point2d) -> ProjectionResult:
        """로컬 점 p를 직선에 투영."""
        lx, ly = self._to_local_coords(p)

        is_on = (0.0 <= lx <= self._length)

        # 측점(s) 및 실제 거리(distance) 계산
        if lx < 0.0:
            s = 0.0
            distance = math.hypot(lx, ly)  # 시작점(0, 0)까지의 거리
        elif lx > self._length:
            s = self._length
            distance = math.hypot(lx - self._length, ly)  # 끝점(length, 0)까지의 거리
        else:
            s = lx
            distance = abs(ly)  # 선분 내부 수직 거리

        # 로컬 투영점 월드 변환 준비
        proj_world = self._to_local_point(s, 0.0)

        # offset: 로컬 y의 반대 (좌-, 우+)
        offset = -ly

        return ProjectionResult(
            point=proj_world,
            station=s,
            offset=offset,
            distance=distance,
            tangent=self.start_azimuth,
            is_on_entity=is_on,
        )

    def reversed(self) -> "LineGeometry":
        """뒤집힌 직선 (start_azimuth + π)."""
        x, y = self.coordinate_delta
        return replace(
            self,
            start_azimuth=(self.start_azimuth + math.pi) % (2 * math.pi),
            is_reversed=not self.is_reversed,
            _delta=(-x, -y),
        )

    def offset_by(self, distance: float) -> "LineGeometry":
        """평행 이동한 직선 (길이/방위각 동일, start만 이동)."""
        # 직선은 offset_by가 기하 자체를 바꾸지 않음 (start 이동은 외부 책임)
        return self

    # ---- 로컬 ↔ 월드 변환 (start_azimuth 기준) ----
    def _to_local_point(self, lx: float, ly: float) -> Point2d:
        """로컬 (lx, ly) → 월드 좌표."""
        ca, sa = self.unit_direction
        return Point2d(lx * ca - ly * sa, lx * sa + ly * ca)

    def _to_local_coords(self, p: Point2d) -> tuple[float, float]:
        """월드 좌표 → 로컬 (lx, ly)."""
        ca, sa = self.unit_direction
        lx = p.x * ca + p.y * sa
        ly = -p.x * sa + p.y * ca
        return lx, ly
