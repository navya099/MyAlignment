from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class SectionViewStyle:
    """횡단 뷰의 크기, 축, 격자와 레이블 표시 설정."""

    name: str = "Standard"
    width: float = 400.0
    height: float = 200.0
    margin_left: float = 80.0
    margin_right: float = 40.0
    margin_top: float = 40.0
    margin_bottom: float = 60.0
    grid_x_interval: float = 2.0
    grid_y_interval: float = 1.0
    grid_color: int = 8
    section_line_color: int = 7
    section_lineweight: float = 0.5
    surface_color: int = 3
    surface_lineweight: float = 0.3
    vertical_exaggeration: float = 1.0
    text_height: float = 2.0
    text_color: int = 7
    axis_color: int = 7
    axis_lineweight: float = 0.5
    layer: str = "C-SECTION-VIEW"
    show_offset_labels: bool = True
    show_elevation_labels: bool = True
    show_slope_labels: bool = False

    def __post_init__(self):
        for name in ("width", "height", "grid_x_interval", "grid_y_interval",
                     "vertical_exaggeration", "text_height"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        for name in ("margin_left", "margin_right", "margin_top", "margin_bottom",
                     "section_lineweight", "surface_lineweight", "axis_lineweight"):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and nonnegative")
        if self.plot_width <= 0 or self.plot_height <= 0:
            raise ValueError("Margins must leave a positive plot area")
        for color in (self.grid_color, self.section_line_color, self.surface_color, self.text_color, self.axis_color):
            if not isinstance(color, int) or not 0 <= color <= 256:
                raise ValueError("ACI colors must be integers between 0 and 256")

    @property
    def plot_width(self) -> float:
        return self.width - self.margin_left - self.margin_right

    @property
    def plot_height(self) -> float:
        return self.height - self.margin_top - self.margin_bottom

    def offset_to_x(self, offset: float, min_offset: float, max_offset: float) -> float:
        if max_offset <= min_offset:
            return self.margin_left
        return self.margin_left + (offset - min_offset) * self.plot_width / (max_offset - min_offset)

    def elevation_to_y(self, elevation: float, min_elev: float, max_elev: float) -> float:
        if max_elev <= min_elev:
            return self.margin_bottom
        return self.margin_bottom + (
            (elevation - min_elev) * self.plot_height * self.vertical_exaggeration / (max_elev - min_elev)
        )
