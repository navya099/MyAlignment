from enum import Enum
import math

import pytest

from myalignment.assembly import AssemblyBuilder
from myalignment.assembly.codes import LinkCode, PointCode, ShapeCode
from myalignment.assembly.conditional.branch import ConditionalBranch
from myalignment.assembly.conditional.condition import Condition
from myalignment.assembly.conditional.condition_type import ConditionType
from myalignment.assembly.conditional.conditional_subassembly import ConditionalSubassembly
from myalignment.assembly.custom import (
    CustomSubassemblyBuilder, CustomSubassemblyLibrary, GeometryDefinition, LinkDefinition,
    PointDefinition, ShapeDefinition,
)
from myalignment.assembly.custom.presets import custom_lane, custom_slope, custom_urban_road, custom_v_ditch
from myalignment.assembly.section_context import SectionContext
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.quantity.material import Material
from myalignment.quantity.takeoff import QuantityTakeoff
from myalignment.target.mapping import TargetMapping
from myalignment.target.reference import TargetReference


class CustomPointCode(Enum):
    EDGE = "SpecialEdge"


def test_inputs_computed_outputs_and_custom_codes():
    part = (
        CustomSubassemblyBuilder("Custom lane").with_side(-1)
        .with_parameter("width", 3.5, min_value=2)
        .with_output("drop", "slope * width")
        .with_computed("slope", "-2 / 100")
        .add_point(PointCode.CROWN)
        .add_point(CustomPointCode.EDGE, "width", "drop")
        .add_link(0, 1)
        .build()
    )
    updated = part.with_params(width=5)
    assert part.param_set.outputs()["drop"] == pytest.approx(-0.07)
    assert updated.param_set.outputs()["drop"] == pytest.approx(-0.1)
    points, links = updated.place_at(-2, 10)
    assert points[1].code is CustomPointCode.EDGE
    assert (points[1].x, points[1].z) == pytest.approx((-7, 9.9))
    assert links[0].end is points[1]
    with pytest.raises(ValueError, match="read-only"):
        updated.with_params(drop=0)


def test_station_and_context_re_evaluate_through_conditional_and_corridor():
    part = (
        CustomSubassemblyBuilder().with_computed("width", "2 + station / 10")
        .add_point(PointCode.CROWN)
        .add_point(PointCode.LANE_EDGE, "width", "width * grade")
        .add_link(0, 1)
        .build(context=SectionContext(grade=-0.02))
    )
    conditional = ConditionalSubassembly(branches=(
        ConditionalBranch(part, Condition(ConditionType.CUSTOM, 0, context_key="station")),
        ConditionalBranch(custom_lane()),
    ))
    context = SectionContext(station=10, grade=-0.03)
    points, _ = conditional.generate_geometry(context=context)
    assert (points[1].x, points[1].z) == pytest.approx((3, -0.09))

    assembly = AssemblyBuilder().add_right(conditional).build()
    corridor = CorridorBuilder().add_region("Road", 0, 30, assembly).build()
    for station, expected in ((10, 3), (20, 4)):
        points, _ = corridor.cross_section_at(station, context=SectionContext(station=station, grade=-0.04))
        edge = next(point for point in points if point.code is PointCode.LANE_EDGE)
        assert (edge.x, edge.z) == pytest.approx((expected, -0.04 * expected))


def test_shape_boundaries_support_unordered_edges_and_quantity_takeoff():
    lane = (
        CustomSubassemblyBuilder()
        .add_point(PointCode.CROWN)
        .add_point(PointCode.EDGE, "3", "0")
        .add_point(PointCode.PAVEMENT_BOTTOM, "3", "-0.2")
        .add_point(PointCode.PAVEMENT_BOTTOM, "0", "-0.2")
        .add_link(0, 1, LinkCode.PAVEMENT_TOP)
        .add_link(1, 2, LinkCode.PAVEMENT_SIDE)
        .add_link(2, 3, LinkCode.PAVEMENT_BOTTOM)
        .add_link(3, 0, LinkCode.PAVEMENT_SIDE)
        .add_shape("pave", (2, 0, 3, 1), ShapeCode.PAVEMENT)
        .build()
    )
    assert lane.geometry_def.point_count() == 4 and lane.geometry_def.link_count() == 4
    assembly = AssemblyBuilder().add_right(lane).build()
    corridor = CorridorBuilder().add_region("Road", 0, 20, assembly).build()
    result = QuantityTakeoff([Material("Paving", "PAVEMENT")]).compute(corridor, list(corridor.regions))
    assert result.material_quantities[0].total_quantity == pytest.approx(12)


