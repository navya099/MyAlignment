from dataclasses import replace
import math

from cadgeom import Point2d
import pytest

from myalignment.alignment import Alignment, AlignmentBuilder, CurveLabelStyle, SpiralLabelStyle
from myalignment.alignment.curve_spiral_extractor import CurveSpiralExtractor
from myalignment.alignment.label_component import AlignmentLabelComponent
from myalignment.alignment.label_set import AlignmentLabelSet
from myalignment.alignment.label_style import AlignmentLabelStyle
from myalignment.alignment.label_type import AlignmentLabelType
from myalignment.enitity.entity_collection import AlignmentEntityCollection
from myalignment.enitity.line_entity import LineEntity
from myalignment.enitity.spiral_entity import SpiralEntity
from myalignment.enum.spiraltype import SpiralType
from myalignment.export.dxf_writer import DxfWriter
from myalignment.render.alignment_renderer import AlignmentRenderer
from myalignment.render.curve_label_renderer import CurveLabelRenderer
from myalignment.render.primitives import PrimitiveType
from myalignment.render.scene import Scene
from myalignment.render.spiral_label_renderer import SpiralLabelRenderer
from myalignment.utils import CurveDirection


@pytest.fixture
def axis():
    return (
        AlignmentBuilder("Main").with_pi_coords([(0, 0), (150, 0), (150, 180)])
        .with_radii([None, 40, None]).with_spiral_lengths([0, 12, 0], [0, 16, 0])
        .with_start_station(1000).build()
    )


def _texts(scene, layer=None):
    return [
        primitive.text for primitive in scene.primitives
        if primitive.type is PrimitiveType.TEXT and (layer is None or primitive.style.layer == layer)
    ]


def test_extractor_uses_real_geometry_and_neighbor_transitions(axis):
    curve, = CurveSpiralExtractor.extract_curves(axis)
    assert curve["chord"] == pytest.approx(curve["bc_point"].distance_to(curve["ec_point"]))
    assert curve["mid_station"] == pytest.approx(curve["start_station"] + curve["length"] / 2)
    first, last = CurveSpiralExtractor.extract_spirals(axis)
    assert first["is_entry"] and not last["is_entry"]
    assert last["is_exit"] and not first["is_exit"]
    assert first["sc_station"] == pytest.approx(curve["start_station"])
    assert last["cs_station"] == pytest.approx(curve["end_station"])
    assert first["a_value"] == pytest.approx(math.sqrt(40 * 12))
    assert last["a_value"] == pytest.approx(math.sqrt(40 * 16))
    for item in (first, last):
        assert item["theta"] == pytest.approx(abs(item["entity"].end_azimuth - item["entity"].start_azimuth))
        assert math.hypot(item["x"], item["y"]) == pytest.approx(
            item["entity"].start_coord.distance_to(item["entity"].end_coord),
        )


def test_dms_rounding_carries_minutes_and_preserves_sign():
    assert CurveSpiralExtractor.format_angle(math.radians(12 + 59 / 60 + 59.98 / 3600)) == '13°00\'00.0"'
    assert CurveSpiralExtractor.format_angle(math.radians(-0.5)) == '-0°30\'00.0"'
    assert CurveSpiralExtractor.format_angle(math.pi / 2, "decimal") == "90.0000°"


def test_detailed_curve_style_uses_display_station_and_hides_disabled_fields(axis):
    curve, = CurveSpiralExtractor.extract_curves(axis)
    raw = curve["start_station"]
    adjusted = axis.add_station_equation(raw, 2000)
    style = replace(CurveLabelStyle.detailed(), angle_format="decimal", show_external=False)
    scene = CurveLabelRenderer.render(Scene(), adjusted, style)
    texts = _texts(scene)
    assert "BC = 2000.00" in texts
    assert f"Δ = {math.degrees(curve['delta']):.4f}°" in texts
    assert f"C = {curve['chord']:.3f}" in texts
    assert not any(text.startswith("E =") for text in texts)


def test_spiral_station_zero_and_non_clothoid_parameters():
    line = LineEntity.create(Point2d(-10, 0), Point2d(0, 0), -10)
    spiral = SpiralEntity.create(Point2d(0, 0), 0, 100, 20, SpiralType.JapaneseCubic, CurveDirection.RIGHT, 0)
    axis = Alignment(entities=AlignmentEntityCollection((line, spiral)))
    data, = CurveSpiralExtractor.extract_spirals(axis)
    assert data["ts_station"] == 0
    assert data["a_value"] is None
    assert data["theta"] == pytest.approx(abs(spiral.end_azimuth - spiral.start_azimuth))
    texts = _texts(SpiralLabelRenderer.render(Scene(), axis, SpiralLabelStyle.stations()))
    assert "TS: 0.00" in texts
    assert "SC: —" in texts


def test_curve_points_and_defaults_render_together_and_export(axis, tmp_path):
    points = AlignmentLabelStyle.curve_point_style()
    styled = axis.with_label_set(AlignmentLabelSet.standard().with_style(AlignmentLabelType.CURVE_POINT, points))
    scene = AlignmentRenderer.render_plan(styled, render_labels=True, render_spirals=False)
    assert "CURVE" in _texts(scene, "C-ALIGN-CURVE-LABEL")
    assert not _texts(scene, "C-ALIGN-SPIRAL-LABEL")
    labels = _texts(scene, "C-ALIGN-CURVE-POINT")
    assert labels[0].startswith("BC STA") and labels[2].startswith("EC STA")
    assert labels[1].startswith("N:") and " E: " in labels[1]
    output = tmp_path / "curve-labels.dxf"
    DxfWriter(scene).write(output)
    assert "C-ALIGN-CURVE-POINT" in output.read_text(encoding="cp949")


def test_multiline_template_hides_only_rows_with_disabled_fields(axis):
    style = CurveLabelStyle(
        components=(AlignmentLabelComponent(contents="R <[Radius]>\\PL <[Length]>"),),
        show_radius=False,
    )
    assert _texts(CurveLabelRenderer.render(Scene(), axis, style)) == [
        f"L {CurveSpiralExtractor.extract_curves(axis)[0]['length']:.3f}",
    ]
