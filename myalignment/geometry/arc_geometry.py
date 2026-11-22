# geometry/arc_geometry.py
from __future__ import annotations
from dataclasses import dataclass, replace
import math

from cadgeom import Point2d
from myalignment.core.projection_result import ProjectionResult
from myalignment.geometry.geometry_base import Geometry
from myalignment.utils import CurveDirection


@dataclass(frozen=True, slots=True)
class ArcGeometry(Geometry):
    """
    원곡선 기하 요소 (로컬 좌표계).

    로컬 좌표계:
        - 시작점: (0, 0)
        - 시작 접선: x축 +
        - 곡선 방향: LEFT(반시계) / RIGHT(시계)
    """
    _radius: float = 0.0
    _delta: float = 0.0  # 교각 (rad, 항상 ≥ 0)
    direction: CurveDirection = CurveDirection.NULL

    def __post_init__(self):
        if self._radius <= 0:
            raise ValueError(f"radius는 > 0이어야 함: {self._radius}")
        if self._delta < 0:
            raise ValueError(f"delta는 ≥ 0이어야 함: {self._delta}")
        if self._delta > math.pi:
            raise ValueError(f"delta는 ≤ π여야 함: {self._delta}")
        if self.direction == CurveDirection.NULL:
            raise ValueError("direction이 NULL입니다.")

    @property
    def length(self) -> float:
        return self._radius * self._delta

    @property
    def radius(self) -> float:
        return self._radius

    @property
    def delta(self) -> float:
        return self._delta

    @property
    def is_valid(self) -> bool:
        return (
                self._radius > 0
                and 0 <= self._delta <= math.pi
                and self.direction != CurveDirection.NULL
        )

    def point_at(self, s: float, offset: float = 0.0) -> Point2d:
        """로컬 측점 s의 좌표. offset은 방사 방향."""
        s = self._check_s(s)
        theta = s / self._radius  # 로컬 회전각

        sign = +1.0 if self.direction == CurveDirection.LEFT else -1.0

        # 양의 횡거는 진행 방향 오른쪽이다.
        radius = self._radius + sign * offset
        return self._to_local_point(
            radius * math.sin(theta),
            sign * (self._radius - radius * math.cos(theta)),
        )

    def tangent_at(self, s: float) -> float:
        """접선 방위각 (로컬 기준)."""
        s = self._check_s(s)
        theta = s / self._radius
        sign = +1.0 if self.direction == CurveDirection.LEFT else -1.0
        return self.start_azimuth + sign * theta

    def project_at(self, p: Point2d) -> ProjectionResult:
        """로컬 점 p를 원호에 투영."""
        lx, ly = self._to_local_coords(p)

        sign = 1 if self.direction == CurveDirection.LEFT else -1
        cy = sign * self._radius
        at_center = math.hypot(lx, ly - cy) < 1e-12
        theta = math.atan2(lx, self._radius - sign * ly)
        on_arc = not at_center and -1e-12 <= theta <= self._delta + 1e-12
        if on_arc:
            theta = max(0.0, min(self._delta, theta))
        else:
            ex, ey = self._local_end()
            theta = self._delta if not at_center and math.hypot(lx - ex, ly - ey) < math.hypot(lx, ly) else 0.0

        s = theta * self._radius
        px = self._radius * math.sin(theta)
        py = cy * (1 - math.cos(theta))
        dx, dy = lx - px, ly - py
        offset = dx * math.sin(theta) * sign - dy * math.cos(theta)
        return ProjectionResult(
            point=self._to_local_point(px, py), station=s, offset=offset,
            distance=math.hypot(dx, dy), tangent=self.tangent_at(s), is_on_entity=on_arc,
        )

    def reversed(self) -> "ArcGeometry":
        """뒤집힌 원호 (방향 반전, 시작 접선 + π)."""
        new_dir = (
            CurveDirection.RIGHT if self.direction == CurveDirection.LEFT
            else CurveDirection.LEFT
        )
        return ArcGeometry(
            start_azimuth=(self.tangent_at(self.length) + math.pi) % math.tau,
            _radius=self._radius,
            _delta=self._delta,
            direction=new_dir,
            is_reversed=not self.is_reversed,
        )

    def offset_by(self, distance: float) -> "ArcGeometry":
        """평행 이동한 원호 (반지름 변화)."""
        sign = +1.0 if self.direction == CurveDirection.LEFT else -1.0
        new_radius = self._radius + sign * distance
        if not math.isfinite(new_radius) or new_radius <= 0:
            raise ValueError(f"offset 후 유효하지 않은 반지름: {new_radius}")
        return replace(self, _radius=new_radius)

    # ---- 로컬 헬퍼 ----
    def _local_end(self) -> tuple[float, float]:
        """로컬 좌표계에서 끝점."""
        sign = +1.0 if self.direction == CurveDirection.LEFT else -1.0
        cx, cy = 0.0, sign * self._radius
        end_ang = -sign * math.pi / 2 + sign * self._delta
        return (
            cx + self._radius * math.cos(end_ang),
            cy + self._radius * math.sin(end_ang),
        )

    def _to_local_point(self, lx: float, ly: float) -> Point2d:
        ca, sa = math.cos(self.start_azimuth), math.sin(self.start_azimuth)
        return Point2d(lx * ca - ly * sa, lx * sa + ly * ca)

    def _to_local_coords(self, p: Point2d) -> tuple[float, float]:
        ca, sa = math.cos(self.start_azimuth), math.sin(self.start_azimuth)
        return (p.x * ca + p.y * sa, -p.x * sa + p.y * ca)