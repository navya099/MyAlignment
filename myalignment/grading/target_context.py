# grading/target_context.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol


class Surface(Protocol):
    """지표면 인터페이스 (Protocol)."""

    def elevation_at(self, x: float, y: float) -> float: ...


@dataclass(frozen=True, slots=True)
class TargetContext:
    """
    Grading Target 컨텍스트.

    - surface: 참조 지표면
    - 기타 참조 객체
    """
    surface: Surface | None = None
    metadata: dict = field(default_factory=dict)