from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType

from myalignment.profile.label_style import ProfileLabelStyle
from myalignment.profile.label_type import ProfileLabelType


@dataclass(frozen=True, slots=True)
class ProfileLabelSet:
    """종단에 적용할 유형별 레이블 스타일."""

    name: str = "Standard"
    styles: Mapping[ProfileLabelType, ProfileLabelStyle] = field(default_factory=dict, hash=False)

    def __post_init__(self):
        styles = dict(self.styles)
        if any(kind is not style.label_type for kind, style in styles.items()):
            raise ValueError("레이블 유형과 스타일 유형이 일치해야 합니다")
        object.__setattr__(self, "styles", MappingProxyType(styles))

    def get_style(self, label_type: ProfileLabelType) -> ProfileLabelStyle | None:
        return self.styles.get(label_type)

    def active_types(self) -> tuple[ProfileLabelType, ...]:
        return tuple(self.styles)

    def with_style(self, label_type: ProfileLabelType, style: ProfileLabelStyle) -> ProfileLabelSet:
        return replace(self, styles={**self.styles, label_type: style})

    def without_style(self, label_type: ProfileLabelType) -> ProfileLabelSet:
        return replace(self, styles={kind: style for kind, style in self.styles.items() if kind is not label_type})

    @classmethod
    def standard(cls) -> ProfileLabelSet:
        styles = (
            ProfileLabelStyle.gradient_break_style(), ProfileLabelStyle.crest_curve_style(),
            ProfileLabelStyle.sag_curve_style(), ProfileLabelStyle.pvi_style(),
        )
        return cls(styles={style.label_type: style for style in styles})

    @classmethod
    def minimal(cls) -> ProfileLabelSet:
        return cls("Minimal", {ProfileLabelType.PVI: ProfileLabelStyle.pvi_style()})

    def __repr__(self) -> str:
        return f"ProfileLabelSet({self.name!r}, types={[kind.value for kind in self.styles]})"
