from __future__ import annotations

from dataclasses import dataclass, field
import math
from string import Formatter

from myalignment.profile.projection_object_type import ProjectionObjectType


@dataclass(frozen=True, slots=True)
class ProjectionStyle:
    """투영 객체의 범위, 마커와 레이블 표시 설정."""

    name: str = "Standard"
    object_type: ProjectionObjectType = ProjectionObjectType.STRUCTURE
    show_range: bool = True
    show_elevation: bool = True
    show_marker: bool = True
    show_label: bool = True
    range_color: int = 6
    marker_color: int = 1
    label_color: int = 7
    range_lineweight: float = 0.5
    marker_lineweight: float = 0.3
    layer: str = "C-PROF-PROJECTION"
    label_format: str = "{name}"
    text_height: float = 2.0

    def __post_init__(self):
        if not isinstance(self.object_type, ProjectionObjectType):
            raise ValueError("object_type must be a ProjectionObjectType")
        if not self.layer.strip() or any(ord(char) < 32 for char in self.layer):
            raise ValueError("layer must be nonempty single-line text")
        for color in (self.range_color, self.marker_color, self.label_color):
            if type(color) is not int or not 0 <= color <= 256:
                raise ValueError("projection colors must be ACI integers from 0 to 256")
        for width in (self.range_lineweight, self.marker_lineweight):
            if not math.isfinite(width) or width < 0:
                raise ValueError("lineweights must be finite and nonnegative")
        if not math.isfinite(self.text_height) or self.text_height <= 0:
            raise ValueError("text_height must be finite and positive")
        fields = {"name": "", "start_sta": 0.0, "end_sta": 0.0, "elevation": 0.0}
        try:
            if any(key is not None and key not in fields for _, key, _, _ in Formatter().parse(self.label_format)):
                raise ValueError
            self.label_format.format(**fields)
        except (KeyError, IndexError, ValueError) as error:
            raise ValueError("invalid projection label_format") from error

    @classmethod
    def structure_style(cls) -> ProjectionStyle:
        return cls(name="Structure", label_format="{name}\nSTA {start_sta:.1f} ~ {end_sta:.1f}")

    @classmethod
    def feature_line_style(cls) -> ProjectionStyle:
        return cls(name="FeatureLine", object_type=ProjectionObjectType.FEATURE_LINE, range_color=5, marker_color=3)

    @classmethod
    def alignment_style(cls) -> ProjectionStyle:
        return cls(name="Alignment", object_type=ProjectionObjectType.ALIGNMENT, range_color=2, marker_color=2)

    @classmethod
    def point_style(cls) -> ProjectionStyle:
        return cls(name="Point", object_type=ProjectionObjectType.POINT)


@dataclass(frozen=True, slots=True)
class ProjectionReference:
    """투영할 원본과 스타일, 선택적인 표시 이름."""

    object: object
    style: ProjectionStyle = field(default_factory=ProjectionStyle.structure_style)
    name: str = ""

    def __post_init__(self):
        if self.object is None:
            raise ValueError("projection reference object is required")
        if not self.name:
            object.__setattr__(self, "name", getattr(self.object, "name", "") or "Projection")
