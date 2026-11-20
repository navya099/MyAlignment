from __future__ import annotations

from dataclasses import dataclass, replace
import math

from myalignment.section.label_component import SectionLabelComponent, SectionLabelComponentType
from myalignment.section.label_type import SectionLabelType


@dataclass(frozen=True, slots=True)
class SectionLabelStyle:
    name: str = "Standard"
    label_type: SectionLabelType = SectionLabelType.OFFSET_ELEVATION
    components: tuple[SectionLabelComponent, ...] = ()
    placement: str = "above"
    min_spacing: float = 1.0
    obey_vertical_exaggeration: bool = True

    def __post_init__(self):
        if not self.components:
            raise ValueError("최소 1개 컴포넌트 필요")
        if self.placement not in ("above", "below", "left", "right"):
            raise ValueError("placement must be above, below, left or right")
        if not math.isfinite(self.min_spacing) or self.min_spacing < 0:
            raise ValueError("min_spacing must be finite and nonnegative")

    def text_components(self) -> tuple[SectionLabelComponent, ...]:
        return tuple(c for c in self.components if c.component_type is SectionLabelComponentType.TEXT)

    def with_component(self, comp: SectionLabelComponent) -> SectionLabelStyle:
        return replace(self, components=self.components + (comp,))
