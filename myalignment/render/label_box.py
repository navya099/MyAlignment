from __future__ import annotations

from dataclasses import dataclass
import math
from unicodedata import combining, east_asian_width


@dataclass(frozen=True, slots=True)
class LabelBox:
    """텍스트가 차지하는 도면 좌표의 근사 경계 상자."""

    x_min: float = 0.0
    y_min: float = 0.0
    x_max: float = 0.0
    y_max: float = 0.0
    label_id: str = ""

    @property
    def width(self) -> float:
        return self.x_max - self.x_min

    @property
    def height(self) -> float:
        return self.y_max - self.y_min

    @property
    def center_x(self) -> float:
        return (self.x_min + self.x_max) / 2

    @property
    def center_y(self) -> float:
        return (self.y_min + self.y_max) / 2

    def intersects(self, other: LabelBox, padding: float = 0.0) -> bool:
        return not (
            self.x_max + padding <= other.x_min
            or other.x_max + padding <= self.x_min
            or self.y_max + padding <= other.y_min
            or other.y_max + padding <= self.y_min
        )

    def shifted(self, dx: float, dy: float) -> LabelBox:
        return LabelBox(
            self.x_min + dx, self.y_min + dy, self.x_max + dx, self.y_max + dy, self.label_id,
        )

    @classmethod
    def from_text(
        cls, x: float, y: float, text: str, height: float, char_width_ratio: float = 0.6,
        rotation: float = 0.0, label_id: str = "",
    ) -> LabelBox:
        """삽입점을 기준으로 텍스트의 네 모서리를 회전한다."""
        lines = text.split("\n")
        width = height * max(
            sum(1.0 if east_asian_width(char) in ("W", "F") else char_width_ratio
                for char in line if not combining(char))
            for line in lines
        )
        # 첫 줄의 삽입점은 좌하단이며 후속 줄은 아래로 배치된다.
        bottom, top = -height * (len(lines) - 1), height
        cos_r, sin_r = math.cos(rotation), math.sin(rotation)
        corners = [
            (x + u * cos_r - v * sin_r, y + u * sin_r + v * cos_r)
            for u in (0.0, width) for v in (bottom, top)
        ]
        xs, ys = zip(*corners)
        return cls(min(xs), min(ys), max(xs), max(ys), label_id or text)
