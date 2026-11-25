from dataclasses import dataclass
import math

from cadgeom import Point2d


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


def section_projection(data, style, min_elev=None, max_elev=None, *, projections=(), extra_points=()):
    """횡단 도형과 레이블이 공유하는 등척도 기반 좌표 변환."""
    lo, hi = min(0.0, data.min_offset), max(0.0, data.max_offset)
    low_z, high_z = data.min_elevation, data.max_elevation
    has_section = bool(data.points or data.surface_points)
    for item in projections:
        if not (item.style.show_outline or item.style.show_marker or item.style.show_label):
            continue
        lo, hi = min(lo, item.left_offset), max(hi, item.right_offset)
        base = item.bottom_elevation
        if item.style.show_marker and item.pier_bottom_elevation is not None:
            base = item.pier_bottom_elevation
        low_z = min(low_z, base) if has_section else base
        high_z = max(high_z, item.top_elevation) if has_section else item.top_elevation
        has_section = True
    for offset, elevation in extra_points:
        lo, hi = min(lo, offset), max(hi, offset)
        low_z = min(low_z, elevation) if has_section else elevation
        high_z = max(high_z, elevation) if has_section else elevation
        has_section = True
    bottom = low_z - 1 if min_elev is None else min_elev
    top = high_z + 1 if max_elev is None else max_elev
    if not (math.isfinite(bottom) and math.isfinite(top) and bottom < top):
        raise ValueError("Elevation bounds must be finite and increasing")
    exaggeration = style.vertical_exaggeration
    horizontal_span = max(hi - lo, style.grid_x_interval)
    scale = min(style.plot_width / horizontal_span, style.plot_height / ((top - bottom) * exaggeration))
    middle_x, middle_z = (lo + hi) / 2, (bottom + top) / 2
    half_x = style.plot_width / (2 * scale)
    half_z = style.plot_height / (2 * scale * exaggeration)
    lo, hi = middle_x - half_x, middle_x + half_x
    bottom, top = middle_z - half_z, middle_z + half_z

    def plot(offset, elevation):
        return Point2d(style.offset_to_x(offset, lo, hi), style.elevation_to_y(
            elevation, bottom, bottom + 2 * half_z * exaggeration,
        ))

    return lo, hi, bottom, top, plot
