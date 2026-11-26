from __future__ import annotations

from dataclasses import dataclass, field
import math

from myalignment.alignment.label_component import AlignmentLabelComponent
from myalignment.alignment.profile_geometry_label_type import ProfileGeometryPointLabelType as Kind


_LAYER = "C-ALIGN-PROF-GEOM"


def _text(contents, height, offset_y, color=7):
    return AlignmentLabelComponent(
        contents=contents, text_height=height, text_color=color, offset_y=offset_y, layer=_LAYER,
    )


def _standard_components():
    return (
        _text("<[Point Type]>", 1.8, 5.0, 5),
        _text("STA <[Station Value]>", 1.5, 3.2),
        _text("EL <[Elevation Value]>", 1.5, 1.5),
    )


@dataclass(frozen=True, slots=True)
class ProfileGeometryLabelStyle:
    """종단 기하점의 텍스트, 표시 유형, 표식기와 지시선."""

    name: str = "Profile Geometry Point"
    components: tuple[AlignmentLabelComponent, ...] = field(default_factory=_standard_components)
    labeled_points: tuple[Kind, ...] = (Kind.PVI, Kind.VPC, Kind.VPT)
    show_marker: bool = True
    marker_size: float = 1.5
    marker_color: int = 5
    show_leader: bool = False
    marker_layer: str = _LAYER

    def __post_init__(self):
        components, points = tuple(self.components), tuple(self.labeled_points)
        if not components or any(not isinstance(item, AlignmentLabelComponent) for item in components):
            raise ValueError("at least one AlignmentLabelComponent is required")
        if any(not isinstance(point, Kind) for point in points):
            raise ValueError("labeled_points must contain ProfileGeometryPointLabelType values")
        object.__setattr__(self, "components", components)
        object.__setattr__(self, "labeled_points", points)
        if not math.isfinite(self.marker_size) or self.marker_size <= 0:
            raise ValueError("marker_size must be finite and positive")
        if type(self.marker_color) is not int or not 0 <= self.marker_color <= 256:
            raise ValueError("marker_color must be an ACI integer from 0 to 256")
        if not self.marker_layer.strip() or any(ord(char) < 32 for char in self.marker_layer):
            raise ValueError("marker_layer must be nonempty single-line text")

    @classmethod
    def standard(cls) -> ProfileGeometryLabelStyle:
        return cls(name="Standard")

    @classmethod
    def pvi_only(cls) -> ProfileGeometryLabelStyle:
        return cls(name="PVI Only", components=(_text("PVI <[Station Value]>", 1.5, 2.0),), labeled_points=(Kind.PVI,))

    @classmethod
    def with_grade_info(cls) -> ProfileGeometryLabelStyle:
        return cls(name="With Grade", labeled_points=(Kind.PVI, Kind.GRADE_BREAK), components=(
            _text("<[Point Type]>", 1.8, 6.0),
            _text("STA <[Station Value]>  EL <[Elevation Value]>", 1.5, 4.3),
            _text("G1: <[Grade In]>  G2: <[Grade Out]>", 1.3, 2.8),
        ))
