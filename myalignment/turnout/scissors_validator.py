
from __future__ import annotations

import math

from cadgeom import Point2d

from myalignment.turnout.crossover_validator import CrossoverValidator


class ScissorsCrossoverValidator:
    """
    Scissors Crossover SIMPLE 기하 검증.

    현재 지원:
    - 동일한 진행 방향의 평행 본선
    - 유효한 STA 및 lead_length
    - 직선 연결부의 내부 교차
    - Diamond 중심 좌표 계산

    아직 지원하지 않음:
    - 실제 턴아웃 분기곡선
    - 연결부 접선 연속성
    - Diamond 상세 치수 및 궤도 간섭
    """

    POSITION_TOL = CrossoverValidator.POSITION_TOL

    @staticmethod
    def _cross(o, a, b) -> float:
        return (
            (a.x - o.x) * (b.y - o.y)
            - (a.y - o.y) * (b.x - o.x)
        )

    @staticmethod
    def _segments_intersection_point(
        p1, p2, p3, p4
    ) -> Point2d | None:
        """
        선분 p1→p2, p3→p4의 내부 교차점.

        평행, 공선, 끝점 접촉은 교차로 인정하지 않는다.
        """
        rx = p2.x - p1.x
        ry = p2.y - p1.y

        sx = p4.x - p3.x
        sy = p4.y - p3.y

        denominator = rx * sy - ry * sx

        len_r = math.hypot(rx, ry)
        len_s = math.hypot(sx, sy)

        if (
            not math.isfinite(len_r)
            or not math.isfinite(len_s)
            or len_r <= 0
            or len_s <= 0
        ):
            return None

        # 무차원 평행 판정
        if abs(denominator) <= 1e-12 * len_r * len_s:
            return None

        qpx = p3.x - p1.x
        qpy = p3.y - p1.y

        t = (qpx * sy - qpy * sx) / denominator
        u = (qpx * ry - qpy * rx) / denominator

        # 끝점 제외. 허용오차를 각 선분 길이로 정규화.
        eps_t = min(0.25, ScissorsCrossoverValidator.POSITION_TOL / len_r)
        eps_u = min(0.25, ScissorsCrossoverValidator.POSITION_TOL / len_s)

        if not (eps_t < t < 1.0 - eps_t):
            return None

        if not (eps_u < u < 1.0 - eps_u):
            return None

        return Point2d(
            p1.x + t * rx,
            p1.y + t * ry,
        )

    @staticmethod
    def _segments_intersect(p1, p2, p3, p4) -> bool:
        """기존 API 호환용 교차 여부 판정."""
        return (
            ScissorsCrossoverValidator._segments_intersection_point(
                p1, p2, p3, p4
            )
            is not None
        )

    @staticmethod
    def validate(
        alignment1,
        alignment2,
        lead_lengths: tuple[float, float, float, float],
        stations: tuple[float, float, float, float],
    ) -> tuple[bool, str]:
        """
        Scissors SIMPLE 배치 검증.

        주의:
        lead_length를 이용한 연결점 계산은 원본 SIMPLE
        모델의 임시 규약이다.

        실제 턴아웃의 분기곡선 끝점은 SC-3에서 계산한다.
        """
        try:
            if len(stations) != 4 or len(lead_lengths) != 4:
                return False, "측점과 리드 길이는 각각 4개 필요"

            if any(not math.isfinite(s) for s in stations):
                return False, "측점에 유한하지 않은 값이 있습니다"

            if any(
                not math.isfinite(length) or length < 0
                for length in lead_lengths
            ):
                return False, "리드 길이는 유한한 0 이상의 값이어야 합니다"

            sta1, sta2, sta3, sta4 = stations
            l1, l2, l3, l4 = lead_lengths

            if sta1 >= sta2:
                return False, "본선1 턴아웃 측점 순서 오류"

            if sta3 >= sta4:
                return False, "본선2 턴아웃 측점 순서 오류"

            # 원본 SIMPLE 모델의 연결점 측점
            s_t1 = sta1 + l1
            s_t2 = sta2 - l2
            s_t3 = sta3 + l3
            s_t4 = sta4 - l4

            if s_t1 >= s_t2:
                return False, "본선1 연결점 순서 오류"

            if s_t3 >= s_t4:
                return False, "본선2 연결점 순서 오류"

            az1 = alignment1.tangent_at(sta1)
            az2 = alignment2.tangent_at(sta3)

            if not math.isfinite(az1) or not math.isfinite(az2):
                return False, "본선 접선 방위각이 유효하지 않습니다"

            diff = abs(
                CrossoverValidator._normalize_angle(az1 - az2)
            )

            if diff > CrossoverValidator.PARALLEL_TOL:
                return False, (
                    "두 본선이 같은 방향으로 평행하지 않음: "
                    f"Δazimuth={math.degrees(diff):.3f}°"
                )

            p_t1 = alignment1.point_at(s_t1)
            p_t2 = alignment1.point_at(s_t2)
            p_t3 = alignment2.point_at(s_t3)
            p_t4 = alignment2.point_at(s_t4)

            points = (p_t1, p_t2, p_t3, p_t4)

            if any(
                not math.isfinite(v)
                for p in points
                for v in (p.x, p.y)
            ):
                return False, "연결점 좌표가 유효하지 않습니다"

            # 두 대각 연결부의 교차점
            diamond = (
                ScissorsCrossoverValidator._segments_intersection_point(
                    p_t1, p_t4, p_t3, p_t2
                )
            )

            if diamond is None:
                return False, "Diamond 교차부 없음"

            return True, ""

        except (ValueError, AttributeError, TypeError, IndexError) as exc:
            return False, f"Scissors 기하 검증 실패: {exc}"
