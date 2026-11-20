from dataclasses import dataclass
import math


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
