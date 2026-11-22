# profile/profile_symmetric_parabola.py
from __future__ import annotations
from dataclasses import dataclass

from myalignment.profile.profileentity import ProfileEntity
from myalignment.profile.profileentitytype import ProfileEntityType


@dataclass(frozen=True, slots=True)
class ProfileSymmetricParabola(ProfileEntity):
    """
    대칭 포물선 종단 요소 (C3D SymmetricParabola 호환, 표준 도로설계).

    - **VPC/VPT 기준** 공식.
    - start_elevation/end_elevation = VPC/VPT의 **접선 연장 표고**.
    - PVI는 두 접선의 교점이며, PVI station에서의 포물선 표고는
      PVI_elevation과 다르다 (= PVI_elev + (G_out - G_in)·L/8).
    - PVI station에서의 포물선 구배 = (G_in + G_out) / 2.
    - K = L / (G_out - G_in)
    """
    entity_type: ProfileEntityType = ProfileEntityType.ParabolaSymmetric
    _pvi_station: float = 0.0
    _pvi_elevation: float = 0.0
    _grade_in: float = 0.0
    _grade_out: float = 0.0
    _curve_length: float = 0.0

    def __post_init__(self):
        if self._curve_length <= 0:
            raise ValueError(f"curve_length > 0 필요: {self._curve_length}")
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
        curve_length: float,
    ) -> "ProfileSymmetricParabola":
        """
        PVI(두 접선의 교점) 기준 대칭 포물선 생성.

        VPC/VPT의 표고는 접선 연장값으로 저장된다:
            start_elevation = pvi_elevation - grade_in  * (L/2)
            end_elevation   = pvi_elevation + grade_out * (L/2)
        """
        half = curve_length / 2.0
        start_sta = pvi_station - half
        end_sta = pvi_station + half
        start_elev = pvi_elevation - grade_in * half
        end_elev = pvi_elevation + grade_out * half

        return cls(
            start_station=start_sta,
            end_station=end_sta,
            start_elevation=start_elev,
            end_elevation=end_elev,
            _pvi_station=pvi_station,
            _pvi_elevation=pvi_elevation,
            _grade_in=grade_in,
            _grade_out=grade_out,
            _curve_length=curve_length,
        )

    # ---- 속성 ----
    @property
    def k_value(self) -> float:
        """K = L / (G_out - G_in)."""
        return self._curve_length / (self._grade_out - self._grade_in)

    @property
    def pvi_station(self) -> float:
        return self._pvi_station

    @property
    def pvi_elevation(self) -> float:
        return self._pvi_elevation

    # ---- 내부 헬퍼 ----
    def _vpc_station(self) -> float:
        return self._pvi_station - self._curve_length / 2.0

    def _u(self, station: float) -> float:
        """VPC로부터의 거리 u (0 ≤ u ≤ L)."""
        return self._clamp_station(station) - self._vpc_station()

    def _vpc_elevation(self) -> float:
        return self._pvi_elevation - self._grade_in * self._curve_length / 2.0

    # ---- 표고/구배 (VPC 기준 표준 공식) ----
    def elevation_at(self, station: float) -> float:
        u = self._u(station)
        return (
            self._vpc_elevation()
            + self._grade_in * u
            + (self._grade_out - self._grade_in) * u * u
              / (2.0 * self._curve_length)
        )

    def grade_at(self, station: float) -> float:
        u = self._u(station)
        return (
            self._grade_in
            + (self._grade_out - self._grade_in) * u / self._curve_length
        )

    # ---- 유틸 ----
    def extremum_station(self) -> float | None:
        """곡선 내부에서 구배가 0이 되는 station (없으면 None)."""
        denom = self._grade_out - self._grade_in
        if abs(denom) < 1e-12:
            return None
        u = -self._grade_in * self._curve_length / denom
        sta = self._vpc_station() + u
        if self.start_station < sta < self.end_station:
            return sta
        return None

    def pvi_stations(self) -> tuple[float, ...]:
        """이 엔티티가 정의하는 PVI station."""
        return (self._pvi_station,)

    # ---- 반전 ----
    def reversed(self, total_length: float) -> "ProfileSymmetricParabola":
        L = total_length
        half = self._curve_length / 2.0

        new_pvi_station = L - self._pvi_station
        new_grade_in = -self._grade_out
        new_grade_out = -self._grade_in

        # 반전 후 VPC = 원본 VPT. 그 표고는 원본 end_elevation.
        new_vpc_elev = self.end_elevation
        # PVI 표고는 접선 연장으로 역산 (VPC + G_in' · half)
        new_pvi_elev = new_vpc_elev + new_grade_in * half

        return ProfileSymmetricParabola.create(
            pvi_station=new_pvi_station,
            pvi_elevation=new_pvi_elev,
            grade_in=new_grade_in,
            grade_out=new_grade_out,
            curve_length=self._curve_length,
        )