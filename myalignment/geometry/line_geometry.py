# geometry/line_geometry.py
from __future__ import annotations
from dataclasses import dataclass
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

    def __post_init__(self):
        if self._length < 0:
            raise ValueError(f"length는 ≥ 0이어야 함: {self._length}")
        if not math.isfinite(self.start_azimuth):
            raise ValueError(f"start_azimuth가 유한하지 않음: {self.start_azimuth}")

    @property
    def length(self) -> float:
        return self._length

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

        s = max(0.0, min(self._length, lx))
        is_on = (0.0 <= lx <= self._length)

        # 로컬 투영점
        proj_local = Point2d(s, 0.0)
        proj_world = self._to_local_point(s, 0.0)

        # offset: 로컬 y의 반대 (좌-, 우+)
        offset = -ly
        distance = abs(ly)

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
        return LineGeometry(
            start_azimuth=(self.start_azimuth + math.pi) % (2 * math.pi),
            _length=self._length,
            is_reversed=not self.is_reversed,
        )

    def offset_by(self, distance: float) -> "LineGeometry":
        """평행 이동한 직선 (길이/방위각 동일, start만 이동)."""
        # 직선은 offset_by가 기하 자체를 바꾸지 않음 (start 이동은 외부 책임)
        return LineGeometry(
            start_azimuth=self.start_azimuth,
            _length=self._length,
            is_reversed=self.is_reversed,
        )

    # ---- 로컬 ↔ 월드 변환 (start_azimuth 기준) ----
    def _to_local_point(self, lx: float, ly: float) -> Point2d:
        """로컬 (lx, ly) → 월드 좌표."""
        ca, sa = math.cos(self.start_azimuth), math.sin(self.start_azimuth)
        return Point2d(lx * ca - ly * sa, lx * sa + ly * ca)

    def _to_local_coords(self, p: Point2d) -> tuple[float, float]:
        """월드 좌표 → 로컬 (lx, ly)."""
        ca, sa = math.cos(self.start_azimuth), math.sin(self.start_azimuth)
        lx = p.x * ca + p.y * sa
        ly = -p.x * sa + p.y * ca
        return lx, ly