from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from myalignment.assembly.conditional.condition import Condition
from myalignment.assembly.subassembly import Subassembly


@dataclass(frozen=True, slots=True)
class ConditionalBranch:
    """조건이 충족되면 배치하는 서브어셈블리. 조건이 없으면 else다."""

    subassembly: Subassembly
    condition: Condition | None = None
    name: str = ""

    def __post_init__(self):
        if not isinstance(self.subassembly, Subassembly):
            raise TypeError("subassembly must be a Subassembly")
        if self.condition is not None and not isinstance(self.condition, Condition):
            raise TypeError("condition must be a Condition")

    @property
    def is_else(self) -> bool:
        return self.condition is None

    def matches(self, context: Mapping[str, float | bool | None]) -> bool:
        """컨텍스트가 이 분기를 선택하는지 평가한다."""
        return self.condition is None or self.condition.evaluate(context)
