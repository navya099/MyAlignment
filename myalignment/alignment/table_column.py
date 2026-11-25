from dataclasses import dataclass
from enum import Enum
import math


class AlignmentTableColumn(Enum):
    """선형 제원표의 열 항목."""

    ELEMENT_TYPE = "Element Type"
    START_STATION = "Start Station"
    END_STATION = "End Station"
    LENGTH = "Length"
    BEARING = "Bearing"
    RADIUS = "Radius"
    DELTA = "Delta"
    TANGENT = "Tangent"
    EXTERNAL = "External"
    MID_ORDINATE = "Mid Ordinate"
    SPIRAL_TYPE = "Spiral Type"
    A_VALUE = "A Value"


@dataclass(frozen=True, slots=True)
class TableColumnSpec:
    """열 제목과 도면 폭, 숫자 형식. 폭이 0이면 내용에 맞춰 계산한다."""

    column: AlignmentTableColumn
    header: str = ""
    width: float = 0.0
    format_spec: str = ".2f"

    def __post_init__(self):
        if not isinstance(self.column, AlignmentTableColumn):
            raise ValueError("column must be an AlignmentTableColumn")
        if not math.isfinite(self.width) or self.width < 0:
            raise ValueError("width must be finite and nonnegative")
        if any(ord(char) < 32 for char in self.header + self.format_spec):
            raise ValueError("header and format_spec must be single-line text")
        try:
            format(1.0, self.format_spec)
        except ValueError as error:
            raise ValueError(f"Invalid numeric format: {self.format_spec!r}") from error
