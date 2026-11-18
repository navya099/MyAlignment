# turnout/type.py
from dataclasses import dataclass, field
from enum import Enum

class TurnoutSide(Enum):
    LEFT = "left"
    RIGHT = "right"

@dataclass(frozen=True, slots=True)
class TurnoutType:
    """턴아웃 유형 (라이브러리 항목, 불변)."""
    name: str = ""
    # 기하 파라미터 (C3D 카탈로그 기반)
    frog_number: float = 0.0          # 분기기 번수 (예: 1/12)
    lead_length: float = 0.0          # 리드 길이 (m)
    radius: float = 0.0               # 분기 곡선 반경 (m)
    max_speed_main: float = 0.0       # 본선 통과 속도
    max_speed_branch: float = 0.0     # 분기 통과 속도