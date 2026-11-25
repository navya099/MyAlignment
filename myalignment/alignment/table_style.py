from __future__ import annotations

from dataclasses import dataclass
import math

from myalignment.alignment.table_column import AlignmentTableColumn as Column, TableColumnSpec
from myalignment.alignment.table_type import AlignmentTableType


@dataclass(frozen=True, slots=True)
class AlignmentTableStyle:
    """선형 제원표의 열, 배치, 정렬과 분할 설정."""

    name: str = "Standard"
    table_type: AlignmentTableType = AlignmentTableType.SEGMENT
    columns: tuple[TableColumnSpec, ...] = ()
    title: str = "Alignment Table"
    header_height: float = 3.0
    row_height: float = 2.5
    text_height: float = 1.5
    layer: str = "C-ALIGN-TABLE"
    sort_by: Column = Column.START_STATION
    split_table: bool = False
    max_rows_per_table: int = 30

    def __post_init__(self):
        columns = tuple(self.columns)
        if not columns or any(not isinstance(column, TableColumnSpec) for column in columns):
            raise ValueError("at least one TableColumnSpec is required")
        object.__setattr__(self, "columns", columns)
        if not isinstance(self.table_type, AlignmentTableType) or not isinstance(self.sort_by, Column):
            raise ValueError("invalid table_type or sort_by")
        for name in ("row_height", "header_height", "text_height"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if type(self.max_rows_per_table) is not int or self.max_rows_per_table < 1:
            raise ValueError("max_rows_per_table must be a positive integer")
        if not self.layer.strip() or any(ord(char) < 32 for char in self.layer + self.title):
            raise ValueError("title and layer must be single-line text and layer must not be empty")

    @classmethod
    def segment_style(cls) -> AlignmentTableStyle:
        """직선·원곡선·완화곡선의 측점과 주요 제원."""
        return cls(name="Segment Table", title="Alignment Segment Table", columns=(
            TableColumnSpec(Column.ELEMENT_TYPE, "Type"),
            TableColumnSpec(Column.START_STATION, "Start STA"),
            TableColumnSpec(Column.END_STATION, "End STA"),
            TableColumnSpec(Column.LENGTH, "Length"),
            TableColumnSpec(Column.RADIUS),
            TableColumnSpec(Column.DELTA, "Delta (deg)", format_spec=".4f"),
        ))

    @classmethod
    def line_style(cls) -> AlignmentTableStyle:
        """직선의 측점, 길이와 시작 접선 방위각."""
        return cls(name="Line Table", table_type=AlignmentTableType.LINE, title="Alignment Line Table", columns=(
            TableColumnSpec(Column.START_STATION, "Start STA"),
            TableColumnSpec(Column.END_STATION, "End STA"),
            TableColumnSpec(Column.BEARING, "Bearing (deg)"),
            TableColumnSpec(Column.LENGTH),
        ))

    @classmethod
    def curve_style(cls) -> AlignmentTableStyle:
        """원곡선의 측점, 반경과 원호 제원."""
        return cls(name="Curve Table", table_type=AlignmentTableType.CURVE, title="Alignment Curve Table", columns=(
            TableColumnSpec(Column.START_STATION, "PC Station"),
            TableColumnSpec(Column.END_STATION, "PT Station"),
            TableColumnSpec(Column.RADIUS),
            TableColumnSpec(Column.DELTA, "Delta (deg)"),
            TableColumnSpec(Column.TANGENT),
            TableColumnSpec(Column.LENGTH),
        ))

    @classmethod
    def spiral_style(cls) -> AlignmentTableStyle:
        """완화곡선의 측점, 반경, 유형과 클로소이드 설계 상수."""
        return cls(name="Spiral Table", table_type=AlignmentTableType.SPIRAL, title="Alignment Spiral Table", columns=(
            TableColumnSpec(Column.START_STATION, "Start STA"),
            TableColumnSpec(Column.END_STATION, "End STA"),
            TableColumnSpec(Column.SPIRAL_TYPE),
            TableColumnSpec(Column.RADIUS),
            TableColumnSpec(Column.A_VALUE),
            TableColumnSpec(Column.LENGTH),
        ))
