from __future__ import annotations
from dataclasses import dataclass, field, replace
import math
from myalignment.turnout.crossover_geometry import CrossoverGeometry, ConnectionGeometry
from myalignment.turnout.crossover_type import CrossoverType
from myalignment.turnout.crossover_validator import CrossoverValidator
from myalignment.turnout.turnout import Turnout
from myalignment.turnout.type import TurnoutSide

@dataclass(frozen=True, slots=True)
class XY:
    x: float
    y: float

@dataclass(frozen=True, slots=True)
class Crossover:
    name: str = ''
    crossover_type: CrossoverType = CrossoverType.SINGLE
    turnout1: Turnout | None = None
    turnout2: Turnout | None = None
    source_alignment1_name: str = ''
    source_alignment2_name: str = ''
    connecting_alignment_name: str = ''
    geometry: CrossoverGeometry | None = None
    additional_turnouts: tuple[Turnout, ...] = field(default_factory=tuple)

    def __post_init__(self):
        if self.turnout1 is None or self.turnout2 is None:
            raise ValueError('two turnouts required')
        if self.turnout1.source_alignment_name != self.source_alignment1_name:
            raise ValueError('turnout1 source alignment mismatch')
        if self.turnout2.source_alignment_name != self.source_alignment2_name:
            raise ValueError('turnout2 source alignment mismatch')
        if self.crossover_type is CrossoverType.DOUBLE and len(self.additional_turnouts) != 2:
            raise ValueError('DOUBLE requires four turnouts')

    @property
    def turnouts(self):
        return (self.turnout1, self.turnout2) + self.additional_turnouts

    @staticmethod
    def _offset(point, az, longitudinal, lateral):
        ca, sa = math.cos(az), math.sin(az)
        return XY(point.x + longitudinal*ca-lateral*sa,
                  point.y + longitudinal*sa+lateral*ca)

    @staticmethod
    def _invalid(sta1, sta2, message, required=0.0):
        return CrossoverGeometry(turnout1_station=sta1, turnout2_station=sta2,
                                 required_station_delta=required, is_valid=False,
                                 error_message=message)

    def compute_geometry(self, alignment1, alignment2) -> CrossoverGeometry:
        """Idealized parallel-straight crossover with circular turnout arcs.

        Each turnout has straight approach lead_length then a radius-R arc through
        atan(1/N). Second turnout is traversed in the trailing direction.
        Connecting segment must be straight and tangent at both ends.
        This is NOT a certified turnout catalogue or physical clearance check.
        """
        sta1, sta2 = self.turnout1.station_on_source, self.turnout2.station_on_source
        if self.crossover_type is CrossoverType.SCISSORS:
            return self._invalid(sta1, sta2, 'SCISSORS not implemented')
        try:
            p1, p2, az, along, across = CrossoverValidator.inspect(alignment1, alignment2, sta1, sta2)
            tt1, tt2 = self.turnout1.turnout_type, self.turnout2.turnout_type
            if tt1 != tt2:
                raise ValueError('현재 기하 엔진은 양쪽에 동일한 TurnoutType만 지원합니다')
            tt = tt1
            expected1 = TurnoutSide.LEFT if across > 0 else TurnoutSide.RIGHT
            expected2 = TurnoutSide.RIGHT if across > 0 else TurnoutSide.LEFT
            if self.turnout1.side is not expected1 or self.turnout2.side is not expected2:
                raise ValueError(f'분기 방향 오류: T1={expected1.value}, T2={expected2.value} 필요')
            theta = tt.frog_angle
            rise, run = tt.rise, tt.run
            spacing = abs(across)
            remaining = spacing - 2*rise
            if remaining < -CrossoverValidator.POSITION_TOL:
                raise ValueError(f'분기곡선 횡변위 과다: 선간 {spacing:.3f}m < 2×곡선 횡변위 {2*rise:.3f}m')
            straight_length = max(0.0, remaining / math.sin(theta))
            required_along = 2*run + straight_length*math.cos(theta)
            # along is toe2-to-toe1 projection. For parallel straight lines this
            # equals station delta when both station origins match.
            if abs(along-required_along) > CrossoverValidator.POSITION_TOL:
                raise ValueError(f'턴아웃 배치 불일치: 실제 종방향 거리 {along:.3f}m, '
                                 f'필요 {required_along:.3f}m (STA2 조정 참고: '
                                 f'{sta2 + required_along-along:.3f})')
            # Ensure source alignments are straight over the turnout extents.
            # Check toe and branch-end projected points against source tangent.
            for alignment, sta, direction in ((alignment1, sta1, 1), (alignment2, sta2, -1)):
                probe = alignment.point_at(sta + direction*run)
                base = alignment.point_at(sta)
                expected = self._offset(base, az, direction*run, 0)
                if math.hypot(probe.x-expected.x, probe.y-expected.y) > CrossoverValidator.POSITION_TOL:
                    raise ValueError('분기기 구간 본선이 직선이 아닙니다')
                a_probe = alignment.tangent_at(sta + direction*run)
                if abs(CrossoverValidator._normalize_angle(a_probe-az)) > CrossoverValidator.ANGLE_TOL:
                    raise ValueError('분기기 구간 접선 방향이 변합니다')
            sign = expected1.sign
            start = self._offset(p1, az, run, sign*rise)
            end = self._offset(p2, az, -run, -sign*rise)
            def connection(name, a, b, side_sign):
                dx, dy = b.x-a.x, b.y-a.y
                length = math.hypot(dx, dy)
                heading = math.atan2(dy, dx)
                expected_heading = az + side_sign*theta
                if abs(CrossoverValidator._normalize_angle(heading-expected_heading)) > CrossoverValidator.ANGLE_TOL:
                    raise ValueError(f'{name} 연결선 접선 불연속')
                return ConnectionGeometry(name, a, b, expected_heading,
                                          expected_heading, length, sta1, sta2)
            conn1 = connection(self.connecting_alignment_name, start, end, sign)
            connections = [conn1]
            if self.crossover_type is CrossoverType.DOUBLE:
                t3, t4 = self.additional_turnouts
                if (t3.station_on_source != sta1 or t4.station_on_source != sta2 or
                    t3.side is not expected2 or t4.side is not expected1):
                    raise ValueError('DOUBLE 보조 턴아웃의 측점 또는 방향 불일치')
                upper_start = alignment2.point_at(sta1)
                lower_end = alignment1.point_at(sta2)
                a = self._offset(upper_start, az, run, -sign*rise)
                b = self._offset(lower_end, az, -run, sign*rise)
                connections.append(connection(f'{self.name}_Conn2', a, b, -sign))
            return CrossoverGeometry(turnout1_station=sta1, turnout1_point=start,
                                     turnout1_azimuth=conn1.start_azimuth,
                                     turnout2_station=sta2, turnout2_point=end,
                                     turnout2_azimuth=conn1.end_azimuth,
                                     connecting_length=conn1.length,
                                     connecting_azimuth=conn1.start_azimuth,
                                     connections=tuple(connections),
                                     required_station_delta=required_along,
                                     is_valid=True)
        except (ValueError, AttributeError, TypeError) as exc:
            # Keep required delta visible even on station placement failure.
            return self._invalid(sta1, sta2, str(exc),
                                 locals().get('required_along', 0.0))

    @classmethod
    def double_crossover(cls, name, alignment1_name, alignment2_name, turnout_type,
                         station1, station2, connecting_length=0.0,
                         side1=TurnoutSide.LEFT, side2=TurnoutSide.RIGHT):
        from myalignment.turnout.crossover_builder import CrossoverBuilder
        return (CrossoverBuilder(name).with_alignments(alignment1_name, alignment2_name)
                .with_turnout_type(turnout_type).at_stations(station1, station2)
                .with_sides(side1, side2).as_double().build())

    def with_geometry(self, geometry):
        return replace(self, geometry=geometry)

    @property
    def is_valid(self):
        return self.geometry is not None and self.geometry.is_valid

    @property
    def connecting_length(self):
        return self.geometry.connecting_length if self.geometry else 0.0
