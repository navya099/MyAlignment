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

    def _centerline(self, s: float) -> tuple[float, float]:
        sign = 1 if self.direction == CurveDirection.LEFT else -1
        if not self.is_reversed:
            x, y = self._spiral_xy(s, self.spiral_type)
            return x, sign * y

        # 역방향 곡선은 반대쪽 끝에서 같은 궤적을 거슬러 올라간다.
        end_x, end_y = self._spiral_xy(self.length, self.spiral_type)
        x, y = self._spiral_xy(self.length - s, self.spiral_type)
        angle = sign * self._spiral_tangent(self.length)
        dx, dy = end_x - x, -sign * (end_y - y)
        ca, sa = math.cos(angle), math.sin(angle)
        return dx * ca - dy * sa, dx * sa + dy * ca

    def point_at(self, s: float, offset: float = 0.0) -> Point2d:
        s = self._check_s(s)
        x, y = self._centerline(s)
        angle = self.tangent_at(s) - self.start_azimuth
        return self._to_local_point(x + offset * math.sin(angle), y - offset * math.cos(angle))

    def tangent_at(self, s: float) -> float:
        s = self._check_s(s)
        sign = 1 if self.direction == CurveDirection.LEFT else -1
        if self.is_reversed:
            angle = self._spiral_tangent(self.length) - self._spiral_tangent(self.length - s)
        else:
            angle = self._spiral_tangent(s)
        return self.start_azimuth + sign * angle

    def project_at(self, p: Point2d) -> ProjectionResult:
        """동일한 중심선에서 최근접 측점을 수치적으로 찾는다."""
        lx, ly = self._to_local_coords(p)

        def distance(s):
            x, y = self._centerline(s)
            return math.hypot(lx - x, ly - y)

        samples = [self.length * i / 100 for i in range(101)]
        best = min(range(len(samples)), key=lambda i: distance(samples[i]))
        lo, hi = samples[max(0, best - 1)], samples[min(100, best + 1)]
        for _ in range(65):
            a, b = lo + (hi - lo) / 3, hi - (hi - lo) / 3
            if distance(a) <= distance(b):
                hi = b
            else:
                lo = a
        s = min((samples[best], (lo + hi) / 2), key=distance)
        px, py = self._centerline(s)
        dx, dy = lx - px, ly - py
        tangent = self.tangent_at(s)
        angle = tangent - self.start_azimuth
        along = dx * math.cos(angle) + dy * math.sin(angle)
        on_entity = not ((s == 0 and along < -1e-9) or (s == self.length and along > 1e-9))
        return ProjectionResult(
            point=self._to_local_point(px, py), station=s,
            offset=dx * math.sin(angle) - dy * math.cos(angle),
            distance=math.hypot(dx, dy), tangent=tangent, is_on_entity=on_entity,
        )

    def reversed(self) -> "SpiralGeometry":
        direction = CurveDirection.RIGHT if self.direction == CurveDirection.LEFT else CurveDirection.LEFT
        return SpiralGeometry(
            start_azimuth=(self.tangent_at(self.length) + math.pi) % math.tau,
            params=self.params, direction=direction, is_reversed=not self.is_reversed,
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
        kind = self.spiral_type
        radius, length = self.radius, self.length
        if kind in (SpiralType.Clothoid, SpiralType.OffsetClothoid):
            angle = s * s / (2 * radius * length)
            dx = 1 - angle ** 2 / 2 + angle ** 4 / 24
            dy = angle - angle ** 3 / 6
        elif kind in (SpiralType.JapaneseCubic, SpiralType.OffsetJapaneseCubic):
            dx = 1 - 3 * s ** 2 / (40 * radius ** 2)
            dy = s ** 2 / (2 * radius * length)
        elif kind in (SpiralType.CubicParabola, SpiralType.OffsetCubicParabola):
            dx, dy = 1, s ** 2 / (2 * radius * length)
        elif kind in (SpiralType.SineHalfWave, SpiralType.OffsetHalfWaveLenDimnTangent):
            phase = math.tau * s / length
            amplitude = length / (4 * radius)
            dx, dy = 1 - amplitude * math.cos(phase), amplitude * math.sin(phase)
        else:
            raise NotImplementedError(kind)
        return math.atan2(dy, dx)

    # ---- 로컬 변환 ----
    def _to_local_point(self, lx: float, ly: float) -> Point2d:
        ca, sa = math.cos(self.start_azimuth), math.sin(self.start_azimuth)
        return Point2d(lx * ca - ly * sa, lx * sa + ly * ca)

    def _to_local_coords(self, p: Point2d) -> tuple[float, float]:
        ca, sa = math.cos(self.start_azimuth), math.sin(self.start_azimuth)
        return (p.x * ca + p.y * sa, -p.x * sa + p.y * ca)