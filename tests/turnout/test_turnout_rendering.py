from dataclasses import replace
import math

import pytest

from myalignment.alignment import AlignmentBuilder
from myalignment.render.primitives import PrimitiveType
from myalignment.render.primitives_3d import PrimitiveType3D
from myalignment.render.scene import Scene
from myalignment.render.scene_3d import Scene3D
from myalignment.render.turnout_3d_renderer import Turnout3DRenderer
from myalignment.render.turnout_renderer import TurnoutRenderer
from myalignment.turnout.geometry import TurnoutGeometryCalculator
from myalignment.turnout.turnout import Turnout
from myalignment.turnout.turnout_preview import TurnoutPreview
from myalignment.turnout.type import TurnoutSide, TurnoutType


@pytest.fixture
def alignment():
    return (
        AlignmentBuilder("Main").with_pi_coords([(10, 20), (210, 20)])
        .with_start_station(1000).as_rail_alignment(gauge=1.52).build()
    )


@pytest.fixture
def turnout():
    return Turnout("분기기 T1", TurnoutType("F12", 12, 0, 100), "Main", "Branch", 1030, TurnoutSide.LEFT)


@pytest.mark.parametrize("side", [TurnoutSide.LEFT, TurnoutSide.RIGHT])
def test_geometry_reuses_arc_end_and_offsets_both_rails(alignment, turnout, side):
    turnout = replace(turnout, side=side)
    geometry = TurnoutGeometryCalculator.calculate(alignment, turnout, sample_step=1, extension=0)
    kind = turnout.turnout_type

    assert geometry.is_valid
    assert geometry.gauge == 1.52
    assert (geometry.ps_point.x, geometry.ps_point.y) == pytest.approx((40, 20))
    assert geometry.pf_station == pytest.approx(1030 + kind.run)
    assert (geometry.pf_point.x, geometry.pf_point.y) == pytest.approx((40 + kind.run, 20))
    assert (geometry.pc_point.x, geometry.pc_point.y) == pytest.approx((40 + kind.run, 20 + side.sign * kind.rise))
    assert geometry.pc_station == pytest.approx(kind.arc_length)
    assert geometry.branch_azimuth == pytest.approx(side.sign * kind.frog_angle)

    for left, right in (
        (geometry.main_left_rail, geometry.main_right_rail),
        (geometry.branch_left_rail, geometry.branch_right_rail),
    ):
        assert len(left) == len(right) > 2
        assert all(a.distance_to(b) == pytest.approx(1.52) for a, b in zip(left, right))
    assert geometry.branch_left_rail[0] != geometry.branch_left_rail[1]
    assert geometry.branch_left_rail[0].y > geometry.branch_right_rail[0].y


def test_main_track_uses_curved_alignment_offsets():
    axis = (
        AlignmentBuilder("Main").with_pi_coords([(0, 0), (150, 0), (150, 150)])
        .with_radii([None, 40, None]).build()
    )
    station = axis.entities[1].start_station + 5
    turnout = Turnout("T1", TurnoutType("F12", 12, 5, 100), "Main", "Branch", station)
    geometry = TurnoutGeometryCalculator.calculate(axis, turnout, gauge=1.5, extension=0)
    assert geometry.is_valid
    assert geometry.main_left_rail[0].distance_to(axis.point_at(station, -0.75)) < 1e-9
    assert geometry.main_right_rail[-1].distance_to(axis.point_at(geometry.pf_station, 0.75)) < 1e-9
    assert geometry.main_right_rail[0].y != geometry.main_right_rail[-1].y


def test_invalid_location_is_reported_by_both_renderers(alignment, turnout):
    near_end = replace(turnout, station_on_source=1199)
    invalid = TurnoutGeometryCalculator.calculate(alignment, near_end)
    assert not invalid.is_valid
    assert invalid.error_message
    with pytest.raises(ValueError, match="범위"):
        TurnoutRenderer.render_2d(Scene(), invalid)
    with pytest.raises(ValueError, match=near_end.name):
        Turnout3DRenderer.render_turnout_set_3d(Scene3D(), (near_end,), alignment)
    assert not TurnoutGeometryCalculator.calculate(alignment, replace(turnout, source_alignment_name="Other")).is_valid


def test_2d_and_3d_render_the_same_rails_and_center_the_ties(alignment, turnout):
    geometry = TurnoutGeometryCalculator.calculate(alignment, turnout, sample_step=1, extension=0)
    plan = TurnoutRenderer.render_2d(Scene(), geometry, show_labels=False, show_markers=False)
    spatial = Turnout3DRenderer.render_3d(Scene3D(), geometry, elevation=100, rail_elevation=0.2, show_markers=False)
    assert {layer.name for layer in plan.layers} == {
        TurnoutRenderer.MAIN_RAIL_LAYER, TurnoutRenderer.BRANCH_RAIL_LAYER,
    }
    assert len(plan.primitives) == 4
    rails = [p for p in spatial.primitives if p.type is PrimitiveType3D.POLYLINE]
    assert len(rails) == 4
    for two, three in zip(plan.primitives, rails):
        assert [(p.x, p.y) for p in two.points] == [(p.x, p.y) for p in three.points]
        assert {p.z for p in three.points} == {100.2}
    ties = [p for p in spatial.primitives if p.style.layer == Turnout3DRenderer.TIE_LAYER]
    assert ties
    for index, tie in enumerate(ties[:3]):
        left, right = tie.points
        assert (left.x + right.x) / 2 == pytest.approx(40 + index * 0.6)
        assert (left.y + right.y) / 2 == pytest.approx(20)
        assert left.distance_to(right) == pytest.approx(1.52 + 0.6)
        assert left.z == right.z == pytest.approx(100.1)


def test_preview_exports_2d_dxf_3d_dxf_and_html(tmp_path, alignment, turnout):
    plan_path, dxf_path, html_path = (tmp_path / name for name in ("plan.dxf", "rail.dxf", "rail.html"))
    plan = TurnoutPreview.preview_2d(alignment, turnout, plan_path)
    spatial = TurnoutPreview.preview_3d(alignment, (turnout,), 100.0, dxf_path, html_path)
    labels = [p.text for p in plan.primitives if p.type is PrimitiveType.TEXT]
    assert {"PS (STA 1030.00)", turnout.name, "1/12"} <= set(labels)
    assert len([p for p in spatial.primitives if p.style.layer == Turnout3DRenderer.MARKER_LAYER]) == 3
    assert turnout.name in plan_path.read_text(encoding="cp949")
    assert Turnout3DRenderer.BRANCH_RAIL_LAYER in dxf_path.read_text(encoding="cp949")
    assert Turnout3DRenderer.TIE_LAYER in html_path.read_text(encoding="utf-8")
    assert "Turnout 3D (1)" in html_path.read_text(encoding="utf-8")


@pytest.mark.parametrize("options", [{"gauge": 0}, {"sample_step": math.inf}, {"extension": -1}])
def test_invalid_calculator_options(alignment, turnout, options):
    with pytest.raises(ValueError):
        TurnoutGeometryCalculator.calculate(alignment, turnout, **options)
