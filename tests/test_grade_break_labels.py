from dataclasses import replace

import pytest

from myalignment.export.dxf_writer import DxfWriter
from myalignment.profile.grade_break_set import GradeBreakLabelSet
from myalignment.profile.grade_break_style import GradeBreakLabelStyle
from myalignment.profile.profile import ProfileBuilder
from myalignment.profile.view_style import ProfileViewStyle
from myalignment.render.grade_break_label_renderer import GradeBreakLabelRenderer
from myalignment.render.primitives import PrimitiveType
from myalignment.render.profile_view_renderer import ProfileViewRenderer
from myalignment.render.scene import Scene
from myalignment.render.section_grade_break_renderer import SectionViewGradeBreakRenderer
from myalignment.render.section_view_renderer import SectionViewRenderer
from myalignment.render.stagger_config import StaggerConfig
from myalignment.section.section_view_data import SectionLink, SectionPoint, SectionViewData
from myalignment.section.section_view_style import SectionViewStyle


def _tangents():
    return (ProfileBuilder().add_tangent(100, 150, 13, 15.5)
            .add_tangent(150, 200, 15.5, 14).build())


def test_grade_break_text_options_and_arrows():
    profile = _tangents()
    minimal = GradeBreakLabelSet.standard().get_style("minimal")
    scene = GradeBreakLabelRenderer.render(Scene(), profile, replace(minimal, use_sign=False), 2)
    assert [p.text for p in scene.primitives if p.type is PrimitiveType.TEXT] == ["5.00% → -3.00%"]

    arrows = GradeBreakLabelStyle.with_arrows()
    result = GradeBreakLabelRenderer.render(Scene(), profile, arrows, 2)
    lines = [p for p in result.primitives if p.type is PrimitiveType.LINE]
    assert len(lines) == 6
    assert [(p.x, p.y) for p in lines[0].points] == [pytest.approx((146, 30.6)), (150, 31)]
    assert [(p.x, p.y) for p in lines[3].points] == [(150, 31), pytest.approx((154, 30.76))]
    disabled = GradeBreakLabelRenderer.render(Scene(), profile, replace(arrows, show_arrows=False), 2)
    assert all(p.type is PrimitiveType.TEXT for p in disabled.primitives)


def test_profile_view_replaces_generic_grade_break_and_exports(tmp_path):
    scene = ProfileViewRenderer.render(
        [_tangents()], "A", ProfileViewStyle(vertical_exaggeration=2),
        grade_break_style=GradeBreakLabelStyle.standard(), stagger_config=StaggerConfig(),
    )
    texts = [p.text for p in scene.primitives if p.type is PrimitiveType.TEXT]
    assert "ΔG: -8.00%" in texts and "STA 150.00" in texts and "EL 15.500" in texts
    assert texts.count("STA 150.00") == 1
    assert "PVI" not in texts
    path = tmp_path / "grade-break.dxf"
    DxfWriter(scene).write(path)
    assert "G1: +5.00%" in path.read_text("cp949")


def test_curve_grade_labels_use_signed_k_per_percentage_point():
    profile = ProfileBuilder().add_symmetric_parabola(150, 15.5, .05, -.03, 100).build()
    standard = GradeBreakLabelRenderer.render(Scene(), profile)
    assert [p.text for p in standard.primitives if p.text in {"VPC", "PVI", "VPT"}] == ["VPC", "PVI", "VPT"]
    scene = GradeBreakLabelRenderer.render(Scene(), profile, GradeBreakLabelStyle.with_k_value())
    assert [p.text for p in scene.primitives if p.text.startswith("K:")] == ["K: -12.50"] * 3
    assert "EL 15.500" in [p.text for p in scene.primitives]


def test_section_grade_break_respects_offset_order_and_threshold():
    a, b, c, d = (SectionPoint(*pt) for pt in ((-10, 1), (0, 2), (10, 1.8), (20, 1.55)))
    data = SectionViewData(100, (a, b, c, d), (
        SectionLink(b, a, slope=10), SectionLink(c, b, slope=-2), SectionLink(c, d, slope=-2.5),
    ))
    style = SectionViewStyle(vertical_exaggeration=2)
    independent = SectionViewGradeBreakRenderer.render(Scene(), data, style)
    assert [p.text for p in independent.primitives if p.type is PrimitiveType.TEXT] == ["Δ-12.0%"]
    scene = SectionViewRenderer.render(Scene(), data, style, render_grade_breaks=True)
    assert tuple(p for p in scene.primitives if p.style.layer == "C-SECTION-GRADEBREAK") == independent.primitives
