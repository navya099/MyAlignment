from __future__ import annotations

from itertools import accumulate
import math
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.alignment.curve_spiral_extractor import _curve_parameters, _spiral_parameters
from myalignment.alignment.table_column import AlignmentTableColumn as Column
from myalignment.alignment.table_type import AlignmentTableType
from myalignment.enitity.arc_entity import ArcEntity
from myalignment.enitity.line_entity import LineEntity
from myalignment.enitity.spiral_entity import SpiralEntity
from myalignment.render.label_box import LabelBox
from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.alignment.table_style import AlignmentTableStyle
    from myalignment.enitity.alignment_entity import AlignmentEntity


_ENTITY_TYPES = (
    (LineEntity, AlignmentTableType.LINE),
    (ArcEntity, AlignmentTableType.CURVE),
    (SpiralEntity, AlignmentTableType.SPIRAL),
)


def _values(entity: AlignmentEntity, kind: AlignmentTableType) -> dict[Column, float | str]:
    row = {
        Column.ELEMENT_TYPE: kind.value,
        Column.START_STATION: entity.start_station,
        Column.END_STATION: entity.end_station,
        Column.LENGTH: entity.length,
        Column.BEARING: math.degrees(entity.start_azimuth) % 360,
    }
    if isinstance(entity, ArcEntity):
        values = _curve_parameters(entity)
        row.update({
            Column.RADIUS: values["radius"], Column.DELTA: math.degrees(values["delta"]),
            Column.MID_ORDINATE: values["mid_ordinate"],
        })
        if values["tangent"] is not None:
            row[Column.TANGENT] = values["tangent"]
            row[Column.EXTERNAL] = values["external"]
    elif isinstance(entity, SpiralEntity):
        values = _spiral_parameters(entity)
        row.update({
            Column.RADIUS: values["radius"], Column.DELTA: math.degrees(values["theta"]),
            Column.SPIRAL_TYPE: values["spiral_type"],
        })
        if values["a_value"] is not None:
            row[Column.A_VALUE] = values["a_value"]
    return row


def _text_width(text: str, height: float) -> float:
    return LabelBox.from_text(0, 0, text, height).width


def _format_value(value: float | str, format_spec: str) -> str:
    return value if isinstance(value, str) else format(value, format_spec)


class AlignmentTableRenderer:
    """선형 제원을 수집해 DXF에 저장할 수 있는 표 도형으로 만든다."""

    @classmethod
    def collect_rows(cls, alignment: Alignment, style: AlignmentTableStyle) -> list[dict[Column, float | str]]:
        """지정된 열의 원본 값을 정렬된 행으로 반환한다.

        측점은 원시 측점이고 각도는 도 단위다. 적용할 수 없는 열은
        빈 문자열로 반환하며 정렬 시 해당 값은 끝에 배치한다.
        """
        rows = []
        for entity in alignment.entities:
            kind = next((kind for entity_type, kind in _ENTITY_TYPES if isinstance(entity, entity_type)), None)
            if kind is not None and style.table_type in (AlignmentTableType.SEGMENT, kind):
                rows.append(_values(entity, kind))
        rows.sort(key=lambda row: (style.sort_by not in row, row.get(style.sort_by, "")))
        return [{spec.column: row.get(spec.column, "") for spec in style.columns} for row in rows]

    @classmethod
    def render(
        cls,
        scene: Scene,
        alignment: Alignment,
        style: AlignmentTableStyle,
        insert_point: Point2d | None = None,
    ) -> Scene:
        """첫 표의 좌하단을 insert_point에 두고 나머지 표를 오른쪽에 배치한다."""
        rows = cls.collect_rows(alignment, style)
        if not rows:
            return scene
        origin = Point2d(0, 0) if insert_point is None else insert_point
        headers = tuple(spec.header or spec.column.value for spec in style.columns)
        contents = [
            tuple(_format_value(row[spec.column], spec.format_spec) for spec in style.columns)
            for row in rows
        ]
        widths = tuple(
            spec.width or max(
                20.0, max(_text_width(text, style.text_height) for text in texts) + 2,
            )
            for spec, texts in zip(style.columns, zip(headers, *contents))
        )
        edges = tuple(accumulate(widths, initial=0.0))
        per_table = style.max_rows_per_table if style.split_table else len(contents)
        table_count = math.ceil(len(contents) / per_table)
        appearance = Style(color=7, layer=style.layer, lineweight=0.3)
        primitives = []
        for page, start in enumerate(range(0, len(contents), per_table), 1):
            x = origin.x + (page - 1) * (edges[-1] + 5)
            title = style.title
            if title and table_count > 1:
                title = f"{title} ({page}/{table_count})"
            primitives.extend(cls._table(
                Point2d(x, origin.y), edges, headers, contents[start:start + per_table], title, style, appearance,
            ))
        return scene.add_layer(Layer(style.layer, color=7)).add_all(primitives)

    @classmethod
    def _table(cls, origin, edges, headers, rows, title, style, appearance):
        x, y = origin.x, origin.y
        body_top = y + len(rows) * style.row_height
        header_top = body_top + style.header_height
        top = header_top + style.header_height if title else header_top
        right = x + edges[-1]
        yield Primitive.polyline(
            (origin, Point2d(right, y), Point2d(right, top), Point2d(x, top)),
            closed=True, style=appearance,
        )
        for offset in edges[1:-1]:
            yield Primitive.line(Point2d(x + offset, y), Point2d(x + offset, header_top), appearance)
        for index in range(1, len(rows) + 1):
            height = y + index * style.row_height
            yield Primitive.line(Point2d(x, height), Point2d(right, height), appearance)
        if title:
            yield Primitive.line(Point2d(x, header_top), Point2d(right, header_top), appearance)
            yield cls._cell(title, x, header_top, edges[-1], style.header_height, style, appearance)

        for values, bottom, height in (
            (headers, body_top, style.header_height),
            *((row, body_top - index * style.row_height, style.row_height)
              for index, row in enumerate(rows, 1)),
        ):
            for text, left, right_edge in zip(values, edges, edges[1:]):
                if text:
                    yield cls._cell(text, x + left, bottom, right_edge - left, height, style, appearance)

    @staticmethod
    def _cell(text, x, y, width, height, style, appearance):
        padding = min(1.0, width / 10)
        font = min(style.text_height, height * 0.8)
        measured = _text_width(text, font)
        if measured > width - 2 * padding:
            font *= (width - 2 * padding) / measured
        return Primitive.text(Point2d(x + padding, y + (height - font) / 2), text, font, style=appearance)
