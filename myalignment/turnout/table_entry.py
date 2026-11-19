# turnout/table_entry.py
from __future__ import annotations
from dataclasses import dataclass, field
import math
from enum import Enum

from myalignment.turnout.type import TurnoutType
from myalignment.turnout.type import TurnoutSide


class SwitchType(Enum):
    """스위치 종류."""
    SINGLE = "단동"
    DOUBLE = "복동"
    SPRING = "탄성"
    SLIP = "슬립"


@dataclass(frozen=True, slots=True)
class TurnoutTableEntry:
    """
    턴아웃 테이블 항목 (불변).

    C3D Turnout Table의 한 행.
    - TurnoutType을 확장한 메타데이터 포함.
    """
    # 기본 식별
    name: str = ""  # "1/12"
    description: str = ""

    # 기하 파라미터 (TurnoutType 핵심)
    frog_number: float = 0.0  # 분기기 번수
    lead_length: float = 0.0  # 리드 길이 (m)
    radius: float = 0.0  # 분기 곡선 반경 (m)
    switch_type: SwitchType = SwitchType.SINGLE

    # 성능
    max_speed_main: float = 0.0  # 본선 (km/h)
    max_speed_branch: float = 0.0  # 분기 (km/h)

    # 호환성
    gauge: float = 1.435  # 표준궤 (m)
    default_side: TurnoutSide = TurnoutSide.RIGHT

    def __post_init__(self):
        if not self.name:
            raise ValueError("name이 비어있습니다.")
        if self.lead_length <= 0:
            raise ValueError(f"lead_length > 0 필요: {self.lead_length}")
        if self.radius <= 0:
            raise ValueError(f"radius > 0 필요: {self.radius}")

    # ================================================================
    # TurnoutType 변환
    # ================================================================
    def to_turnout_type(self) -> TurnoutType:
        """TurnoutTableEntry → TurnoutType."""
        return TurnoutType(
            name=self.name,
            frog_number=self.frog_number,
            lead_length=self.lead_length,
            radius=self.radius,
            max_speed_main=self.max_speed_main,
            max_speed_branch=self.max_speed_branch,
        )

    # ================================================================
    # 검증
    # ================================================================
    def is_compatible_with_gauge(self, gauge: float, tol: float = 1e-3) -> bool:
        """궤간 호환성."""
        return abs(self.gauge - gauge) < tol

    # ================================================================
    # 불변 변환
    # ================================================================
    def with_speed(self, main: float, branch: float) -> "TurnoutTableEntry":
        from dataclasses import replace
        return replace(self, max_speed_main=main, max_speed_branch=branch)

    def with_description(self, description: str) -> "TurnoutTableEntry":
        from dataclasses import replace
        return replace(self, description=description)

    def __repr__(self) -> str:
        return (
            f"TurnoutTableEntry('{self.name}', "
            f"1/{int(self.frog_number) if self.frog_number else 0}, "
            f"L={self.lead_length:.1f}m, R={self.radius:.1f}m)"
        )