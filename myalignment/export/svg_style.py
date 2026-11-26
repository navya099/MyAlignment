from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class SvgStyle:
    """SVG 페이지, 배경, 선가중치와 글꼴 설정."""

    background_color: str = "#FFFFFF"
    stroke_width_scale: float = 1.0
    font_family: str = "Arial, sans-serif"
    font_size_scale: float = 1.0
    use_aci_colors: bool = True
    page_width_mm: float = 297.0
    page_height_mm: float = 210.0
    margin_mm: float = 10.0
    auto_fit_viewport: bool = True

    def __post_init__(self):
        for name in ("stroke_width_scale", "font_size_scale", "page_width_mm", "page_height_mm"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if not math.isfinite(self.margin_mm) or not 0 <= self.margin_mm < min(
            self.page_width_mm, self.page_height_mm,
        ) / 2:
            raise ValueError("margin_mm must leave a positive drawing area")
        if not self.background_color.strip() or not self.font_family.strip():
            raise ValueError("background_color and font_family must be nonempty")

    @classmethod
    def web(cls) -> SvgStyle:
        return cls(font_family="system-ui, sans-serif", font_size_scale=1.2, stroke_width_scale=1.5)

    @classmethod
    def print(cls) -> SvgStyle:
        return cls(font_family="Arial, Helvetica, sans-serif", use_aci_colors=False)

    @classmethod
    def dark(cls) -> SvgStyle:
        return cls(background_color="#1a1a2e", font_family="monospace")
