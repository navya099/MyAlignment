
from __future__ import annotations

from dataclasses import dataclass
import math

from cadgeom import Point2d


@dataclass(frozen=True, slots=True)
class ScissorsCrossoverGeometry:
    """Scissors Crossover SIMPLE 기하 계산 결과."""

    # 4개 턴아웃 시작 측점
    turnout1_station: float = 0.0
    turnout2_station: float = 0.0
    turnout3_station: float = 0.0
    turnout4_station: float = 0.0

    # 연결부 끝점 (월드 좌표)
    turnout1_point: Point2d | None = None
    turnout2_point: Point2d | None = None
    turnout3_point: Point2d | None = None
    turnout4_point: Point2d | None = None

    # 순서: T1→T4, T3→T2, T1→T2, T3→T4
    connecting_lengths: tuple[float, float, float, float] = (
        0.0, 0.0, 0.0, 0.0
    )
    connecting_azimuths: tuple[float, float, float, float] = (
        0.0, 0.0, 0.0, 0.0
    )

    # 두 대각 연결부의 교차점
    diamond_center: Point2d | None = None

    # 기존 필드명 유지
    # 현재 의미: 대각 연결부 전체 길이
    diamond_diagonal1: float = 0.0
    diamond_diagonal2: float = 0.0

    is_valid: bool = True
    error_message: str = ""

    def __post_init__(self):
        if not self.is_valid and not self.error_message:
            raise ValueError(
                "is_valid=False인데 error_message 없음"
            )

        if len(self.connecting_lengths) != 4:
            raise ValueError(
                "connecting_lengths는 4개여야 합니다"
            )

        if len(self.connecting_azimuths) != 4:
            raise ValueError(
                "connecting_azimuths는 4개여야 합니다"
            )

        if any(
            not math.isfinite(v) or v < 0
            for v in self.connecting_lengths
        ):
            raise ValueError(
                "연결 길이는 유한한 0 이상의 값이어야 합니다"
            )

        if any(
            not math.isfinite(v)
            for v in self.connecting_azimuths
        ):
            raise ValueError(
                "연결 방위각은 유한한 값이어야 합니다"
            )

    @property
    def total_connecting_length(self) -> float:
        return sum(self.connecting_lengths)

    def __repr__(self) -> str:
        status = (
            "OK" if self.is_valid
            else f"INVALID({self.error_message})"
        )
        return (
            f"ScissorsGeometry({status}, "
            f"4턴아웃, "
            f"L_total={self.total_connecting_length:.2f}m, "
            f"diamond=("
            f"{self.diamond_diagonal1:.1f}×"
            f"{self.diamond_diagonal2:.1f})m)"
        )
