# turnout/crossover_geometry.py
from __future__ import annotations
from dataclasses import dataclass, field
import math

from cadgeom import Point2d


@dataclass(frozen=True, slots=True)
class CrossoverGeometry:
    """
    Crossover 기하 계산 결과 (불변).

    - 두 본선의 턴아웃 시작점
    - 연결 선형의 시작/끝점
    - 연결 선형 길이/방위각
    """
    # 턴아웃1 (본선1 → 연결)
    turnout1_station: float = 0.0  # 본선1 위 측점
    turnout1_point: Point2d = None  # 월드 좌표
    turnout1_azimuth: float = 0.0  # 분기 방위각

    # 턴아웃2 (연결 → 본선2)
    turnout2_station: float = 0.0  # 본선2 위 측점
    turnout2_point: Point2d = None  # 월드 좌표
    turnout2_azimuth: float = 0.0  # 합류 방위각

    # 연결 선형
    connecting_length: float = 0.0
    connecting_azimuth: float = 0.0

    # 검증
    is_valid: bool = True
    error_message: str = ""

    def __post_init__(self):
        if not self.is_valid and not self.error_message:
            raise ValueError("is_valid=False인데 error_message가 비어있음")

    def __repr__(self) -> str:
        status = "OK" if self.is_valid else f"INVALID({self.error_message})"
        return (
            f"CrossoverGeometry({status}, "
            f"L={self.connecting_length:.2f}m, "
            f"T1_sta={self.turnout1_station:.2f}, "
            f"T2_sta={self.turnout2_station:.2f})"
        )