from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType

from myalignment.alignment.equation_label_style import StationEquationLabelStyle
from myalignment.alignment.label_style import AlignmentLabelStyle
from myalignment.alignment.label_type import AlignmentLabelType


@dataclass(frozen=True, slots=True)
class AlignmentLabelSet:
    """평면선형에 적용할 유형별 스타일."""

    name: str = "Standard"
    styles: Mapping[AlignmentLabelType, AlignmentLabelStyle] = field(default_factory=dict, hash=False)

    equation_style: StationEquationLabelStyle | None = None

    def __post_init__(self):
        styles = dict(self.styles)
        if any(kind is not style.label_type for kind, style in styles.items()):
            raise ValueError("레이블 유형과 스타일 유형이 일치해야 합니다")
        object.__setattr__(self, "styles", MappingProxyType(styles))

    def get_style(self, label_type: AlignmentLabelType) -> AlignmentLabelStyle | None:
        return self.styles.get(label_type)

    def with_style(self, label_type: AlignmentLabelType, style: AlignmentLabelStyle) -> AlignmentLabelSet:
        return replace(self, styles={**self.styles, label_type: style})

    def with_equation_style(self, style: StationEquationLabelStyle | None) -> AlignmentLabelSet:
        return replace(self, equation_style=style)

    @classmethod
    def standard(cls) -> AlignmentLabelSet:
        styles = (
            AlignmentLabelStyle.major_station_style(),
            AlignmentLabelStyle.minor_station_style(),
            AlignmentLabelStyle.geometry_point_style(),
            AlignmentLabelStyle.line_style(),
        )
        return cls(
            styles={style.label_type: style for style in styles},
            equation_style=StationEquationLabelStyle.standard(),
        )

    @classmethod
    def with_minor_text(cls) -> AlignmentLabelSet:
        styles = (
            AlignmentLabelStyle.major_station_style(),
            AlignmentLabelStyle.minor_station_with_text_style(),
            AlignmentLabelStyle.geometry_point_style(),
        )
        return cls("With Minor Text", {style.label_type: style for style in styles})

    @classmethod
    def with_surface_reference(cls) -> AlignmentLabelSet:
        styles = (
            AlignmentLabelStyle.major_station_style(),
            AlignmentLabelStyle.geometry_point_with_surface_style(),
        )
        return cls("With Surface", {style.label_type: style for style in styles})
