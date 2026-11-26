from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math
import operator

from myalignment.assembly.conditional.condition_type import ConditionType


_KEYS = {
    ConditionType.CUT_FILL: "elevation_diff",
    ConditionType.SURFACE_ELEVATION: "surface_elevation",
    ConditionType.OFFSET_RANGE: "offset",
    ConditionType.GRADE_THRESHOLD: "grade",
    ConditionType.TARGET_REACHED: "target_reached",
    ConditionType.CUSTOM: "surface_elevation",
}
_COMPARISONS = {
    ">": operator.gt, "<": operator.lt, ">=": operator.ge, "<=": operator.le,
    "==": lambda a, b: math.isclose(a, b, rel_tol=0, abs_tol=1e-6),
    "!=": lambda a, b: not math.isclose(a, b, rel_tol=0, abs_tol=1e-6),
}


@dataclass(frozen=True, slots=True)
class Condition:
    """컨텍스트의 값 하나를 임계값과 비교한다."""

    condition_type: ConditionType
    threshold: float = 0.0
    comparison: str = ">"
    context_key: str | None = None

    def __post_init__(self):
        if not isinstance(self.condition_type, ConditionType):
            raise ValueError("condition_type must be a ConditionType")
        if self.comparison not in _COMPARISONS:
            raise ValueError(f"Unknown comparison: {self.comparison}")
        if not math.isfinite(self.threshold):
            raise ValueError("threshold must be finite")
        if self.context_key is None:
            object.__setattr__(self, "context_key", _KEYS[self.condition_type])
        elif not self.context_key.strip():
            raise ValueError("context_key must be nonempty")

    def evaluate(self, context: Mapping[str, float | bool | None]) -> bool:
        """값이 존재하고 유한할 때 비교 결과를 반환한다."""
        value = context.get(self.context_key)
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            return False
        return _COMPARISONS[self.comparison](value, self.threshold)

    @classmethod
    def cut_fill_condition(cls, cut_threshold: float = 0.0) -> Condition:
        """원지반이 설계 접점보다 높으면 절토로 판정한다."""
        return cls(ConditionType.CUT_FILL, cut_threshold)
