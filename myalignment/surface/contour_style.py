from __future__ import annotations

from dataclasses import dataclass
import math

from myalignment.surface.contour_type import ContourType


@dataclass(frozen=True, slots=True)
class ContourStyle:
    """등고선의 표고 간격, 표시 및 레이블 설정."""

    name: str = "Standard"
    major_interval: float = 5.0
    minor_interval: float = 1.0
    show_major: bool = True
    show_minor: bool = True
    show_labels: bool = True
    major_color: int = 7
    minor_color: int = 8
    major_lineweight: float = 0.5
    minor_lineweight: float = 0.2
    label_height: float = 1.5
    label_color: int = 7
    label_interval_distance: float = 100.0
    major_layer: str = "C-TOPO-MAJOR-CONT"
    minor_layer: str = "C-TOPO-MINOR-CONT"
    label_layer: str = "C-TOPO-CONT-TEXT"
    user_contours: tuple[float, ...] = ()
    elevation_colors: tuple[tuple[float, int], ...] = ()
    user_color: int = 1
    user_lineweight: float = 0.6
    user_layer: str = "C-TOPO-USER-CONT"

    def __post_init__(self):
        for name in ("major_interval", "minor_interval", "label_height", "label_interval_distance"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        for width in (self.major_lineweight, self.minor_lineweight, self.user_lineweight):
            if not math.isfinite(width) or width < 0:
                raise ValueError("lineweights must be finite and nonnegative")
        for layer in (self.major_layer, self.minor_layer, self.user_layer, self.label_layer):
            if not layer.strip() or any(ord(char) < 32 for char in layer):
                raise ValueError("layer must be nonempty single-line text")
        elevations = tuple(self.user_contours)
        colors = tuple(tuple(pair) for pair in self.elevation_colors)
        if not all(map(math.isfinite, (*elevations, *(elevation for elevation, _ in colors)))):
            raise ValueError("contour elevations must be finite")
        if any(type(color) is not int or not 0 <= color <= 256 for color in (
            self.major_color, self.minor_color, self.user_color, self.label_color, *(color for _, color in colors),
        )):
            raise ValueError("colors must be ACI integers between 0 and 256")
        object.__setattr__(self, "user_contours", elevations)
        object.__setattr__(self, "elevation_colors", colors)

    @classmethod
    def standard(cls) -> ContourStyle:
        return cls()

    @classmethod
    def dense(cls) -> ContourStyle:
        return cls(major_interval=1.0, minor_interval=0.2)

    @classmethod
    def sparse(cls) -> ContourStyle:
        return cls(major_interval=10.0, minor_interval=2.0)

    def color_for_elevation(self, elevation: float) -> int | None:
        """가장 가까운 표고 기준점의 색상을 반환한다."""
        if not self.elevation_colors:
            return None
        return min(self.elevation_colors, key=lambda item: (abs(item[0] - elevation), item[0]))[1]

    def appearance(self, contour_type: ContourType, elevation: float) -> tuple[str, int, float]:
        """레이어, 실제 색상, 선가중치를 반환한다."""
        if contour_type is ContourType.MAJOR:
            layer, color, weight = self.major_layer, self.major_color, self.major_lineweight
        elif contour_type is ContourType.MINOR:
            layer, color, weight = self.minor_layer, self.minor_color, self.minor_lineweight
        else:
            layer, color, weight = self.user_layer, self.user_color, self.user_lineweight
        override = self.color_for_elevation(elevation)
        return layer, color if override is None else override, weight

    def is_visible(self, contour_type: ContourType) -> bool:
        """유형별 표시 설정을 반환한다."""
        return {
            ContourType.MAJOR: self.show_major, ContourType.MINOR: self.show_minor, ContourType.USER: True,
        }[contour_type]
