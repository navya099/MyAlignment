from dataclasses import replace

import pytest

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.codes import LinkCode
from myalignment.assembly.parameter.display import show_parameters
from myalignment.assembly.parameter.parameter import Parameter
from myalignment.assembly.parameter.parameter_set import ParameterSet
from myalignment.assembly.parameter.parameter_type import ParameterType as Kind
from myalignment.assembly.parameterized.builder import ParametricAssemblyBuilder
from myalignment.assembly.parameterized.parametric_lane import ParametricLane
from myalignment.assembly.parameterized.parametric_slope import ParametricSlope
from myalignment.assembly.section_context import SectionContext
from myalignment.cant.curve import CantCriticalStation, CantCurve, CantPivotMethod
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.surface.tin_surface import TinSurface
from myalignment.target.mapping import TargetMapping
from myalignment.target.reference import TargetReference


def test_parameter_validation_and_immutable_updates():
    lane = ParametricLane.create(4, -0.03)
    revised = lane.with_params(width=5, apply_aor="True")
    assert lane.get_param("width") == 4 and not lane.apply_aor
    assert revised.apply_aor and revised.get_param("computed_elevation_drop") == pytest.approx(-0.15)
    assert revised.param_set.outputs()["computed_area"] == 5
    assert "computed_slope_percent: -3.000 %" in show_parameters(revised)
    assert revised.with_params(width=None).get_param("width") == 4
    with pytest.raises(ValueError, match="minimum"):
        ParametricLane.create(0)
    with pytest.raises(ValueError, match="finite"):
        lane.with_params(slope=float("nan"))
    with pytest.raises(ValueError, match="read-only"):
        lane.with_params(computed_area=1)
    with pytest.raises(KeyError, match="Unknown parameter"):
        lane.with_params(wdth=8)
    with pytest.raises(ValueError, match="Duplicate"):
        ParameterSet((Parameter("width"), Parameter("width")))
    with pytest.raises(ValueError, match="one of"):
        lane.with_params(apply_aor="invalid")


def test_formula_dependencies_context_and_errors():
    params = ParameterSet((
        Parameter("total", Kind.OUTPUT, expression="adjusted * 2"),
        Parameter("adjusted", Kind.COMPUTED, expression="width + allowance"),
        Parameter("width", default=3),
    ))
    assert params.evaluate_computed({"allowance": 0.5}).outputs() == {"total": 7}
    assert params.set_value("width", 4).evaluate_computed({"allowance": 0.5}).outputs() == {"total": 9}
    with pytest.raises(ValueError, match="Unknown formula variable"):
        params.evaluate_computed()
    for formula, error in [("x + 1", "Circular"), ("1/0", "division"), ("width.real", "only arithmetic"),
                           ("abs(width)", "only arithmetic"), ("10.0 * 1e308", "finite")]:
        item = Parameter("x", Kind.COMPUTED, expression=formula)
        with pytest.raises(ValueError, match=error):
            ParameterSet((item, Parameter("width", default=2))).evaluate_computed()


def test_corridor_samples_computed_width_at_station():
    axis = AlignmentBuilder("Main").with_pi_coords([(0, 0), (30, 0)]).build()
    lane = replace(ParametricLane(), param_set=ParameterSet((
        Parameter("width", Kind.COMPUTED, expression="3 + station / 10"),
        Parameter("slope", default=-0.04),
    )))
    assembly = AssemblyBuilder().add_right(lane).build()
    corridor = (
        CorridorBuilder().add_baseline_from_alignment(axis).add_region("Lane", 0, 30, assembly).build()
    )
    for station, (_, links) in corridor.sample_cross_sections().items():
        link, = links
        assert link.end.x == pytest.approx(3 + station / 10)
        assert link.end.z == pytest.approx(-0.04 * link.end.x)


def test_parametric_builder_connects_lanes_shoulders_and_default_slopes():
    assembly = ParametricAssemblyBuilder().with_lane(4).with_shoulder(1).with_slope(2, 3).build()
    _, links = assembly.generate_cross_section()
    assert [link.code for link in links] == [LinkCode.PAVEMENT, LinkCode.SHOULDER, LinkCode.SLOPE] * 2
    for lane, shoulder, slope in (links[:3], links[3:]):
        assert (lane.end.x, lane.end.z) == (shoulder.start.x, shoulder.start.z)
        assert (shoulder.end.x, shoulder.end.z) == (slope.start.x, slope.start.z)
        assert abs(slope.end.x) == pytest.approx(11)
        assert slope.end.z == pytest.approx(-3.12)
        assert not slope.end.is_parametric


def test_slope_intersects_real_ground_on_each_side_and_resolves_custom_target():
    axis = AlignmentBuilder("Main").with_pi_coords([(0, 0), (20, 0)]).build()
    terrain = TinSurface.from_points([(0, -10, -4), (20, -10, -4), (0, 10, 4), (20, 10, 4)])
    context = SectionContext.from_alignment(axis, 10, surfaces={"Ground": terrain})
    targets = TargetMapping((TargetReference("NaturalGround", object_name="Ground"),))
    slope = ParametricSlope.create(1.5, 5).with_params(target_surface="NaturalGround")
    for sign in (-1, 1):
        _, links = slope.place_at(sign * 4, 0, sign, targets, context=context)
        a, b = links[0].start, links[0].end
        assert b.is_parametric and sign * b.x > 4
        assert b.z == pytest.approx(-0.4 * b.x)
        assert abs(b.x - a.x) / abs(b.z - a.z) == pytest.approx(1.5)

    _, missing = slope.place_at(4, 0, 1, targets)
    assert missing[0].end.x == pytest.approx(11.5)
    assert not missing[0].end.is_parametric


def test_aor_toggle_and_connected_shoulder():
    cant = CantCurve(start_station=0, end_station=20, pivot_method=CantPivotMethod.CENTERLINE,
                     critical_stations=(CantCriticalStation(0, 0.15),))
    standard = ParametricAssemblyBuilder().build()

    def section(assembly):
        corridor = (
            CorridorBuilder().add_region_with_assembly("Test", 0, 20, assembly, cant_curve=cant).build()
        )
        return corridor.cross_section_at(10)[1]

    disabled = section(standard)
    assert disabled[0].end.z == pytest.approx(-0.07)
    lane, *rest = standard.right_subassemblies
    enabled = section(replace(standard, right_subassemblies=(lane.with_params(apply_aor=True), *rest)))
    assert enabled[0].end.z != pytest.approx(-0.07)
    for links in (enabled, disabled):
        assert links[0].end.z == pytest.approx(links[1].start.z)


def test_conditional_branch_places_parametric_geometry_with_same_context():
    from myalignment.assembly.conditional.builder import ConditionalSubassemblyBuilder

    lane = replace(ParametricLane(), param_set=ParameterSet((
        Parameter("width", Kind.COMPUTED, expression="3 + station / 10"),
        Parameter("slope", default=-0.04),
    )))
    branch = ConditionalSubassemblyBuilder().else_(lane).build()
    assembly = AssemblyBuilder().add_conditional("left", branch).build()
    _, (link,) = assembly.generate_cross_section(context=SectionContext(station=15))
    assert link.end.x == pytest.approx(-4.5)
    assert link.end.z == pytest.approx(-0.18)
