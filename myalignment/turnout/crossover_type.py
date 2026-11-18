# turnout/crossover_type.py
from enum import Enum


class CrossoverType(Enum):
    """C3D Crossover 유형."""
    SINGLE = "single"          # 단일 (한 방향)
    DOUBLE = "double"          # 복식 (양방향, X자)
    SCISSORS = "scissors"      # 시저스 (양방향, 교차부 포함)