from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType

from myalignment.section.label_component import SectionLabelStyleFactory
from myalignment.section.label_style import SectionLabelStyle
from myalignment.section.label_type import SectionLabelType


@dataclass(frozen=True, slots=True)
class SectionLabelSet:
    """횡단 뷰에 적용할 유형별 레이블 스타일."""

    name: str = "Standard"
    styles: Mapping[SectionLabelType, SectionLabelStyle] = field(default_factory=dict, hash=False)

    def __post_init__(self):
        styles = dict(self.styles)
        if any(kind is not style.label_type for kind, style in styles.items()):
            raise ValueError("레이블 유형과 스타일 유형이 일치해야 합니다")
        object.__setattr__(self, "styles", MappingProxyType(styles))

    def get_style(self, label_type: SectionLabelType) -> SectionLabelStyle | None:
        return self.styles.get(label_type)

    def with_style(self, label_type: SectionLabelType, style: SectionLabelStyle) -> SectionLabelSet:
        return replace(self, styles={**self.styles, label_type: style})

    def without_style(self, label_type: SectionLabelType) -> SectionLabelSet:
        return replace(self, styles={kind: style for kind, style in self.styles.items() if kind is not label_type})

    @classmethod
    def standard(cls) -> SectionLabelSet:
        points, slope = SectionLabelStyleFactory.offset_elevation_style(), SectionLabelStyleFactory.slope_style()
        return cls(styles={points.label_type: points, slope.label_type: slope})

    @classmethod
    def minimal(cls) -> SectionLabelSet:
        points = SectionLabelStyleFactory.offset_elevation_style()
        return cls("Minimal", {points.label_type: points})

    @classmethod
    def full(cls) -> SectionLabelSet:
        styles = (
            SectionLabelStyleFactory.full_style(),
            SectionLabelStyleFactory.slope_style(),
            SectionLabelStyleFactory.distance_style(),
        )
        return cls("Full", {style.label_type: style for style in styles})
