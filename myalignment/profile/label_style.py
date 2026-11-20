from dataclasses import dataclass
import math


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
