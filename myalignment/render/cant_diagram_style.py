from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class CantDiagramStyle:
    """독립 캔트 다이어그램의 치수와 표시 스타일. Y 격자 간격은 mm 기준이다."""

    name: str = "Standard"
    width: float = 1000.0
    height: float = 200.0
    margin_left: float = 80.0
    margin_right: float = 40.0
    margin_top: float = 40.0
    margin_bottom: float = 60.0
    grid_x_interval: float = 100.0
    grid_y_interval: float = 20.0
    grid_color: int = 8
    cant_line_color: int = 1
    cant_lineweight: float = 0.5
    transition_color: int = 3
    full_cant_color: int = 1
    normal_color: int = 8
    text_height: float = 3.0
    text_color: int = 7
    axis_color: int = 7
    axis_lineweight: float = 0.5
    layer: str = "C-CANT-DIAGRAM"
    unit: str = "mm"

    def __post_init__(self):
        for name in ("width", "height", "grid_x_interval", "grid_y_interval", "text_height"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        for name in ("margin_left", "margin_right", "margin_top", "margin_bottom",
                     "cant_lineweight", "axis_lineweight"):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and nonnegative")
        if self.margin_left + self.margin_right >= self.width or self.margin_top + self.margin_bottom >= self.height:
            raise ValueError("Margins must leave a positive plot area")
        if self.unit not in ("mm", "%"):
            raise ValueError("unit must be mm or %")
        for color in (self.grid_color, self.cant_line_color, self.transition_color,
                      self.full_cant_color, self.normal_color, self.text_color, self.axis_color):
            if not isinstance(color, int) or not 0 <= color <= 256:
                raise ValueError("ACI colors must be integers between 0 and 256")

    def cant_to_y(self, cant_mm: float, max_cant: float) -> float:
        if max_cant <= 0:
            return self.margin_bottom
        span = self.height - self.margin_top - self.margin_bottom
        return self.margin_bottom + cant_mm / max_cant * span

    def station_to_x(self, station: float, min_sta: float, max_sta: float) -> float:
        if max_sta <= min_sta:
            return self.margin_left
        span = self.width - self.margin_left - self.margin_right
        return self.margin_left + (station - min_sta) / (max_sta - min_sta) * span
