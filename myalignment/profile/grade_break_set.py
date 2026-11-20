from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType

from myalignment.profile.grade_break_style import GradeBreakLabelStyle


@dataclass(frozen=True, slots=True)
class GradeBreakLabelSet:
    name: str = "Standard"
    styles: Mapping[str, GradeBreakLabelStyle] = field(default_factory=dict, hash=False)

    def __post_init__(self):
        object.__setattr__(self, "styles", MappingProxyType(dict(self.styles)))

    def get_style(self, name: str) -> GradeBreakLabelStyle | None:
        return self.styles.get(name)

    def with_style(self, name: str, style: GradeBreakLabelStyle) -> GradeBreakLabelSet:
        return replace(self, styles={**self.styles, name: style})

    @classmethod
    def standard(cls) -> GradeBreakLabelSet:
        return cls(styles={
            "standard": GradeBreakLabelStyle.standard(), "minimal": GradeBreakLabelStyle.minimal(),
            "with_k": GradeBreakLabelStyle.with_k_value(), "with_arrows": GradeBreakLabelStyle.with_arrows(),
        })
