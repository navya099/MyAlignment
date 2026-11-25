from dataclasses import replace
import math

from cadgeom import Point2d
import pytest

from myalignment.alignment import (
    Alignment, AlignmentBuilder, AlignmentTableColumn as Column, AlignmentTableStyle,
    AlignmentTableType, TableColumnSpec,
)
from myalignment.enitity.arc_entity import ArcEntity
from myalignment.enitity.spiral_entity import SpiralEntity
from myalignment.export.dxf_writer import DxfWriter
from myalignment.render.alignment_table_renderer import AlignmentTableRenderer
from myalignment.render.label_box import LabelBox
from myalignment.render.primitives import Primitive, PrimitiveType
from myalignment.render.scene import Scene


@pytest.fixture
def alignment():
    return (
        AlignmentBuilder("Main")
        .with_pi_coords([(0, 0), (150, 0), (150, 180)])
        .with_radii([None, 40, None])
        .with_spiral_lengths([0, 12, 0], [0, 16, 0])
        .with_start_station(1000).build()
    )


def _all_columns(kind):
    return AlignmentTableStyle(table_type=kind, columns=tuple(TableColumnSpec(column) for column in Column))


def test_segment_rows_read_geometry_and_use_raw_stations(alignment):
    rows = AlignmentTableRenderer.collect_rows(
        alignment.add_station_equation(1050, 5000), AlignmentTableStyle.segment_style(),
    )
    assert [row[Column.ELEMENT_TYPE] for row in rows] == ["Line", "Spiral", "Curve", "Spiral", "Line"]
    assert rows[0][Column.START_STATION] == 1000
    assert rows[-1][Column.END_STATION] == pytest.approx(alignment.end_station)
    assert rows[0][Column.RADIUS] == ""
    assert sum(row[Column.LENGTH] for row in rows) == pytest.approx(alignment.length)


def test_each_table_filters_and_extracts_its_parameters(alignment):
    line_rows = AlignmentTableRenderer.collect_rows(alignment, AlignmentTableStyle.line_style())
    assert [row[Column.BEARING] for row in line_rows] == pytest.approx([0, 90])
    curve, = AlignmentTableRenderer.collect_rows(alignment, _all_columns(AlignmentTableType.CURVE))
    arc = next(entity.geometry for entity in alignment.entities if isinstance(entity, ArcEntity))
    assert curve[Column.RADIUS] == 40
    assert curve[Column.DELTA] == pytest.approx(math.degrees(arc.delta))
    assert curve[Column.TANGENT] == pytest.approx(40 * math.tan(arc.delta / 2))
    assert curve[Column.EXTERNAL] == pytest.approx(40 * (1 / math.cos(arc.delta / 2) - 1))
    assert curve[Column.MID_ORDINATE] == pytest.approx(40 * (1 - math.cos(arc.delta / 2)))

    spirals = [entity for entity in alignment.entities if isinstance(entity, SpiralEntity)]
    rows = AlignmentTableRenderer.collect_rows(alignment, _all_columns(AlignmentTableType.SPIRAL))
    assert [row[Column.A_VALUE] for row in rows] == pytest.approx([math.sqrt(480), math.sqrt(640)])
    for row, spiral in zip(rows, spirals, strict=True):
        assert row[Column.SPIRAL_TYPE] == "Clothoid"
        assert row[Column.DELTA] == pytest.approx(
            math.degrees(abs(spiral.end_azimuth - spiral.start_azimuth)),
        )
        assert row[Column.TANGENT] == ""


def test_sorting_works_when_key_is_not_a_display_column(alignment):
    style = AlignmentTableStyle(columns=(TableColumnSpec(Column.START_STATION),), sort_by=Column.RADIUS)
    rows = AlignmentTableRenderer.collect_rows(alignment, style)
    assert [row[Column.START_STATION] for row in rows] == [
        alignment.entities[index].start_station for index in (1, 2, 3, 0, 4)
    ]


def test_split_tables_respect_widths_title_headers_and_export(alignment, tmp_path):
    style = AlignmentTableStyle(
        columns=(TableColumnSpec(Column.ELEMENT_TYPE, "요소", 8),
                 TableColumnSpec(Column.START_STATION, "Start", 12, ".1f")),
        split_table=True, max_rows_per_table=2, row_height=4, header_height=5, text_height=2,
    )
    marker = Primitive.circle(Point2d(1, 1), 1)
    original = Scene().add(marker)
    scene = AlignmentTableRenderer.render(original, alignment, style, Point2d(50, 60))
    assert scene.primitives[0] is marker
    assert original.primitives == (marker,)
    borders = [item for item in scene.primitives if item.type is PrimitiveType.POLYLINE]
    assert [item.points[0].x for item in borders] == [50, 75, 100]
    assert [item.points[2].y for item in borders] == [78, 78, 74]
    assert borders[0].points[1].x == 70
    texts = [item for item in scene.primitives if item.type is PrimitiveType.TEXT]
    assert sum(item.text == "요소" for item in texts) == 3
    assert sum(item.text == "Start" for item in texts) == 3
    assert any(item.text == "1000.0" for item in texts)
    for item in texts:
        point = item.points[0]
        box = LabelBox.from_text(point.x, point.y, item.text, item.text_height)
        assert any(border.points[0].x <= box.x_min <= box.x_max <= border.points[1].x + 1e-9
                   for border in borders)
    path = tmp_path / "alignment-table.dxf"
    DxfWriter(scene).write(path)
    assert "Alignment Table (3/3)" in path.read_text(encoding="cp949")


def test_empty_table_does_not_change_the_scene():
    scene = Scene(metadata={"example": True})
    assert AlignmentTableRenderer.render(scene, Alignment(), AlignmentTableStyle.segment_style()) is scene


@pytest.mark.parametrize("change", [{"row_height": 0}, {"header_height": math.nan}, {"max_rows_per_table": 0}])
def test_invalid_style_settings(change):
    with pytest.raises(ValueError):
        replace(AlignmentTableStyle.segment_style(), **change)
