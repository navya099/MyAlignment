from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import TYPE_CHECKING

from myalignment.section.label_type import SectionLabelType

if TYPE_CHECKING:
    from myalignment.section.label_style import SectionLabelStyle


class SectionLabelComponentType(Enum):
    TEXT = "Text"
    LINE = "Line"
    TICK = "Tick"


@dataclass(frozen=True, slots=True)
class SectionLabelComponent:
    """횡단 레이블의 텍스트, 선 또는 틱."""

    component_type: SectionLabelComponentType = SectionLabelComponentType.TEXT
    contents: str = ""
    text_height: float = 1.5
    text_color: int = 7
    rotation: float = 0.0
    offset_x: float = 0.0
    offset_y: float = 2.0
    visible: bool = True
    layer: str = "C-SECTION-LABEL"
    size: float = 0.8

    def __post_init__(self):
        if not math.isfinite(self.text_height) or self.text_height <= 0:
            raise ValueError("text_height must be finite and positive")
        if not math.isfinite(self.size) or self.size < 0:
            raise ValueError("size must be finite and nonnegative")
        if not all(math.isfinite(v) for v in (self.rotation, self.offset_x, self.offset_y)):
            raise ValueError("rotation and offsets must be finite")
        if not isinstance(self.text_color, int) or not 0 <= self.text_color <= 256:
            raise ValueError("text_color must be an ACI integer from 0 to 256")


class SectionLabelStyleFactory:
    @staticmethod
    def offset_elevation_style() -> SectionLabelStyle:
        from myalignment.section.label_style import SectionLabelStyle

        return SectionLabelStyle("Offset Elevation", SectionLabelType.OFFSET_ELEVATION, (
            SectionLabelComponent(contents="OFF: <[Offset]>", offset_y=2.5),
            SectionLabelComponent(contents="EL: <[Elevation]>", offset_y=1.0),
        ))

    @staticmethod
    def slope_style() -> SectionLabelStyle:
        from myalignment.section.label_style import SectionLabelStyle

        return SectionLabelStyle("Slope", SectionLabelType.SLOPE, (
            SectionLabelComponent(contents="<[Slope]>", text_height=1.2, offset_y=1.0),
        ))

    @staticmethod
    def distance_style() -> SectionLabelStyle:
        from myalignment.section.label_style import SectionLabelStyle

        return SectionLabelStyle("Distance", SectionLabelType.DISTANCE, (
            SectionLabelComponent(contents="L: <[Distance]>", text_height=1.2, offset_y=2.5),
        ))

    @staticmethod
    def full_style() -> SectionLabelStyle:
        from myalignment.section.label_style import SectionLabelStyle

        return SectionLabelStyle("Full", SectionLabelType.OFFSET_ELEVATION, (
            SectionLabelComponent(contents="OFF: <[Offset]>", text_height=1.3, offset_y=3.5),
            SectionLabelComponent(contents="EL: <[Elevation]>", text_height=1.3, offset_y=2.0),
            SectionLabelComponent(contents="S: <[Slope]>", text_height=1.2, offset_y=0.5),
        ))

    @staticmethod
    def grade_break_style() -> SectionLabelStyle:
        from myalignment.section.label_style import SectionLabelStyle

        return SectionLabelStyle("Grade Break", SectionLabelType.GRADE_BREAK, (
            SectionLabelComponent(contents="GB <[Slope In]> → <[Slope Out]>"),
        ))

    @staticmethod
    def section_segment_style() -> SectionLabelStyle:
        from myalignment.section.label_style import SectionLabelStyle

        return SectionLabelStyle("Section Segment", SectionLabelType.SECTION_SEGMENT, (
            SectionLabelComponent(contents="STA <[Station]> | Width <[Width]> | L: <[Distance]>"),
        ))
