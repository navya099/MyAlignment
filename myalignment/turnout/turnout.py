# turnout/turnout.py
from dataclasses import dataclass
import math

from myalignment.turnout.type import TurnoutSide, TurnoutType


@dataclass(frozen=True, slots=True)
class Turnout:
    """턴아웃 객체 (C3D Turnout 호환, 불변)."""
    name: str = ""
    turnout_type: TurnoutType = None
    source_alignment_name: str = ""    # 소스 선형 이름
    branch_alignment_name: str = ""    # 분기 선형 이름
    station_on_source: float = 0.0     # 소스 선형 위 턴아웃 시작 측점
    side: TurnoutSide = TurnoutSide.RIGHT

    def __post_init__(self):
        if self.turnout_type is None:
            raise ValueError("turnout_type이 None입니다.")
        if not self.source_alignment_name:
            raise ValueError("source_alignment_name이 비어있습니다.")

    @property
    def branch_start_station(self) -> float:
        """분기 선형의 시작 측점 (소스 선형 기준)."""
        return self.station_on_source + self.turnout_type.lead_length