from dataclasses import replace

import pytest

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.codes import LinkCode, PointCode
from myalignment.assembly.conditional.builder import ConditionalSubassemblyBuilder
from myalignment.assembly.parameter.cant_binding import CantBinding
from myalignment.assembly.parameter.superelevation_binding import SuperelevationBinding
from myalignment.assembly.parameterized.builder import ParametricAssemblyBuilder
from myalignment.assembly.parameterized.parametric_lane import ParametricLane
from myalignment.assembly.parameterized.parametric_rail import ParametricRailTrack
from myalignment.cant.curve import CantCriticalStation, CantCurve, CantPivotMethod
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.section.section_view_builder import SectionViewBuilder
from myalignment.superelevation.collection import SuperelevationCollection
from myalignment.superelevation.critical_station import CrossSegmentType as Segment, SuperelevationCriticalStation
from myalignment.superelevation.curve import SuperelevationCurve


def _road_slopes():
    return SuperelevationCollection((SuperelevationCurve(
        start_station=110, end_station=130, critical_stations=(
            SuperelevationCriticalStation(110, slopes={Segment.LEFT_OUT_LANE: -0.02, Segment.RIGHT_OUT_LANE: -0.02}),
            SuperelevationCriticalStation(130, slopes={Segment.LEFT_OUT_LANE: 0.06, Segment.RIGHT_OUT_LANE: -0.06}),
        ),
    ),))


def _cant():
    return CantCurve(start_station=110, end_station=130, critical_stations=(
        CantCriticalStation(110, 0), CantCriticalStation(130, 0.15),
    ))


def _axis():
    return AlignmentBuilder("Axis").with_pi_coords([(0, 0), (40, 0)]).with_start_station(100).build()


def _pavement(links):
    return [link for link in links if link.code is LinkCode.PAVEMENT]


def test_superelevation_interpolates_and_uses_default():
    binding = SuperelevationBinding(_road_slopes(), Segment.LEFT_OUT_LANE, -0.025)
    assert binding.slope_at(120) == pytest.approx(0.02)
    assert binding.slope_at(130) == pytest.approx(0.06)
    assert binding.slope_at(131) == pytest.approx(-0.025)
    missing = replace(binding, segment_type=Segment.LEFT_IN_SHOULDER)
    assert missing.slope_at(120) == pytest.approx(-0.025)


def test_lane_aor_and_station_snapshot_agree_with_geometry():
    binding = SuperelevationBinding(_road_slopes(), Segment.LEFT_OUT_LANE, -0.03)
    lane = ParametricLane.create(width=4, superelevation=binding).with_station(120)
    assert lane.get_param("slope") == -0.03
    inclined = lane.with_params(apply_aor=True).with_station(120)
    assert inclined.get_param("computed_slope_percent") == pytest.approx(2)
    assert inclined.generate_geometry()[0][-1].z == pytest.approx(0.08)
    assert inclined.with_station(140).generate_geometry()[0][-1].z == pytest.approx(-0.12)


def test_corridor_uses_distinct_left_right_road_slopes_and_keeps_shoulder_connected():
    axis = _axis()
    assembly = ParametricAssemblyBuilder().with_superelevation(_road_slopes()).with_lane(4, -0.03).build()
    corridor = (
        CorridorBuilder().add_baseline_from_alignment(axis)
        .add_region("Paving", 100, 140, assembly, frequency=10).build()
    )
    _, links = corridor.cross_section_at(120)
    right, left = _pavement(links)
    assert (right.end.x, left.end.x) == (4, -4)
    assert (right.end.z, left.end.z) == pytest.approx((-0.16, 0.08))
    assert right.end.z == links[1].start.z and left.end.z == links[4].start.z
    assert [p.end.z for p in _pavement(corridor.cross_section_at(100)[1])] == pytest.approx([-0.12, -0.12])
    assert [link.end.elevation for link in SectionViewBuilder.build_data(corridor, axis, 120).links
            if link.code == LinkCode.PAVEMENT.value] == pytest.approx([-0.16, 0.08])


@pytest.mark.parametrize(("pivot", "expected"), [
    (CantPivotMethod.CENTERLINE, (-0.0375, 0.0375)),
    (CantPivotMethod.LEFT_RAIL, (0, 0.075)),
    (CantPivotMethod.RIGHT_RAIL, (-0.075, 0)),
])
def test_cant_interpolation_units_and_pivots(pivot, expected):
    binding = CantBinding((_cant(),), pivot, 1.5, default_cant=-20)
    assert binding.cant_at(120) == pytest.approx(75)
    assert binding.rail_offsets_at(120) == pytest.approx(expected)
    assert binding.cant_at(100) == pytest.approx(-20)
    track = ParametricRailTrack.create(cant=binding).with_station(120)
    rails, _ = track.generate_geometry()
    assert [p.x for p in rails] == [-0.75, 0.75]
    assert [p.z for p in rails] == pytest.approx(expected)


def test_center_track_cant_is_applied_once_and_reversal_keeps_physical_elevation():
    axis = _axis()
    curve = _cant()
    assembly = ParametricAssemblyBuilder().with_cant((curve,), CantPivotMethod.LEFT_RAIL, gauge=1.5).build()
    corridor = (
        CorridorBuilder().add_baseline_from_alignment(axis)
        .add_region_with_assembly("Track", 100, 140, assembly, cant_curve=curve).build()
    )
    before, = _pavement(corridor.cross_section_at(125)[1])
    assert (before.start.z, before.end.z) == pytest.approx((0, 0.1125))
    reversed_axis = replace(axis, corridors=(corridor,)).reversed_alignment()
    after, = _pavement(reversed_axis.primary_corridor.cross_section_at(115)[1])
    assert after.start.code is PointCode.RIGHT_RAIL and after.end.code is PointCode.LEFT_RAIL
    assert after.start.x == -before.start.x and after.end.x == -before.end.x
    assert (after.start.z, after.end.z) == pytest.approx((before.start.z, before.end.z))


def test_nested_road_binding_uses_region_station():
    lane = ParametricLane.create(
        width=4, superelevation=SuperelevationBinding(_road_slopes(), Segment.LEFT_OUT_LANE),
    ).with_params(apply_aor=True)
    branch = ConditionalSubassemblyBuilder().else_(lane).build()
    assembly = AssemblyBuilder().add_conditional("left", branch).build()
    corridor = CorridorBuilder().add_region("Left", 100, 140, assembly).build()
    left, = _pavement(corridor.cross_section_at(125)[1])
    assert (left.end.x, left.end.z) == pytest.approx((-4, 0.16))
