from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class EarthworkBandStyle:
    """절토·성토와 계획고·지반고를 표시하는 종단 밴드 스타일."""

    name: str = "Earthwork"
    row_height: float = 4.0
    band_gap: float = 1.0
    show_station: bool = True
    show_fg: bool = True
    show_eg: bool = True
    show_cut: bool = True
    show_fill: bool = True
    show_diff: bool = False
    sample_interval: float = 50.0
    station_color: int = 7
    fg_color: int = 1
    eg_color: int = 3
    cut_color: int = 6
    fill_color: int = 5
    diff_color: int = 2
    text_height: float = 2.0
    label_height: float = 2.5
    layer: str = "C-PROF-BAND-EARTHWORK"

    def __post_init__(self):
        for name in ("row_height", "sample_interval", "text_height", "label_height"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if not math.isfinite(self.band_gap) or self.band_gap < 0:
            raise ValueError("band_gap must be finite and nonnegative")
        for color in (self.station_color, self.fg_color, self.eg_color,
                      self.cut_color, self.fill_color, self.diff_color):
            if type(color) is not int or not 0 <= color <= 256:
                raise ValueError("ACI colors must be integers between 0 and 256")

    @property
    def total_height(self) -> float:
        """표시할 행 높이의 합."""
        return self.row_height * sum((
            self.show_station, self.show_fg, self.show_eg, self.show_cut, self.show_fill, self.show_diff,
        ))

    @classmethod
    def standard(cls) -> "EarthworkBandStyle":
        """측점, 계획고, 지반고, 절토·성토를 표시한다."""
        return cls()

    @classmethod
    def minimal(cls) -> "EarthworkBandStyle":
        """측점과 절토·성토를 표시한다."""
        return cls(show_fg=False, show_eg=False)

    @classmethod
    def detailed(cls) -> "EarthworkBandStyle":
        """표준 행과 부호가 있는 표고차를 표시한다."""
        return cls(show_diff=True)
