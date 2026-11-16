# geometry/arc_geometry.py
from __future__ import annotations
from dataclasses import dataclass
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

        # 로컬 중심: (0, sign*radius)
        cx, cy = 0.0, sign * self._radius

        # 로컬 점 (원 위)
        lx = cx + self._radius * math.sin(theta) * sign * sign  # = cx + r*sin(theta)
        ly = cy - sign * self._radius * math.cos(theta)

        # offset 적용 (방사 방향)
        if offset != 0.0:
            # 방사 단위 벡터
            rx, ry = lx - cx, ly - cy
            r_len = math.hypot(rx, ry)
            if r_len > 0:
                lx += offset * rx / r_len
                ly += offset * ry / r_len

        return self._to_local_point(lx, ly)

    def tangent_at(self, s: float) -> float:
        """접선 방위각 (로컬 기준)."""
        s = self._check_s(s)
        theta = s / self._radius
        sign = +1.0 if self.direction == CurveDirection.LEFT else -1.0
        return self.start_azimuth + sign * theta

    def project_at(self, p: Point2d) -> ProjectionResult:
        """로컬 점 p를 원호에 투영."""
        lx, ly = self._to_local_coords(p)

        sign = +1.0 if self.direction == CurveDirection.LEFT else -1.0
        cx, cy = 0.0, sign * self._radius

        # 중심→점 벡터
        vx, vy = lx - cx, ly - cy
        d = math.hypot(vx, vy)

        if d < 1e-12:
            # 중심점 (degenerate)
            return ProjectionResult(
                point=self._to_local_point(0.0, 0.0),
                station=0.0,
                offset=0.0,
                distance=self._radius,
                tangent=self.tangent_at(0.0),
                is_on_entity=False,
            )

        # 점의 극각 (중심 기준)
        ang = math.atan2(vy, vx)

        # 시작/끝 반지름 각도
        start_ang = math.atan2(-sign * self._radius, 0.0)  # = -sign*π/2
        end_ang = start_ang + sign * self._delta

        # ang를 호 범위로 정규화
        def normalize(a: float, lo: float, hi: float) -> float:
            while a < lo:
                a += 2 * math.pi
            while a > hi:
                a -= 2 * math.pi
            return a

        if sign > 0:  # LEFT
            lo, hi = start_ang, start_ang + self._delta
        else:  # RIGHT
            lo, hi = start_ang - self._delta, start_ang

        ang_norm = normalize(ang, lo, hi)
        is_on = (lo <= ang_norm <= hi)

        if not is_on:
            # 시작/끝 중 가까운 쪽으로 클램프
            d_start = math.hypot(lx - 0.0, ly - 0.0)
            d_end = math.hypot(lx - self._local_end()[0], ly - self._local_end()[1])
            if d_start <= d_end:
                ang_norm = start_ang
                s = 0.0
            else:
                ang_norm = end_ang
                s = self.length
        else:
            s = abs(ang_norm - start_ang) * self._radius

        # 투영점 (로컬)
        proj_local_x = cx + self._radius * math.cos(ang_norm)
        proj_local_y = cy + self._radius * math.sin(ang_norm)
        proj_world = self._to_local_point(proj_local_x, proj_local_y)

        # offset: 반지름 - 거리 (좌-, 우+)
        offset = self._radius - d
        distance = abs(offset)

        return ProjectionResult(
            point=proj_world,
            station=s,
            offset=offset,
            distance=distance,
            tangent=self.tangent_at(s),
            is_on_entity=is_on,
        )

    def reversed(self) -> "ArcGeometry":
        """뒤집힌 원호 (방향 반전, 시작 접선 + π)."""
        new_dir = (
            CurveDirection.RIGHT if self.direction == CurveDirection.LEFT
            else CurveDirection.LEFT
        )
        return ArcGeometry(
            start_azimuth=(self.start_azimuth + self._delta + math.pi) % (2 * math.pi),
            _radius=self._radius,
            _delta=self._delta,
            direction=new_dir,
            is_reversed=not self.is_reversed,
        )

    def offset_by(self, distance: float) -> "ArcGeometry":
        """평행 이동한 원호 (반지름 변화)."""
        sign = +1.0 if self.direction == CurveDirection.LEFT else -1.0
        new_radius = self._radius - sign * distance
        if new_radius <= 0:
            raise ValueError(f"offset 후 반지름이 ≤ 0: {new_radius}")
        # 길이 유지를 위해 delta 조정
        new_delta = self.length / new_radius
        if new_delta > math.pi:
            raise ValueError(f"offset 후 delta > π: {new_delta}")
        return ArcGeometry(
            start_azimuth=self.start_azimuth,
            _radius=new_radius,
            _delta=new_delta,
            direction=self.direction,
            is_reversed=self.is_reversed,
        )

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