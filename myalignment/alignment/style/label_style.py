from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class LabelComponentType(Enum):
    TEXT = "Text"
    LINE = "Line"
    TICK = "Tick"
    BLOCK = "Block"


@dataclass(frozen=True, slots=True)
class LabelComponent:
    """레이블의 텍스트, 선, 눈금 또는 블록."""

    component_type: LabelComponentType
    contents: str = ""
    height: float = 0.0
    visible: bool = True


@dataclass(frozen=True, slots=True)
class LabelStyle:
    """레이블 구성요소의 표시 순서를 정의한다."""

    name: str = ""
    components: tuple[LabelComponent, ...] = ()

    def with_component(self, comp: LabelComponent) -> LabelStyle:
        return replace(self, components=self.components + (comp,))
