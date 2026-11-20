from dataclasses import replace

import pytest

from myalignment.export.dxf_writer import DxfWriter
from myalignment.render.primitives import PrimitiveType
from myalignment.render.scene import Scene
from myalignment.render.section_label_renderer import SectionLabelRenderer
from myalignment.render.section_view_renderer import SectionViewRenderer
from myalignment.section.label_component import (
    SectionLabelComponent, SectionLabelComponentType, SectionLabelStyleFactory,
)
from myalignment.section.label_set import SectionLabelSet
from myalignment.section.label_style import SectionLabelStyle
from myalignment.section.label_type import SectionLabelType
from myalignment.section.section_view_data import SectionLink, SectionPoint, SectionViewData
from myalignment.section.section_view_style import SectionViewStyle, section_projection


def _section():
    a, b, c, d = (SectionPoint(*p) for p in ((-5, 9), (0, 10), (5, 8), (5, 6)))
    return SectionViewData(120, (a, b, c, d), (
        SectionLink(b, a, slope=20), SectionLink(b, c, slope=-40), SectionLink(c, d),
    ))


def test_label_types_use_section_geometry_and_skip_vertical_link_slopes():
    data = _section()
    labels = SectionLabelSet.full()
    for style in (SectionLabelStyleFactory.grade_break_style(), SectionLabelStyleFactory.section_segment_style()):
        labels = labels.with_style(style.label_type, style)
    view = SectionViewStyle(show_slope_labels=True)
    scene = SectionViewRenderer.render(Scene(), data, view, labels)
    text = [p.text for p in scene.primitives if p.type is PrimitiveType.TEXT and p.style.layer == "C-SECTION-LABEL"]
    assert "OFF: -5.00" in text and "EL: 10.000" in text
    assert {"L: 5.10", "L: 5.39", "L: 2.00", "+20.0%", "-40.0%"} <= set(text)
    assert "+0.0%" not in text
    assert [t for t in text if t.startswith("GB")] == ["GB +20.0% → -40.0%"]
    assert "STA 120.00 | Width 10.00 | L: 12.48" in text
    assert text.count("+20.0%") == 1
    assert labels.without_style(SectionLabelType.DISTANCE).get_style(SectionLabelType.DISTANCE) is None


def test_custom_components_share_projection_and_export_multiline_dxf(tmp_path):
    data = _section()
    view = SectionViewStyle(vertical_exaggeration=3)
    style = SectionLabelStyle(
        label_type=SectionLabelType.GRADE_BREAK, placement="below", obey_vertical_exaggeration=False,
        components=(
            SectionLabelComponent(contents=r"변곡 <[Offset]>\PEL <[Elevation]>", offset_y=2),
            SectionLabelComponent(SectionLabelComponentType.TICK, offset_y=0, layer="TICKS"),
            SectionLabelComponent(contents="hidden", visible=False),
        ),
    )
    labels = SectionLabelSet().with_style(style.label_type, style)
    scene = SectionViewRenderer.render(Scene(), data, view, labels)
    independent = SectionLabelRenderer.render(Scene(), data, view, labels)
    exported = tuple(p for p in scene.primitives if p.style.layer in ("C-SECTION-LABEL", "TICKS"))
    assert exported == independent.primitives
    *_, plot = section_projection(data, view)
    anchor = plot(0, 10)
    assert exported[0].points[0].y == pytest.approx(anchor.y - 2)
    assert exported[1].points[0].y == pytest.approx(anchor.y - 3.8)
    assert exported[2].points[1].y - exported[2].points[0].y == pytest.approx(1.6)
    path = tmp_path / "section-labels.dxf"
    DxfWriter(scene).write(path)
    text = path.read_text("cp949")
    assert "변곡 +0.00" in text and "EL 10.000" in text and "hidden" not in text


def test_min_spacing_skips_nearby_anchors_of_same_type():
    data = _section()
    style = replace(SectionLabelStyleFactory.offset_elevation_style(), min_spacing=1000)
    scene = SectionLabelRenderer.render(
        Scene(), data, SectionViewStyle(), SectionLabelSet.minimal().with_style(style.label_type, style),
    )
    assert [p.text for p in scene.primitives] == ["OFF: -5.00", "EL: 9.000"]
