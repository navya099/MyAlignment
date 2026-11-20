from __future__ import annotations

from dataclasses import dataclass, replace
import math

from myalignment.profile.label_component import LabelComponentType, ProfileLabelComponent
from myalignment.profile.label_type import ProfileLabelType


@dataclass(frozen=True, slots=True)
class LabelStyle:
    """종단 뷰의 측점·표고 레이블 스타일."""

    name: str = "Standard"
    text_height: float = 2.0
    text_color: int = 7
    fields: tuple[str, ...] = ("STA <[Station Value]>", "EL <[Profile 1 Elevation]>")
    offset_x: float = 0.0
    offset_y: float = 2.0
    show_marker: bool = True
    marker_size: float = 0.5

    def __post_init__(self):
        if not math.isfinite(self.text_height) or self.text_height <= 0:
            raise ValueError("text_height must be finite and positive")
        if not isinstance(self.text_color, int) or not 0 <= self.text_color <= 256:
            raise ValueError("text_color must be an ACI integer from 0 to 256")
        if not (math.isfinite(self.offset_x) and math.isfinite(self.offset_y)):
            raise ValueError("label offsets must be finite")
        if not math.isfinite(self.marker_size) or self.marker_size < 0:
            raise ValueError("marker_size must be finite and nonnegative")


@dataclass(frozen=True, slots=True)
class ProfileLabelStyle:
    """종단 레이블 유형별 구성요소와 배치 설정."""

    name: str = "Standard"
    label_type: ProfileLabelType = ProfileLabelType.GRADIENT_BREAK
    description: str = ""
    components: tuple[ProfileLabelComponent, ...] = ()
    placement: str = "above"
    obey_vertical_exaggeration: bool = True
    min_spacing: float = 5.0

    def __post_init__(self):
        if not self.components:
            raise ValueError("최소 1개 컴포넌트 필요")
        if self.placement not in ("above", "below", "left", "right"):
            raise ValueError("placement must be above, below, left or right")
        if not math.isfinite(self.min_spacing) or self.min_spacing < 0:
            raise ValueError("min_spacing must be finite and nonnegative")

    def text_components(self) -> tuple[ProfileLabelComponent, ...]:
        return tuple(c for c in self.components if c.component_type is LabelComponentType.TEXT)

    def marker_components(self) -> tuple[ProfileLabelComponent, ...]:
        return tuple(c for c in self.components if c.component_type in (
            LabelComponentType.LINE, LabelComponentType.TICK,
        ))

    def with_component(self, comp: ProfileLabelComponent) -> ProfileLabelStyle:
        return replace(self, components=self.components + (comp,))

    def without_component(self, index: int) -> ProfileLabelStyle:
        if not 0 <= index < len(self.components):
            raise IndexError(f"컴포넌트 인덱스 범위 초과: {index}")
        return replace(self, components=self.components[:index] + self.components[index + 1:])

    @classmethod
    def gradient_break_style(cls) -> ProfileLabelStyle:
        return cls(name="Gradient Break", label_type=ProfileLabelType.GRADIENT_BREAK, components=(
            ProfileLabelComponent(contents="STA <[Station Value]>", text_height=1.8, offset_y=2.0),
            ProfileLabelComponent(contents="EL <[Elevation Value]>", text_height=1.8, offset_y=0.5),
            ProfileLabelComponent(contents="G: <[Grade In]> → <[Grade Out]>", text_height=1.5, offset_y=-1.0),
        ))

    @classmethod
    def crest_curve_style(cls) -> ProfileLabelStyle:
        return cls(name="Crest Curve", label_type=ProfileLabelType.CREST_CURVE, components=(
            ProfileLabelComponent(contents="HIGH POINT", text_height=1.8, offset_y=3.0),
            ProfileLabelComponent(contents="STA <[High Point Station]>", text_height=1.5, offset_y=1.5),
            ProfileLabelComponent(contents="EL <[High Point Elevation]>", text_height=1.5, offset_y=0.0),
        ))

    @classmethod
    def sag_curve_style(cls) -> ProfileLabelStyle:
        return cls(name="Sag Curve", label_type=ProfileLabelType.SAG_CURVE, placement="below", components=(
            ProfileLabelComponent(contents="LOW POINT", text_height=1.8, offset_y=3.0),
            ProfileLabelComponent(contents="STA <[Low Point Station]>", text_height=1.5, offset_y=1.5),
            ProfileLabelComponent(contents="EL <[Low Point Elevation]>", text_height=1.5, offset_y=0.0),
        ))

    @classmethod
    def line_style(cls) -> ProfileLabelStyle:
        return cls(name="Line", label_type=ProfileLabelType.LINE, components=(
            ProfileLabelComponent(contents="G: <[Grade]>", text_height=1.5, offset_y=1.5),
            ProfileLabelComponent(contents="L: <[Length]>", text_height=1.5, offset_y=0.0),
        ))

    @classmethod
    def curve_style(cls) -> ProfileLabelStyle:
        return cls(name="Curve", label_type=ProfileLabelType.CURVE, components=(
            ProfileLabelComponent(contents="K: <[K Value]>", text_height=1.5, offset_y=1.5),
            ProfileLabelComponent(contents="L: <[Curve Length]>", text_height=1.5, offset_y=0.0),
        ))

    @classmethod
    def pvi_style(cls) -> ProfileLabelStyle:
        return cls(name="PVI", label_type=ProfileLabelType.PVI, placement="below", components=(
            ProfileLabelComponent(contents="PVI", text_height=1.8, offset_y=3.0),
            ProfileLabelComponent(contents="STA <[Station Value]>", text_height=1.5, offset_y=1.5),
            ProfileLabelComponent(contents="EL <[Elevation Value]>", text_height=1.5, offset_y=0.0),
        ))

    def __repr__(self) -> str:
        return f"ProfileLabelStyle({self.name!r}, {self.label_type.value}, components={len(self.components)})"
