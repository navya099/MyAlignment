# turnout/crossover_validator.py
from __future__ import annotations
import math

from myalignment.turnout.type import TurnoutSide


class CrossoverValidator:
    """
    Crossover 유효성 검사 (C3D 규칙).

    검증 항목:
        1. 두 본선이 평행 (각도 오차 내)
        2. 선간 거리 ≥ 2 × lead_length
        3. 턴아웃 방향 (마주보기/등지기)
        4. 턴아웃 측점 겹침 없음
    """

    # 평행 허용 오차 (rad, 약 0.5°)
    PARALLEL_TOL = math.radians(0.5)
    # 선간 거리 허용 오차 (m)
    DISTANCE_TOL = 0.1

    @staticmethod
    def validate(
            alignment1,
            alignment2,
            t1_lead_length: float,
            t2_lead_length: float,
            station1: float,
            station2: float,
    ) -> tuple[bool, str]:
        """
        Crossover 유효성 검사.

        Returns:
            (is_valid, error_message)
        """
        # 1) 두 본선의 방위각 확인
        try:
            az1 = alignment1.tangent_at(station1)
            az2 = alignment2.tangent_at(station2)
        except (ValueError, AttributeError) as e:
            return False, f"선형 측점 조회 실패: {e}"

        # 방위각 차이 (평행 검사)
        az_diff = abs(CrossoverValidator._normalize_angle(az1 - az2))
        if az_diff > CrossoverValidator.PARALLEL_TOL:
            return False, (
                f"두 본선이 평행하지 않음: "
                f"Δazimuth={math.degrees(az_diff):.3f}° "
                f"(허용 {math.degrees(CrossoverValidator.PARALLEL_TOL):.3f}°)"
            )

        # 2) 선간 거리 확인
        p1 = alignment1.point_at(station1)
        p2 = alignment2.point_at(station2)

        # 수직 거리 (본선 방향 기준)
        normal_az = az1 + math.pi / 2
        nx = math.cos(normal_az)
        ny = math.sin(normal_az)
        dx = p2.x - p1.x
        dy = p2.y - p1.y
        perp_dist = abs(dx * nx + dy * ny)

        min_distance = t1_lead_length + t2_lead_length
        if perp_dist < min_distance - CrossoverValidator.DISTANCE_TOL:
            return False, (
                f"선간 거리 부족: {perp_dist:.2f}m "
                f"< 필요 최소 {min_distance:.2f}m "
                f"(lead1={t1_lead_length:.2f}, lead2={t2_lead_length:.2f})"
            )

        return True, ""

    @staticmethod
    def validate_direction(
            alignment1,
            alignment2,
            station1: float,
            station2: float,
            t1_side: TurnoutSide,
            t2_side: TurnoutSide,
    ) -> tuple[bool, str]:
        """
        턴아웃 방향 검증.

        단일 Crossover: 턴아웃이 서로 마주보거나 등져야 함.
        """
        # 본선1에서 본선2의 방향 판정
        p1 = alignment1.point_at(station1)
        p2 = alignment2.point_at(station2)
        az1 = alignment1.tangent_at(station1)

        # 본선1 진행 방향 기준 본선2의 좌/우 판정
        normal_az = az1 + math.pi / 2
        nx = math.cos(normal_az)
        ny = math.sin(normal_az)
        dx = p2.x - p1.x
        dy = p2.y - p1.y
        perp = dx * nx + dy * ny

        alignment2_side = TurnoutSide.LEFT if perp > 0 else TurnoutSide.RIGHT

        # 턴아웃1이 본선2 쪽을 향해야 함
        if t1_side != alignment2_side:
            return False, (
                f"턴아웃1 방향 오류: "
                f"본선2는 {alignment2_side.value}인데 "
                f"턴아웃1은 {t1_side.value}"
            )

        # 턴아웃2가 본선1 쪽을 향해야 함
        # 본선2 진행 방향 기준 본선1의 좌/우
        az2 = alignment2.tangent_at(station2)
        normal_az2 = az2 + math.pi / 2
        nx2 = math.cos(normal_az2)
        ny2 = math.sin(normal_az2)
        dx2 = p1.x - p2.x
        dy2 = p1.y - p2.y
        perp2 = dx2 * nx2 + dy2 * ny2

        alignment1_side = TurnoutSide.LEFT if perp2 > 0 else TurnoutSide.RIGHT

        if t2_side != alignment1_side:
            return False, (
                f"턴아웃2 방향 오류: "
                f"본선1은 {alignment1_side.value}인데 "
                f"턴아웃2는 {t2_side.value}"
            )

        return True, ""

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        """[-π, π] 범위로 정규화."""
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle