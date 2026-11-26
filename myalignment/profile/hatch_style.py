from __future__ import annotations

from dataclasses import dataclass
import math

from myalignment.profile.hatch_pattern import HatchPattern


@dataclass(frozen=True, slots=True)
class ProfileHatchStyle:
    """절토·성토 해치의 패턴, 색상, 간격과 출력 레이어."""

    name: str = "Standard"
    cut_pattern: HatchPattern = HatchPattern.DIAGONAL
    cut_color: int = 1
    cut_spacing: float = 3.0
    cut_opacity: float = 0.3
    fill_pattern: HatchPattern = HatchPattern.CROSS
    fill_color: int = 5
    fill_spacing: float = 3.0
    fill_opacity: float = 0.3
    lineweight: float = 0.2
    boundary_lineweight: float = 0.5
    cut_layer: str = "C-PROF-HATCH-CUT"
    fill_layer: str = "C-PROF-HATCH-FILL"
    boundary_layer: str = "C-PROF-HATCH-BND"
    show_cut: bool = True
    show_fill: bool = True
    show_net: bool = False
    net_color: int = 7

    def __post_init__(self):
        if not all(isinstance(value, HatchPattern) for value in (self.cut_pattern, self.fill_pattern)):
            raise ValueError("patterns must be HatchPattern values")
        for value in (self.cut_spacing, self.fill_spacing):
            if not math.isfinite(value) or value <= 0:
                raise ValueError("hatch spacing must be finite and positive")
        for value in (self.cut_opacity, self.fill_opacity):
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("opacity must be between 0 and 1")
        for value in (self.lineweight, self.boundary_lineweight):
            if not math.isfinite(value) or value < 0:
                raise ValueError("lineweights must be finite and nonnegative")
        for color in (self.cut_color, self.fill_color, self.net_color):
            if type(color) is not int or not 0 <= color <= 256:
                raise ValueError("colors must be ACI integers from 0 to 256")
        for layer in (self.cut_layer, self.fill_layer, self.boundary_layer):
            if not layer.strip() or any(ord(char) < 32 for char in layer):
                raise ValueError("layer must be nonempty single-line text")

    @classmethod
    def standard(cls) -> ProfileHatchStyle:
        return cls()

    @classmethod
    def subtle(cls) -> ProfileHatchStyle:
        return cls(cut_opacity=0.15, fill_opacity=0.15, cut_spacing=5, fill_spacing=5)

    @classmethod
    def bold(cls) -> ProfileHatchStyle:
        return cls(cut_opacity=0.5, fill_opacity=0.5, cut_spacing=2, fill_spacing=2)