@pytest.mark.parametrize(("links", "indices", "message"), [
    ((LinkDefinition(0, 4),), (), "end_index"),
    ((LinkDefinition(0, 0),), (), "different point"),
    ((LinkDefinition(0, 1), LinkDefinition(1, 2), LinkDefinition(2, 3)), (0, 1, 2), "closed boundary"),
    ((LinkDefinition(0, 1), LinkDefinition(1, 2), LinkDefinition(2, 0)), (0, 1, 3), "link index"),
    ((LinkDefinition(0, 1, shape_code=ShapeCode.CURB), LinkDefinition(1, 2), LinkDefinition(2, 0)),
     (0, 1, 2), "Conflicting"),
])
def test_invalid_geometry_indices_and_shape_topology(links, indices, message):
    shapes = (ShapeDefinition("area", indices, ShapeCode.PAVEMENT),) if indices else ()
    with pytest.raises(ValueError, match=message):
        GeometryDefinition(tuple(PointDefinition(PointCode.EDGE) for _ in range(4)), links, shapes)


def test_allowlisted_formula_errors_report_each_axis_and_build_fails():
    geometry = GeometryDefinition((PointDefinition(PointCode.EDGE, "(1).__class__", "missing / 0"),))
    errors = geometry.validate_expressions({})
    assert len(errors) == 2
    assert errors[0].startswith("Point[0].x: only arithmetic")
    assert errors[1].startswith("Point[0].z: Unknown formula variable")
    for expression in ("1 / 0", "1e309", "10 ** 1000", "(-1) ** 0.5", "abs(1)", "True"):
        with pytest.raises(ValueError, match=r"Point\[0\]\.x"):
            CustomSubassemblyBuilder().add_point(PointCode.EDGE, expression).build()


def test_slope_target_uses_placed_origin_and_keeps_default_without_a_hit():
    slope = custom_slope(side=-1, target_surface="Existing")
    context = SectionContext(
        station=10, base_elevation=10,
        surface_elevation_at=lambda name, offset: 8,
        surface_section_at=lambda name: (((-15, 8), (15, 8)),),
    )
    targets = TargetMapping((TargetReference("Existing", object_name="Ground"),))
    assert slope.target_parameters == ("Existing",)
    points, links = slope.place_at(-3, 1, target_mapping=targets, context=context)
    assert (points[1].x, points[1].z) == pytest.approx((-7.5, -2))
    assert points[1].is_parametric and points[1].apply_aor is False
    assert links[0].end == points[1]
    fallback, _ = slope.place_at(-3, 1, context=context)
    assert (fallback[1].x, fallback[1].z) == pytest.approx((-10.5, -4))


def test_library_is_immutable_and_presets_generate_sections():
    library = CustomSubassemblyLibrary.standard()
    assert library.list_names() == ["CustomLane", "ShoulderCurb", "VDitch", "CustomSlope"]
    lane = custom_lane(width=4)
    updated = library.register(lane)
    assert library.get(lane.name).get_param("width") == 3.5
    assert updated.get(lane.name) == lane
    assert tuple(updated) == tuple(updated.subassemblies.values())
    with pytest.raises(TypeError):
        library.subassemblies["new"] = lane
    ditch = custom_v_ditch(2, 1)
    assert ditch.get_param("slope_length") == pytest.approx(math.sqrt(2))
    points, _ = custom_urban_road(lane_count=1).generate_cross_section()
    assert sorted(p.x for p in points if p.code is PointCode.SIDEWALK_OUT) == pytest.approx([-6.15, 6.15])
