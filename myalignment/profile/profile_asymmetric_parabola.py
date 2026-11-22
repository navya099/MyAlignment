# profile/profile_asymmetric_parabola.py
from __future__ import annotations
from dataclasses import dataclass
import math

from myalignment.profile.profileentity import ProfileEntity
from myalignment.profile.profileentitytype import ProfileEntityType


@dataclass(frozen=True, slots=True)
class ProfileAsymmetricParabola(ProfileEntity):
    """
    비대칭 포물선 (진입/진출 길이 다름).

    C3D AsymmetricParabola 호환, 표준 도로설계(VPC/VPT 기준).
    - start_elevation/end_elevation = VPC/VPT 접선 연장 표고.
    - VPC: (PVI_station - L_in, PVI_elev - G1·L_in), 구배 G1
    - VPT: (PVI_station + L_out, PVI_elev + G2·L_out), 구배 G2
    - PVI station에서 포물선 표고 = PVI_elev + k,
      k = (G2-G1)·L_in·L_out/(2·L_total)
    - PVI station에서 포물선 구배 = (G1·L_out + G2·L_in)/L_total
    """
    entity_type: ProfileEntityType = ProfileEntityType.ParabolaAsymmetric
    _pvi_station: float = 0.0
    _pvi_elevation: float = 0.0
    _grade_in: float = 0.0
    _grade_out: float = 0.0
    _length_in: float = 0.0
    _length_out: float = 0.0

    def __post_init__(self):
        if self._length_in <= 0 or self._length_out <= 0:
            raise ValueError("length_in/out > 0 필요")
        if abs(self._grade_out - self._grade_in) < 1e-12:
            raise ValueError("grade_in == grade_out (포물선 불가)")

    # ---- 생성 ----
    @classmethod
    def create(
        cls,
        pvi_station: float,
        pvi_elevation: float,
        grade_in: float,
        grade_out: float,
        length_in: float,
        length_out: float,
    ) -> "ProfileAsymmetricParabola":
        start_sta = pvi_station - length_in
        end_sta = pvi_station + length_out
        # VPC/VPT = 접선 연장값
        start_elev = pvi_elevation - grade_in * length_in
        end_elev = pvi_elevation + grade_out * length_out
        return cls(
            start_station=start_sta,
            end_station=end_sta,
            start_elevation=start_elev,
            end_elevation=end_elev,
            _pvi_station=pvi_station,
            _pvi_elevation=pvi_elevation,
            _grade_in=grade_in,
            _grade_out=grade_out,
            _length_in=length_in,
            _length_out=length_out,
        )

    # ---- 속성 ----
    @property
    def total_length(self) -> float:
        return self._length_in + self._length_out

    @property
    def k_value(self) -> float:
        """K = L_total / (G_out - G_in)."""
        return self.total_length / (self._grade_out - self._grade_in)

    @property
    def pvi_station(self) -> float:
        return self._pvi_station

    @property
    def pvi_elevation(self) -> float:
        return self._pvi_elevation

    # ---- 내부 헬퍼 ----
    def _vpc_station(self) -> float:
        return self._pvi_station - self._length_in

    def _vpc_elevation(self) -> float:
        return self._pvi_elevation - self._grade_in * self._length_in

    def _u(self, station: float) -> float:
        return self._clamp_station(station) - self._vpc_station()

    def _k(self) -> float:
        """PVI station에서의 포물선 offset."""
        L = self.total_length
        return (self._grade_out - self._grade_in) * self._length_in * self._length_out / (2.0 * L)

    # ---- 표고/구배 (VPC 기준) ----
    def elevation_at(self, station: float) -> float:
        u = self._u(station)
        L_in, L_out = self._length_in, self._length_out
        L = self.total_length
        k = self._k()

        if u <= L_in:
            # 진입 구간: a_in = k / L_in²
            a_in = k / (L_in * L_in)
            return self._vpc_elevation() + self._grade_in * u + a_in * u * u
        else:
            # 진출 구간: VPT 기준으로 계산
            v = L - u  # VPT로부터의 거리 (0 ≤ v ≤ L_out)
            a_out = k / (L_out * L_out)
            return self.end_elevation - self._grade_out * v + a_out * v * v

    def grade_at(self, station: float) -> float:
        u = self._u(station)
        L_in, L_out = self._length_in, self._length_out
        L = self.total_length
        k = self._k()

        if u <= L_in:
            a_in = k / (L_in * L_in)
            return self._grade_in + 2.0 * a_in * u
        else:
            v = L - u
            a_out = k / (L_out * L_out)
            return self._grade_out - 2.0 * a_out * v

    # ---- 유틸 ----
    def extremum_station(self) -> float | None:
        """곡선 내부에서 구배가 0이 되는 station (없으면 None)."""
        L_in, L_out = self._length_in, self._length_out
        L = self.total_length
        k = self._k()
        if self._grade_in * self._grade_out < 0 and math.isclose(
            self.grade_at(self.pvi_station), 0.0, rel_tol=0.0, abs_tol=1e-12
        ):
            return self.pvi_station

        # 진입 구간: G1 + 2·a_in·u = 0 → u = -G1·L_in²/(2k)
        if abs(k) > 1e-15:
            u_in = -self._grade_in * L_in * L_in / (2.0 * k)
            if 0 < u_in < L_in:
                return self._vpc_station() + u_in
            # 진출 구간: G2 - 2·a_out·v = 0 → v = G2·L_out²/(2k)
            v_out = self._grade_out * L_out * L_out / (2.0 * k)
            if 0 < v_out < L_out:
                return self._vpc_station() + (L - v_out)
        return None

    def pvi_stations(self) -> tuple[float, ...]:
        return (self._pvi_station,)

    # ---- 반전 ----
    def reversed(self, total_length: float) -> "ProfileAsymmetricParabola":
        L = total_length
        new_pvi_station = L - self._pvi_station
        new_length_in = self._length_out
        new_length_out = self._length_in
        new_grade_in = -self._grade_out
        new_grade_out = -self._grade_in

        # VPC' = 원본 VPT, VPT' = 원본 VPC
        new_start_elev = self.end_elevation
        new_end_elev = self.start_elevation

        # PVI' = VPC' + G_in'·L_in'
        new_pvi_elev = new_start_elev + new_grade_in * new_length_in

        return ProfileAsymmetricParabola(
            start_station=L - self.end_station,
            end_station=L - self.start_station,
            start_elevation=new_start_elev,
            end_elevation=new_end_elev,
            _pvi_station=new_pvi_station,
            _pvi_elevation=new_pvi_elev,
            _grade_in=new_grade_in,
            _grade_out=new_grade_out,
            _length_in=new_length_in,
            _length_out=new_length_out,
        )