# turnout/crossover.py
from dataclasses import dataclass

from myalignment.turnout.turnout import Turnout


@dataclass(frozen=True, slots=True)
class Crossover:
    """크로스오버 (평행 선형 연결, 불변)."""
    name: str = ""
    turnout1: Turnout = None      # 첫 번째 턴아웃
    turnout2: Turnout = None      # 두 번째 턴아웃
    connecting_alignment_name: str = ""

    def __post_init__(self):
        if self.turnout1 is None or self.turnout2 is None:
            raise ValueError("두 턴아웃이 필요합니다.")