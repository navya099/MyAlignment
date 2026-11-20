from dataclasses import replace

import pytest

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.alignment.equation_label_style import StationEquationLabelStyle
from myalignment.alignment.label_component import AlignmentLabelComponent
from myalignment.alignment.label_set import AlignmentLabelSet
from myalignment.alignment.station_equation_type import StationEquationType
from myalignment.export.dxf_writer import DxfWriter
from myalignment.render.alignment_label_renderer import AlignmentLabelRenderer
from myalignment.render.alignment_renderer import AlignmentRenderer
from myalignment.render.primitives import PrimitiveType
from myalignment.render.scene import Scene


def _alignment():
    return (
        AlignmentBuilder().with_pi_coords([(10, 20), (10, 320)]).build()
        .add_station_equation(75, 500)
        .add_station_equation(200, 120, StationEquationType.DECREASING)
        .add_station_equation(310, 1000)
    )


def test_plan_draws_standard_equation_labels_at_raw_positions(tmp_path):
    scene = AlignmentRenderer.render_plan(_alignment(), render_labels=True)
    marks = [p for p in scene.primitives if p.style.layer == "C-ALIGN-EQUATION"]
    assert [p.text for p in marks if p.type is PrimitiveType.TEXT] == [
        "STA 500.00 (Eq)", "Raw: 75.00", "Δ: +425.00",
        "STA 120.00 (Eq-)", "Raw: 200.00", "Δ: -80.00",
    ]
    ticks = [p for p in marks if p.type is PrimitiveType.LINE]
    for tick, y in zip(ticks, (95, 220), strict=True):
        assert [p.x for p in tick.points] == pytest.approx([10.8, 9.2])
        assert [p.y for p in tick.points] == pytest.approx([y, y])
        assert tick.style.color == 1
    path = tmp_path / "equations.dxf"
    DxfWriter(scene).write(path)
    assert "STA 120.00 (Eq-)" in path.read_text("cp949")


def test_equation_style_presets_and_render_switch():
    alignment = _alignment()
    minimal = AlignmentLabelSet().with_equation_style(StationEquationLabelStyle.minimal())
    original = Scene()
    styled = alignment.with_label_set(minimal)
    assert AlignmentLabelRenderer.render(original, styled, render_equations=False) is original
    scene = AlignmentLabelRenderer.render(original, styled)
    assert [p.text for p in scene.primitives if p.type is PrimitiveType.TEXT] == [
        "STA 500.00 (Eq)", "STA 120.00 (Eq-)",
    ]
    arrow_style = StationEquationLabelStyle.with_arrow()
    arrow = AlignmentLabelRenderer.render(
        original, styled.with_label_set(minimal.with_equation_style(arrow_style)),
    )
    assert [p.text for p in arrow.primitives if "→" in p.text] == ["75.00 → 500.00", "200.00 → 120.00"]
    no_markers = AlignmentRenderer.render_plan(alignment, render_labels=True, render_equations=False)
    assert all(p.style.layer != "C-ALIGN-EQUATION" for p in no_markers.primitives)


def test_custom_equation_label_uses_incoming_display_station_and_honors_visibility():
    component = AlignmentLabelComponent(contents="<[Station Back]> → <[Station Ahead]> <[Station Jump]>")
    style = replace(
        StationEquationLabelStyle.standard(),
        components=(component, *StationEquationLabelStyle.standard().components[1:]),
        show_raw_station=False, show_delta=False,
    )
    alignment = _alignment().with_label_set(AlignmentLabelSet().with_equation_style(style))
    assert not [p for p in AlignmentLabelRenderer.render(Scene(), alignment).primitives
                if p.type is PrimitiveType.TEXT]

    visible = alignment.with_label_set(alignment.label_set.with_equation_style(replace(style, show_delta=True)))
    texts = [p.text for p in AlignmentLabelRenderer.render(Scene(), visible).primitives
             if p.type is PrimitiveType.TEXT]
    assert texts == ["75.00 → 500.00 +425.00", "Δ: +425.00",
                     "625.00 → 120.00 -505.00", "Δ: -80.00"]
