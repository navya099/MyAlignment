import pytest

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly import AssemblyBuilder
from myalignment.assembly.codes import LinkCode, PointCode
from myalignment.assembly.subassemblies import (
    CurbAndGutterSubassembly,
    CurbAndSidewalkSubassembly,
    CurbParams,
    CurbSidewalkFactory,
    CurbSubassembly,
    CurbType,
    SidewalkParams,
    SidewalkSubassembly,
)
from myalignment.assembly.subassemblies.side_slope import SideSlope
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.corridor.feature_line_extractor import CorridorFeatureLineExtractor
from myalignment.corridor.feature_line_spec import CorridorFeatureLineSpec
from myalignment.corridor.surface_builder import CorridorSurfaceSpec
from myalignment.quantity.material import Material
from myalignment.quantity.takeoff import QuantityTakeoff


@pytest.mark.parametrize(("curb_type", "face_offset"), [
    (CurbType.VERTICAL, 0.0),
    (CurbType.SLOPED, 0.1),
    (CurbType.MOUNTABLE, 0.2),
    (CurbType.BARRIER, 0.05),
])
def test_curb_face_presets_and_top_slope(curb_type, face_offset):
    curb = CurbSubassembly.create(curb_type, height=0.18, width=0.3, top_slope=0.1)
    points, links = curb.generate_geometry()
    face = next(p for p in points if p.code is PointCode.CURB_FACE)
    top = next(p for p in points if p.code is PointCode.CURB_TOP)
    assert (face.x, face.z) == pytest.approx((face_offset, 0.18))
    assert (top.x, top.z) == pytest.approx((0.30, 0.18 + (0.30 - face_offset) * 0.1))
    assert all(link.end == next_link.start for link, next_link in zip(links, links[1:] + links[:1]))


def test_custom_face_slope_and_mirroring_use_local_outward_geometry():
    curb = CurbSubassembly.create(CurbType.MOUNTABLE, height=0.2, width=0.3, face_slope=0.25, side=-1)
    local, _ = curb.generate_geometry()
    placed, links = curb.place_at(-3.5, 10)
    assert placed[1].x == pytest.approx(-3.55)
    for a, b in zip(local, placed, strict=True):
        assert (b.x, b.z) == pytest.approx((-3.5 - a.x, 10 + a.z))
    assert all(link.start in placed and link.end in placed for link in links)


@pytest.mark.parametrize("params", [
    {"height": 0},
    {"width": float("nan")},
    {"top_slope": -2},
    {"face_slope": -0.1},
    {"face_slope": 1},
])
def test_invalid_curb_params(params):
    with pytest.raises(ValueError):
        CurbParams(**params)


def test_sidewalk_thickness_and_optional_curb():
    params = SidewalkParams(width=2.5, slope=-0.03, thickness=0.12, include_curb=False)
    manual = SidewalkSubassembly(params=params)
    assembly = CurbAndSidewalkSubassembly(sidewalk_params=params)
    points, links = assembly.generate_geometry()
    assert (points, links) == manual.generate_geometry()
    assert (points[1].x, points[1].z) == pytest.approx((2.5, -0.075))
    assert points[1].z - points[2].z == pytest.approx(0.12)
    assert links[2].code is LinkCode.SUBBASE
    with pytest.raises(ValueError, match="thickness"):
        SidewalkParams(thickness=0)


def test_gutter_places_curb_at_invert_and_attaches_sidewalk_to_curb_back():
    gutter = CurbAndGutterSubassembly.create(gutter_width=0.6, gutter_depth=0.1, curb_width=0.2)
    assembly = AssemblyBuilder().add_right(gutter).add_right(SidewalkSubassembly()).build()
    _, links = assembly.generate_cross_section()
    drain, toe = links[:2]
    assert drain.code is LinkCode.DITCH
    assert drain.end.code is PointCode.DITCH_BOTTOM
    assert (drain.end.x, drain.end.z) == pytest.approx((toe.start.x, toe.start.z))
    sidewalk = next(link for link in links if link.code is LinkCode.PAVEMENT)
    assert (sidewalk.start.x, sidewalk.start.z) == pytest.approx((0.8, -0.1))
    with pytest.raises(ValueError, match="gutter_depth"):
        CurbAndGutterSubassembly(gutter_depth=-0.1)


def test_combined_matches_separate_parts_and_attaches_slope_to_walking_surface():
    def section(builder):
        return builder.add_both(lambda side: SideSlope(side=side)).build().generate_cross_section()

    parts = AssemblyBuilder().add_both(CurbSubassembly).add_both(SidewalkSubassembly)
    combined = AssemblyBuilder().add_both(CurbAndSidewalkSubassembly)
    points, links = section(combined)
    assert section(parts) == (points, links)
    assert sorted(p.x for p in points if p.code is PointCode.SIDEWALK_OUT) == pytest.approx((-2.15, 2.15))
    slopes = [link for link in links if link.code is LinkCode.SLOPE]
    assert len(slopes) == 2
    assert all(link.start.z == pytest.approx(-0.04) for link in slopes)


def test_urban_road_extracts_sections_feature_lines_surface_and_volumes():
    assembly = CurbSidewalkFactory.urban_road(lane_count=2, sidewalk_width=2)
    axis = AlignmentBuilder("Road").with_pi_coords([(0, 0), (20, 0)]).build()
    corridor = (
        CorridorBuilder("Urban")
        .add_baseline_from_alignment(axis)
        .add_region("Urban region", 0, 20, assembly, frequency=5)
        .build()
    )
    section, _ = corridor.cross_section_at(10)
    offsets = [p.x for p in section if p.code is PointCode.SIDEWALK_OUT]
    assert sorted(offsets) == pytest.approx((-9.65, 9.65))
    line = CorridorFeatureLineExtractor.extract(
        corridor, CorridorFeatureLineSpec("Right sidewalk inner", point_code=PointCode.SIDEWALK_IN, side="right"),
        alignments={axis.name: axis},
    )
    assert [p.station for p in line.points] == [0, 5, 10, 15, 20]
    assert abs(line.points[0].point.y) == pytest.approx(7.65)
    assert corridor.build_surface(CorridorSurfaceSpec(), alignments={axis.name: axis}).area_2d > 0

    takeoff = QuantityTakeoff([Material("Curb", "CURB"), Material("Sidewalk", "SIDEWALK")])
    quantities = takeoff.compute(corridor, list(corridor.regions)).material_quantities
    assert [q.total_quantity for q in quantities] == pytest.approx([0.9, 8.0])


def test_drainage_factory_reuses_v_ditch_before_curb():
    assembly = CurbSidewalkFactory.urban_road_with_drainage()
    points, _ = assembly.generate_cross_section()
    bottoms = [p for p in points if p.code is PointCode.DITCH_BOTTOM]
    assert sorted(p.x for p in bottoms) == pytest.approx((-7.25, 7.25))
    assert all(p.z == pytest.approx(-0.44) for p in bottoms)
    for count in (0, True, 1.5):
        with pytest.raises(ValueError, match="lane_count"):
            CurbSidewalkFactory.urban_road(lane_count=count)
