from dataclasses import dataclass
import math
from myalignment.profile.vertical_geometry_type import VerticalGeometryPointType


@dataclass(frozen=True, slots=True)
class GeometryBandStyle:
    """수평 지오메트리 밴드의 높이, 틱, 텍스트와 표시할 점 유형."""

    name: str = "Standard"
    band_height: float = 4.0
    tick_length: float = 1.5
    tick_color: int = 2
    tick_lineweight: float = 0.25
    text_height: float = 1.2
    text_color: int = 2
    text_offset_y: float = -1.5
    layer: str = "C-PROF-BAND-HGEOM"
    visible_types: tuple[str, ...] = ("TS", "SC", "CS", "ST", "BC", "EC")

    def __post_init__(self):
        for name in ("band_height", "text_height"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        for name in ("tick_length", "tick_lineweight"):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and nonnegative")
        if not math.isfinite(self.text_offset_y):
            raise ValueError("text_offset_y must be finite")
        for color in (self.tick_color, self.text_color):
            if not isinstance(color, int) or not 0 <= color <= 256:
                raise ValueError("ACI colors must be integers between 0 and 256")


@dataclass(frozen=True, slots=True)
class VerticalGeometryBandStyle:
    """수직 지오메트리 밴드의 틱, 텍스트와 점 유형별 색상."""

    name: str = "Standard"
    band_height: float = 4.0
    tick_length: float = 1.5
    pvi_color: int = 1
    vpc_vpt_color: int = 5
    high_low_color: int = 6
    grade_break_color: int = 2
    text_height: float = 1.2
    text_offset_y: float = -1.5
    layer: str = "C-PROF-BAND-VGEOM"
    visible_types: tuple[str, ...] = ("PVI", "VPC", "VPT", "HP", "LP", "GB")

    def __post_init__(self):
        for value in (self.band_height, self.text_height):
            if not math.isfinite(value) or value <= 0:
                raise ValueError("band_height and text_height must be finite and positive")
        if not math.isfinite(self.tick_length) or self.tick_length < 0:
            raise ValueError("tick_length must be finite and nonnegative")
        if not math.isfinite(self.text_offset_y):
            raise ValueError("text_offset_y must be finite")
        for color in (self.pvi_color, self.vpc_vpt_color, self.high_low_color, self.grade_break_color):
            if not isinstance(color, int) or not 0 <= color <= 256:
                raise ValueError("ACI colors must be integers between 0 and 256")

    def color_for_type(self, point_type: VerticalGeometryPointType) -> int:
        kind = VerticalGeometryPointType
        if point_type is kind.PVI:
            return self.pvi_color
        if point_type in (kind.VPC, kind.VPT):
            return self.vpc_vpt_color
        if point_type in (kind.HIGH_POINT, kind.LOW_POINT):
            return self.high_low_color
        if point_type is kind.GRADE_BREAK:
            return self.grade_break_color
        return 7
