# geometry/spiral_geometry.py
from __future__ import annotations
from dataclasses import dataclass
import math

from cadgeom import Point2d
from myalignment.core.projection_result import ProjectionResult
from myalignment.enum.spiraltype import SpiralType
from myalignment.geometry.geometry_base import Geometry
from myalignment.utils import CurveDirection


@dataclass(frozen=True, slots=True)
class SpiralParams:
    """완화곡선 파라미터 (불변)."""
    radius: float  # 곡선 반경
    length: float  # 완화곡선장 L
    spiral_type: SpiralType  # 완화곡선 종류

    def __post_init__(self):
        if self.radius <= 0:
            raise ValueError(f"radius > 0 필요: {self.radius}")
        if self.length <= 0:
            raise ValueError(f"length > 0 필요: {self.length}")
        if self.spiral_type in (
                SpiralType.OffsetInvalidSpiralType,
        ):
            raise ValueError(f"spiral_type 미설정: {self.spiral_type}")


@dataclass(frozen=True, slots=True)
class SpiralGeometry(Geometry):
    """
    완화곡선 기하 요소 (로컬 좌표계).

    `spiral_type`에 따라 3차(일본식)/5차(클로소이드) 분기.
    """
    params: SpiralParams = None
    direction: CurveDirection = CurveDirection.NULL

    def __post_init__(self):
        if self.params is None:
            raise ValueError("params가 None입니다.")
        if self.direction == CurveDirection.NULL:
            raise ValueError("direction이 NULL입니다.")

    @property
    def length(self) -> float:
        return self.params.length

    @property
    def radius(self) -> float:
        return self.params.radius

    @property
    def spiral_type(self) -> SpiralType:
        return self.params.spiral_type

    @property
    def is_valid(self) -> bool:
        return (
                self.params is not None
                and self.direction != CurveDirection.NULL
        )

    def point_at(self, s: float, offset: float = 0.0) -> Point2d:
        """로컬 측점 s의 좌표."""
        s = self._check_s(s)
        lx, ly = self._spiral_xy(s, self.spiral_type)

        if self.direction == CurveDirection.RIGHT:
            ly = -ly  # y 반전 (좌→우)

        if offset != 0.0:
            # 접선 방향의 수직으로 offset
            tang = self.tangent_at(s)
            nx = -math.sin(tang)
            ny = math.cos(tang)
            lx += offset * nx
            ly += offset * ny

        return self._to_local_point(lx, ly)

    def tangent_at(self, s: float) -> float:
        """접선 방위각 (로컬)."""
        s = self._check_s(s)
        t = self._spiral_tangent(s)
        sign = +1.0 if self.direction == CurveDirection.LEFT else -1.0
        return self.start_azimuth + sign * t

    def project_at(self, p: Point2d) -> ProjectionResult:
        """완화곡선은 해석적 역변환이 어려워 수치 탐색."""
        lx, ly = self._to_local_coords(p)

        # 이분법으로 최근접 s 탐색 (샘플링 → 이분법)
        n = 100
        best_s, best_d = 0.0, float("inf")
        prev_s = 0.0
        prev_pt = self._spiral_xy(prev_s, self.spiral_type)
        prev_d = math.hypot(lx - prev_pt[0], ly - prev_pt[1])

        for i in range(1, n + 1):
            s = self.length * i / n
            pt = self._spiral_xy(s, self.spiral_type)
            d = math.hypot(lx - pt[0], ly - pt[1])
            if d < best_d:
                best_s, best_d = s, d

            if prev_d < d:
                # 이분법
                lo, hi = prev_s, s
                for _ in range(40):
                    mid = 0.5 * (lo + hi)
                    mp = self._spiral_xy(mid, self.spiral_type)
                    md = math.hypot(lx - mp[0], ly - mp[1])
                    if md < best_d:
                        best_s, best_d = mid, md
                    if md > prev_d and md > d:
                        break
                    if md < prev_d:
                        prev_d, prev_s = md, mid
                        lo = mid
                    else:
                        hi = mid

            prev_s, prev_pt, prev_d = s, pt, d

        s = best_s
        proj_local = self._spiral_xy(s, self.spiral_type)
        proj_world = self._to_local_point(proj_local[0], proj_local[1])

        # offset: 로컬 점에서 프로젝션 점까지의 부호 거리
        tang = self.tangent_at(s)
        nx = -math.sin(tang)
        ny = math.cos(tang)
        dx, dy = lx - proj_local[0], ly - proj_local[1]
        offset = dx * nx + dy * ny
        distance = abs(offset)

        is_on = (0.0 <= s <= self.length)

        return ProjectionResult(
            point=proj_world,
            station=s,
            offset=offset,
            distance=distance,
            tangent=tang,
            is_on_entity=is_on,
        )

    def reversed(self) -> "SpiralGeometry":
        """뒤집힌 완화곡선."""
        new_dir = (
            CurveDirection.RIGHT if self.direction == CurveDirection.LEFT
            else CurveDirection.LEFT
        )
        theta = self._spiral_tangent(self.length)
        return SpiralGeometry(
            start_azimuth=(self.start_azimuth + theta + math.pi) % (2 * math.pi),
            params=self.params,
            direction=new_dir,
            is_reversed=not self.is_reversed,
        )

    def offset_by(self, distance: float) -> "SpiralGeometry":
        """평행 이동한 완화곡선 (반지름 변화)."""
        sign = +1.0 if self.direction == CurveDirection.LEFT else -1.0
        new_radius = self.params.radius - sign * distance
        if new_radius <= 0:
            raise ValueError(f"offset 후 반지름 ≤ 0: {new_radius}")
        new_params = SpiralParams(
            radius=new_radius,
            length=self.params.length,
            spiral_type=self.params.spiral_type,
        )
        return SpiralGeometry(
            start_azimuth=self.start_azimuth,
            params=new_params,
            direction=self.direction,
            is_reversed=self.is_reversed,
        )

    # ---- SpiralType별 로컬 좌표 ----
    def _spiral_xy(self, s: float, stype: SpiralType) -> tuple[float, float]:
        """로컬 (x, y). s는 완화곡선 시작 기준."""
        R = self.params.radius
        L = self.params.length

        if stype in (SpiralType.Clothoid, SpiralType.OffsetClothoid):
            return self._clothoid_xy(s, R, L)
        if stype in (SpiralType.JapaneseCubic, SpiralType.OffsetJapaneseCubic):
            return self._japanese_cubic_xy(s, R, L)
        if stype in (SpiralType.CubicParabola, SpiralType.OffsetCubicParabola):
            return self._cubic_parabola_xy(s, R, L)
        if stype in (SpiralType.SineHalfWave, SpiralType.OffsetHalfWaveLenDimnTangent):
            return self._sine_half_wave_xy(s, R, L)
        raise NotImplementedError(f"지원하지 않는 SpiralType: {stype}")

    @staticmethod
    def _clothoid_xy(s: float, R: float, L: float) -> tuple[float, float]:
        """클로소이드 (5차 급수)."""
        A2 = R * L
        x = s - s ** 5 / (40 * A2 ** 2) + s ** 9 / (3456 * A2 ** 4)
        y = s ** 3 / (6 * A2) - s ** 7 / (336 * A2 ** 3)
        return x, y

    @staticmethod
    def _japanese_cubic_xy(s: float, R: float, L: float) -> tuple[float, float]:
        """일본식 3차 포물선."""
        x = s - s ** 3 / (40 * R * R)  # ← 기존 solve_x1과 일관
        y = s ** 3 / (6 * R * L)
        return x, y

    @staticmethod
    def _cubic_parabola_xy(s: float, R: float, L: float) -> tuple[float, float]:
        """3차 포물선."""
        x = s
        y = s ** 3 / (6 * R * L)
        return x, y

    @staticmethod
    def _sine_half_wave_xy(s: float, R: float, L: float) -> tuple[float, float]:
        """Sine half-wave (근사)."""
        theta_max = L / (2 * R)
        x = s - (L * theta_max / (2 * math.pi)) * math.sin(2 * math.pi * s / L) / 2
        y = (L * theta_max / (2 * math.pi)) * (1 - math.cos(2 * math.pi * s / L)) / 2
        return x, y

    def _spiral_tangent(self, s: float) -> float:
        """로컬 접선각 (rad, 부호 없음)."""
        stype = self.spiral_type
        if stype in (SpiralType.Clothoid, SpiralType.OffsetClothoid):
            # θ = s² / (2·A²) = s² / (2·R·L)
            return s * s / (2 * self.params.radius * self.params.length)
        if stype in (SpiralType.JapaneseCubic, SpiralType.CubicParabola):
            # θ = s² / (2·R·L) (근사)
            return s * s / (2 * self.params.radius * self.params.length)
        if stype in (SpiralType.SineHalfWave,):
            theta_max = self.params.length / (2 * self.params.radius)
            return (theta_max / 2) * (1 - math.cos(2 * math.pi * s / self.params.length))
        raise NotImplementedError(stype)

    # ---- 로컬 변환 ----
    def _to_local_point(self, lx: float, ly: float) -> Point2d:
        ca, sa = math.cos(self.start_azimuth), math.sin(self.start_azimuth)
        return Point2d(lx * ca - ly * sa, lx * sa + ly * ca)

    def _to_local_coords(self, p: Point2d) -> tuple[float, float]:
        ca, sa = math.cos(self.start_azimuth), math.sin(self.start_azimuth)
        return (p.x * ca + p.y * sa, -p.x * sa + p.y * ca)