import math
from myalignment.turnout.type import TurnoutSide

class CrossoverValidator:
    PARALLEL_TOL = math.radians(0.5)
    POSITION_TOL = 1e-3
    ANGLE_TOL = 1e-5

    @staticmethod
    def _normalize_angle(angle):
        return (angle + math.pi) % (2 * math.pi) - math.pi

    @staticmethod
    def inspect(alignment1, alignment2, station1, station2):
        p1, p2 = alignment1.point_at(station1), alignment2.point_at(station2)
        a1, a2 = alignment1.tangent_at(station1), alignment2.tangent_at(station2)
        if abs(CrossoverValidator._normalize_angle(a2-a1)) > CrossoverValidator.PARALLEL_TOL:
            raise ValueError('본선 접선이 평행하지 않습니다 (현재 모델은 평행 직선만 지원)')
        ux, uy = math.cos(a1), math.sin(a1)
        dx, dy = p2.x-p1.x, p2.y-p1.y
        along, across = dx*ux+dy*uy, -dx*uy+dy*ux
        if abs(across) <= CrossoverValidator.POSITION_TOL:
            raise ValueError('두 본선의 횡방향 간격이 0에 가깝습니다')
        return p1, p2, a1, along, across

    @staticmethod
    def validate(alignment1, alignment2, t1_lead_length, t2_lead_length, station1, station2):
        # Compatibility shim; this checks alignment context only, not turnout feasibility.
        try:
            CrossoverValidator.inspect(alignment1, alignment2, station1, station2)
            return True, ''
        except (ValueError, AttributeError, TypeError) as exc:
            return False, str(exc)

    @staticmethod
    def validate_direction(alignment1, alignment2, station1, station2, t1_side, t2_side):
        try:
            _, _, _, _, across = CrossoverValidator.inspect(alignment1, alignment2, station1, station2)
            expected1 = TurnoutSide.LEFT if across > 0 else TurnoutSide.RIGHT
            expected2 = TurnoutSide.RIGHT if across > 0 else TurnoutSide.LEFT
            if t1_side is not expected1 or t2_side is not expected2:
                return False, f'분기 방향 오류: 첫 번째={expected1.value}, 두 번째={expected2.value} 필요'
            return True, ''
        except (ValueError, AttributeError, TypeError) as exc:
            return False, str(exc)
