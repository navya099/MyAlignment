from __future__ import annotations

from dataclasses import dataclass, field
import math

from myalignment.alignment.label_component import AlignmentLabelComponent


def _standard_components() -> tuple[AlignmentLabelComponent, ...]:
    layer = "C-ALIGN-SO-LABEL"
    return (
        AlignmentLabelComponent(contents="STA <[Station Value]>", text_height=1.8, offset_y=3.0, layer=layer),
        AlignmentLabelComponent(contents="OFF: <[Offset Value]>", text_height=1.8, offset_y=1.0, layer=layer),
    )


@dataclass(frozen=True, slots=True)
class StationOffsetLabelStyle:
    """측점·횡거 레이블의 컴포넌트와 점 표식기."""

    name: str = "Station Offset"
    components: tuple[AlignmentLabelComponent, ...] = field(default_factory=_standard_components)
    show_station: bool = True
    show_offset: bool = True
    show_marker: bool = True
    marker_size: float = 1.0
    marker_color: int = 1
    is_fixed_point: bool = False
    marker_layer: str = "C-ALIGN-SO-LABEL"

    def __post_init__(self):
        components = tuple(self.components)
        if not components or any(not isinstance(component, AlignmentLabelComponent) for component in components):
            raise ValueError("at least one AlignmentLabelComponent is required")
        object.__setattr__(self, "components", components)
        if not math.isfinite(self.marker_size) or self.marker_size <= 0:
            raise ValueError("marker_size must be finite and positive")
        if type(self.marker_color) is not int or not 0 <= self.marker_color <= 256:
            raise ValueError("marker_color must be an ACI integer from 0 to 256")
        if not self.marker_layer.strip() or any(ord(char) < 32 for char in self.marker_layer):
            raise ValueError("marker_layer must be nonempty single-line text")

    @classmethod
    def standard(cls) -> StationOffsetLabelStyle:
        return cls(name="Standard")

    @classmethod
    def offset_only(cls) -> StationOffsetLabelStyle:
        return cls(name="Offset Only", components=_standard_components()[1:], show_station=False)
