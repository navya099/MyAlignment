
from __future__ import annotations

from dataclasses import dataclass, replace
import math

from cadgeom import Point2d

from myalignment.turnout.turnout import Turnout
from myalignment.turnout.type import TurnoutSide
from myalignment.turnout.scissors_type import ScissorsCrossoverType
from myalignment.turnout.scissors_geometry import ScissorsCrossoverGeometry
from myalignment.turnout.scissors_validator import ScissorsCrossoverValidator
from myalignment.turnout.crossover_validator import CrossoverValidator


@dataclass(frozen=True, slots=True)
class ScissorsCrossover:
    """평행 직선 본선용 이상화 Scissors Crossover."""

    name: str = ""
    crossover_type: ScissorsCrossoverType = (
        ScissorsCrossoverType.STANDARD
    )

    turnout1: Turnout | None = None
    turnout2: Turnout | None = None
    turnout3: Turnout | None = None
    turnout4: Turnout | None = None

    source_alignment1_name: str = ""
    source_alignment2_name: str = ""

    connecting_alignment_names: tuple[str, str, str, str] = (
        "", "", "", ""
    )

    geometry: ScissorsCrossoverGeometry | None = None

    def __post_init__(self):
        if any(t is None for t in self.turnouts):
            raise ValueError("4개 턴아웃이 필요합니다")

        if (
            not self.source_alignment1_name
            or not self.source_alignment2_name
            or self.source_alignment1_name
            == self.source_alignment2_name
        ):
            raise ValueError("서로 다른 두 본선 이름이 필요합니다")

        for i, t in enumerate(self.turnouts):
            expected = (
                self.source_alignment1_name
                if i < 2
                else self.source_alignment2_name
            )
            if t.source_alignment_name != expected:
                raise ValueError(
                    f"turnout{i + 1} source alignment 불일치"
                )

        if len(self.connecting_alignment_names) != 4:
            raise ValueError("연결 선형 이름은 4개 필요합니다")

    @property
    def turnouts(self):
        return (
            self.turnout1,
            self.turnout2,
            self.turnout3,
            self.turnout4,
        )

    @staticmethod
    def _offset(point, azimuth, longitudinal, lateral):
        ca = math.cos(azimuth)
        sa = math.sin(azimuth)
        return Point2d(
            point.x + longitudinal * ca - lateral * sa,
            point.y + longitudinal * sa + lateral * ca,
        )

    @staticmethod
    def _segment(a, b):
        dx = b.x - a.x
        dy = b.y - a.y
        return math.hypot(dx, dy), math.atan2(dy, dx)

    def compute_geometry(
        self, alignment1, alignment2
    ) -> ScissorsCrossoverGeometry:

        stations = tuple(
            t.station_on_source for t in self.turnouts
        )
        sta1, sta2, sta3, sta4 = stations

        def invalid(message):
            return ScissorsCrossoverGeometry(
                turnout1_station=sta1,
                turnout2_station=sta2,
                turnout3_station=sta3,
                turnout4_station=sta4,
                is_valid=False,
                error_message=str(message),
            )

        try:
            if (
                alignment1.name != self.source_alignment1_name
                or alignment2.name != self.source_alignment2_name
            ):
                raise ValueError("입력 본선 이름 불일치")

            if any(not math.isfinite(s) for s in stations):
                raise ValueError("턴아웃 측점이 유효하지 않습니다")

            if sta1 >= sta2 or sta3 >= sta4:
                raise ValueError("턴아웃 측점 순서 오류")

            types = [t.turnout_type for t in self.turnouts]
            if any(tt != types[0] for tt in types[1:]):
                raise ValueError(
                    "현재 엔진은 동일한 TurnoutType 4개만 지원"
                )

            tt = types[0]
            theta = tt.frog_angle
            run = tt.run
            rise = tt.rise
            tol = CrossoverValidator.POSITION_TOL
            angle_tol = CrossoverValidator.ANGLE_TOL

            # 첫 번째 턴아웃 기준의 두 본선 상대 위치
            p1 = alignment1.point_at(sta1)
            p3 = alignment2.point_at(sta3)
            az = alignment1.tangent_at(sta1)

            if not math.isfinite(az):
                raise ValueError("본선 방위각이 유효하지 않습니다")

            ux, uy = math.cos(az), math.sin(az)
            nx, ny = -uy, ux

            dx = p3.x - p1.x
            dy = p3.y - p1.y
            across = dx * nx + dy * ny

            if abs(across) <= tol:
                raise ValueError("두 본선의 선간 거리가 0입니다")

            sign = 1 if across > 0 else -1
            expected_side1 = (
                TurnoutSide.LEFT
                if sign > 0 else TurnoutSide.RIGHT
            )
            expected_side2 = (
                TurnoutSide.RIGHT
                if sign > 0 else TurnoutSide.LEFT
            )

            for t in self.turnouts[:2]:
                if t.side is not expected_side1:
                    raise ValueError("본선1 분기 방향 오류")

            for t in self.turnouts[2:]:
                if t.side is not expected_side2:
                    raise ValueError("본선2 분기 방향 오류")

            # 네 턴아웃의 본선 접선 및 직선 구간 확인
            alignments = (
                alignment1, alignment1,
                alignment2, alignment2,
            )
            directions = (1, -1, 1, -1)

            toes = []
            for alignment, sta, direction in zip(
                alignments, stations, directions
            ):
                toe = alignment.point_at(sta)
                az_here = alignment.tangent_at(sta)

                if abs(
                    CrossoverValidator._normalize_angle(
                        az_here - az
                    )
                ) > angle_tol:
                    raise ValueError(
                        "턴아웃 위치의 본선 접선 방향 불일치"
                    )

                probe = alignment.point_at(
                    sta + direction * run
                )
                expected_probe = self._offset(
                    toe, az, direction * run, 0.0
                )

                if math.hypot(
                    probe.x - expected_probe.x,
                    probe.y - expected_probe.y,
                ) > tol:
                    raise ValueError(
                        "턴아웃 구간 본선이 직선이 아닙니다"
                    )

                probe_az = alignment.tangent_at(
                    sta + direction * run
                )
                if abs(
                    CrossoverValidator._normalize_angle(
                        probe_az - az
                    )
                ) > angle_tol:
                    raise ValueError(
                        "턴아웃 구간 본선 접선 방향 변화"
                    )

                toes.append(toe)

            # 실제 분기곡선 끝점
            p_t1 = self._offset(
                toes[0], az, run, sign * rise
            )
            p_t2 = self._offset(
                toes[1], az, -run, sign * rise
            )
            p_t3 = self._offset(
                toes[2], az, run, -sign * rise
            )
            p_t4 = self._offset(
                toes[3], az, -run, -sign * rise
            )

            # 두 대각 연결부
            L14, az14 = self._segment(p_t1, p_t4)
            L32, az32 = self._segment(p_t3, p_t2)

            if min(L14, L32) <= tol:
                raise ValueError("대각 연결선 길이가 부족합니다")

            expected_az14 = az + sign * theta
            expected_az32 = az - sign * theta

            if abs(
                CrossoverValidator._normalize_angle(
                    az14 - expected_az14
                )
            ) > angle_tol:
                raise ValueError(
                    "T1→T4 연결선 접선 불연속"
                )

            if abs(
                CrossoverValidator._normalize_angle(
                    az32 - expected_az32
                )
            ) > angle_tol:
                raise ValueError(
                    "T3→T2 연결선 접선 불연속"
                )

            diamond = (
                ScissorsCrossoverValidator
                ._segments_intersection_point(
                    p_t1, p_t4, p_t3, p_t2
                )
            )

            if diamond is None:
                raise ValueError("Diamond 교차부 없음")

            # 기존 DTO의 나머지 두 구간
            L12, az12 = self._segment(p_t1, p_t2)
            L34, az34 = self._segment(p_t3, p_t4)

            return ScissorsCrossoverGeometry(
                turnout1_station=sta1,
                turnout2_station=sta2,
                turnout3_station=sta3,
                turnout4_station=sta4,
                turnout1_point=p_t1,
                turnout2_point=p_t2,
                turnout3_point=p_t3,
                turnout4_point=p_t4,
                connecting_lengths=(
                    L14, L32, L12, L34
                ),
                connecting_azimuths=(
                    az14, az32, az12, az34
                ),
                diamond_center=diamond,
                diamond_diagonal1=L14,
                diamond_diagonal2=L32,
                is_valid=True,
            )

        except (
            ValueError,
            AttributeError,
            TypeError,
            IndexError,
        ) as exc:
            return invalid(exc)

    def with_geometry(self, geometry):
        return replace(self, geometry=geometry)

    @property
    def is_valid(self):
        return (
            self.geometry is not None
            and self.geometry.is_valid
        )

    @property
    def total_connecting_length(self):
        if self.geometry is None:
            return 0.0
        return self.geometry.total_connecting_length
