from __future__ import annotations

from dataclasses import dataclass
import math
from string import Formatter

from myalignment.section.projection_object_type import SectionProjectionObjectType


@dataclass(frozen=True, slots=True)
class SectionProjectionStyle:
    """횡단 투영의 외곽선, 마커, 레이블 및 기본 단면 치수."""

    name: str = "Standard"
    object_type: SectionProjectionObjectType = SectionProjectionObjectType.STRUCTURE
    show_marker: bool = True
    show_label: bool = True
    show_outline: bool = True
    marker_color: int = 1
    label_color: int = 7
    outline_color: int = 6
    marker_lineweight: float = 0.5
    outline_lineweight: float = 0.3
    layer: str = "C-SECTION-PROJECTION"
    label_format: str = "{name}"
    deck_height: float = 2.0
    pier_width: float = 1.5
    pipe_diameter: float = 1.0

    def __post_init__(self):
        if not isinstance(self.object_type, SectionProjectionObjectType):
            raise ValueError("object_type must be a SectionProjectionObjectType")
        if not self.layer.strip() or any(ord(char) < 32 for char in self.layer):
            raise ValueError("layer must be nonempty single-line text")
        for color in (self.marker_color, self.label_color, self.outline_color):
            if type(color) is not int or not 0 <= color <= 256:
                raise ValueError("projection colors must be ACI integers from 0 to 256")
        for value in (self.marker_lineweight, self.outline_lineweight):
            if not math.isfinite(value) or value < 0:
                raise ValueError("lineweights must be finite and nonnegative")
        for value in (self.deck_height, self.pier_width, self.pipe_diameter):
            if not math.isfinite(value) or value <= 0:
                raise ValueError("projection dimensions must be finite and positive")
        try:
            self.format_label()
        except (KeyError, IndexError, ValueError) as error:
            raise ValueError("invalid section projection label_format") from error

    def format_label(
        self, *, name: str = "", offset: float = 0.0, elevation: float = 0.0,
        start_sta: float = 0.0, end_sta: float = 0.0, pipe_diameter: float = 0.0,
    ) -> str:
        """이름, 횡거, 표고, 측점 범위, 관경으로 레이블을 만든다."""
        fields = dict(name=name, offset=offset, elevation=elevation,
                      start_sta=start_sta, end_sta=end_sta, pipe_diameter=pipe_diameter)
        if any(key is not None and key not in fields for _, key, _, _ in Formatter().parse(self.label_format)):
            raise ValueError("unknown section projection label field")
        return self.label_format.format(**fields)

    @classmethod
    def structure_style(cls) -> SectionProjectionStyle:
        return cls(name="Structure", label_format="{name}\n({start_sta:.1f}~{end_sta:.1f})")

    @classmethod
    def pipe_style(cls) -> SectionProjectionStyle:
        return cls(name="Pipe", object_type=SectionProjectionObjectType.PIPE,
                   marker_color=4, outline_color=4, label_format="{name}\nΦ{pipe_diameter:.1f}m")

    @classmethod
    def point_style(cls) -> SectionProjectionStyle:
        return cls(name="Point", object_type=SectionProjectionObjectType.POINT,
                   marker_color=2, label_format="{name}\nEL={elevation:.2f}")

    @classmethod
    def feature_line_style(cls) -> SectionProjectionStyle:
        return cls(name="FeatureLine", object_type=SectionProjectionObjectType.FEATURE_LINE,
                   marker_color=3, outline_color=3)

    @classmethod
    def alignment_style(cls) -> SectionProjectionStyle:
        return cls(name="Alignment", object_type=SectionProjectionObjectType.ALIGNMENT, marker_color=5)
