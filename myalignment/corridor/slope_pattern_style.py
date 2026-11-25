from __future__ import annotations

from dataclasses import dataclass
import math

from myalignment.corridor.slope_pattern_type import SlopePatternType


@dataclass(frozen=True, slots=True)
class SlopePatternStyle:
    """사면 패턴의 간격, 크기, 레이어와 레이블 설정."""

    name: str = "Standard"
    pattern_type: SlopePatternType = SlopePatternType.HATCH
    spacing_horizontal: float = 2.0
    spacing_vertical: float = 1.0
    pattern_size: float = 1.0
    step_height: float = 1.0
    step_width: float = 2.0
    include_berm: bool = True
    stake_spacing: float = 5.0
    stake_length: float = 1.5
    berm_width: float = 2.0
    berm_interval: float = 5.0
    color: int = 3
    lineweight: float = 0.3
    layer: str = "C-CORRIDOR-SLOPE-PATTERN"
    show_label: bool = False
    show_slope_value: bool = True

    def __post_init__(self):
        if not isinstance(self.pattern_type, SlopePatternType):
            raise ValueError("pattern_type must be a SlopePatternType")
        for field in ("spacing_horizontal", "spacing_vertical", "pattern_size", "step_height", "step_width",
                      "stake_spacing", "stake_length", "berm_width", "berm_interval"):
            value = getattr(self, field)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{field} must be finite and positive")
        if not math.isfinite(self.lineweight) or self.lineweight < 0:
            raise ValueError("lineweight must be finite and nonnegative")
        if type(self.color) is not int or not 0 <= self.color <= 256:
            raise ValueError("color must be an ACI integer between 0 and 256")
        for field in ("name", "layer"):
            value = getattr(self, field)
            if not value.strip() or any(ord(char) < 32 for char in value):
                raise ValueError(f"{field} must be nonempty single-line text")

    @classmethod
    def hatch_style(cls) -> SlopePatternStyle:
        return cls(name="Hatch")

    @classmethod
    def grid_style(cls) -> SlopePatternStyle:
        return cls(name="Grid", pattern_type=SlopePatternType.GRID, spacing_horizontal=5, spacing_vertical=2, color=5)

    @classmethod
    def steps_style(cls) -> SlopePatternStyle:
        return cls(name="Steps", pattern_type=SlopePatternType.STEPS, color=6)

    @classmethod
    def stakes_style(cls) -> SlopePatternStyle:
        return cls(name="Stakes", pattern_type=SlopePatternType.STAKES, color=1)

    @classmethod
    def berms_style(cls) -> SlopePatternStyle:
        return cls(name="Berms", pattern_type=SlopePatternType.BERMS, color=4)
