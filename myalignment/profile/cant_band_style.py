from dataclasses import dataclass
import math

from myalignment.superelevation.critical_station import TransitionRegionType


@dataclass(frozen=True, slots=True)
class CantBandStyle:
    """철도 캔트 밴드의 색상, 표시 항목과 단위."""

    name: str = "Cant Standard"
    band_height: float = 5.0
    normal_color: int = 8
    transition_color: int = 3
    full_cant_color: int = 1
    text_color: int = 7
    text_height: float = 1.5
    show_cant_value: bool = True
    show_region_label: bool = True
    unit: str = "mm"
    tick_length: float = 1.0
    layer: str = "C-PROF-BAND-CANT"
    show_pivot: bool = True

    def __post_init__(self):
        if self.unit not in ("mm", "m"):
            raise ValueError("unit must be mm or m")
        if any(not math.isfinite(value) or value <= 0 for value in (self.band_height, self.text_height)):
            raise ValueError("band_height and text_height must be finite and positive")
        if not math.isfinite(self.tick_length) or self.tick_length < 0:
            raise ValueError("tick_length must be finite and nonnegative")
        for color in (self.normal_color, self.transition_color, self.full_cant_color, self.text_color):
            if not isinstance(color, int) or not 0 <= color <= 256:
                raise ValueError("ACI colors must be integers between 0 and 256")

    def color_for_region(self, region_type: TransitionRegionType) -> int:
        if region_type is TransitionRegionType.NORMAL:
            return self.normal_color
        if region_type is TransitionRegionType.FULL_SUPERELEVATION:
            return self.full_cant_color
        return self.transition_color
