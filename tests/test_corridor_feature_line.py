from dataclasses import replace

import pytest

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.codes import LinkCode, PointCode
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.assembly.subassemblies.rail_track import SingleTrack
from myalignment.cant.curve import CantCriticalStation, CantCurve, CantPivotMethod
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.corridor.feature_line_extractor import CorridorFeatureLineExtractor
from myalignment.corridor.feature_line_spec import CorridorFeatureLineSpec
from myalignment.corridor.region import CorridorRegion
from myalignment.export.dxf_writer import DxfWriter
from myalignment.profile.profile import ProfileBuilder
from myalignment.render.feature_line_2d_renderer import FeatureLine2DRenderer
from myalignment.render.feature_line_3d_renderer import FeatureLine3DPreview
from myalignment.render.primitives import PrimitiveType
from myalignment.render.primitives_3d import PrimitiveType3D
from myalignment.render.scene import Scene


def _lane(width=3.5):
    return AssemblyBuilder().add_both(lambda side: BasicLane(side=side, width=width)).build()


def _axis(name="Axis", x=100):
    return (AlignmentBuilder(name).with_pi_coords([(x, 200), (x, 240)])
            .with_start_station(500).build())


def test_extraction_uses_world_coordinates_external_grade_and_exact_offset():
    axis = _axis()
    grade = ProfileBuilder("Design").add_tangent(500, 540, 40, 48).build()
    corridor = (CorridorBuilder("Road").add_baseline_from_alignment(axis, grade)
                .add_region("Paving", 500, 515, _lane(), frequency=7).build())
    specs = [
        CorridorFeatureLineSpec("Left", point_code=PointCode.LANE_EDGE, side="left"),
        CorridorFeatureLineSpec("Right", "link_code", link_code=LinkCode.PAVEMENT_TOP, use_start=False,
                                use_end=True, side="right"),
        CorridorFeatureLineSpec("Midpoint", "link_code", link_code=LinkCode.LANE, use_end=True, side="right"),
        CorridorFeatureLineSpec("Offset", "offset", offset=1.25),
        CorridorFeatureLineSpec("Outside", "offset", offset=8),
        CorridorFeatureLineSpec("Center code from link", point_code=PointCode.LANE_EDGE),
    ]
    result = corridor.extract_feature_lines(specs, alignments={axis.name: axis}, profiles={grade.name: grade})
    assert not len(corridor.feature_lines)
    left, right, midpoint, offset, outside, center = result.feature_lines
    assert [p.station for p in offset.points] == [500, 507, 514, 515]
    assert (left.start_point.x, left.start_point.y, left.start_point.z) == pytest.approx((96.5, 200, 39.93))
    assert right.start_point.x == pytest.approx(103.5)
    assert midpoint.start_point.x == pytest.approx(101.75)
    assert offset.start_point.x == pytest.approx(101.25)
    assert offset.start_point.z == pytest.approx(39.975)
    assert center.start_point.x == pytest.approx(100)
    assert not outside.points
    assert offset.point_at_station(505).z == pytest.approx(40.975)
    assert offset.point_at_station(515.0005) == offset.end_point


def test_rail_standard_carries_cant_and_uses_aligned_grade():
    axis = _axis()
    grade = ProfileBuilder("Design").add_tangent(500, 540, 30, 34).build()
    axis = replace(axis, profiles=(grade,))
    assembly = AssemblyBuilder().add_center(SingleTrack(gauge=1.5)).build()
    cant = CantCurve(start_station=500, end_station=540, pivot_method=CantPivotMethod.LEFT_RAIL,
                     critical_stations=(CantCriticalStation(500, 0.15),))
    corridor = (CorridorBuilder().add_baseline_from_alignment(axis, grade)
                .add_region_with_assembly("Track", 500, 540, assembly, cant_curve=cant).build())
    result = corridor.extract_feature_lines(standard="rail", alignments={axis.name: axis}, sample_frequency=8)
    left = result.feature_lines.get("Left_Rail")
    right = result.feature_lines.get("Right_Rail")
    assert left.points[1].station == 508
    assert right.start_point.x - left.start_point.x == pytest.approx(1.5)
    assert right.start_point.z - left.start_point.z == pytest.approx(0.15)
    assert left.end_point.z == 34
    assert result.feature_lines.get("Left_Ballast").start_point.x == pytest.approx(98.75)


def test_region_boundary_merges_only_matching_endpoints_and_preserves_gaps():
    axis = _axis()
    corridor = (CorridorBuilder().add_baseline_from_alignment(axis)
                .add_region("First", 500, 510, _lane())
                .add_region("Second", 510, 520, _lane())
                .add_region("Wider", 520, 530, _lane(4))
                .add_region("After gap", 535, 540, _lane(4)).build())
    spec = CorridorFeatureLineSpec("Right", point_code=PointCode.LANE_EDGE, side="right")
    line = CorridorFeatureLineExtractor.extract(corridor, spec, alignments={axis.name: axis})
    assert [[p.station for p in run] for run in line.segments] == [[500, 510, 520], [520, 530], [535, 540]]
    assert line.point_at_station(533) is None
    with pytest.raises(ValueError, match="multiple feature line positions"):
        line.point_at_station(520)
    assert line.length == pytest.approx(35)


def test_missing_sample_breaks_line_and_multiple_specs_share_sampling(monkeypatch):
    axis = _axis()
    corridor = (CorridorBuilder().add_baseline_from_alignment(axis)
                .add_region("Road", 500, 520, _lane()).build())
    original = CorridorRegion.cross_section_at
    calls = []

    def cross_section(region, station):
        calls.append(station)
        return ((), ()) if station == 510 else original(region, station)

    monkeypatch.setattr(CorridorRegion, "cross_section_at", cross_section)
    result = corridor.extract_feature_lines(alignments={axis.name: axis})
    line = result.feature_lines.get("Right_LaneEdge")
    assert calls == [500, 510, 520]
    assert [[p.station for p in run] for run in line.segments] == [[500], [520]]
    assert line.length == 0 and line.point_at_station(510) is None
    assert len(FeatureLine2DRenderer.render(Scene(), result.feature_lines).primitives) == 8


def test_parallel_baselines_are_distinct_and_exports_preserve_segments(tmp_path):
    a, b = _axis("A"), _axis("B", 125)
    corridor = (CorridorBuilder().add_baseline_from_alignment(a).add_baseline_from_alignment(b)
                .add_region("A", 500, 520, _lane(), baseline_name="A")
                .add_region("B", 500, 520, _lane(), baseline_name="B").build())
    spec = CorridorFeatureLineSpec("Center", "offset", layer="CENTERLINE-FL", color=3)
    alignments = {a.name: a, b.name: b}
    result = corridor.extract_feature_lines([spec], alignments=alignments)
    assert result.feature_lines.total_length == 40
    line = result.feature_lines.get("Center")
    assert [run[0].point.x for run in line.segments] == [100, 125]
    selected = corridor.extract_feature_lines([spec], alignments={"B": b}, baseline_name="B")
    assert selected.feature_lines.total_length == 20
    assert len(selected.feature_lines.get("Center").segments) == 1

    scene = FeatureLine2DRenderer.render(Scene(), result.feature_lines)
    assert sum(primitive.type is PrimitiveType.POLYLINE for primitive in scene.primitives) == 2
    dxf_2d = tmp_path / "plan.dxf"
    DxfWriter(scene).write(dxf_2d)
    assert "CENTERLINE-FL" in dxf_2d.read_text("cp949")
    html, dxf_3d = tmp_path / "preview.html", tmp_path / "view.dxf"
    scene_3d = FeatureLine3DPreview.preview(result.feature_lines, html, dxf_3d, show_points=True)
    assert [p.type for p in scene_3d.primitives].count(PrimitiveType3D.POLYLINE) == 2
    assert [p.type for p in scene_3d.primitives].count(PrimitiveType3D.POINT) == 6
    assert "CENTERLINE-FL" in html.read_text(encoding="utf-8")
    assert "CENTERLINE-FL" in dxf_3d.read_text("cp949")
    assert not len(result.add_region(CorridorRegion("Added")).feature_lines)


def test_feature_line_projection_follows_curved_alignment_and_station_origin():
    axis = (AlignmentBuilder("Curve").with_pi_coords([(0, 0), (50, 0), (50, 80)])
            .with_radii([None, 20, None]).with_start_station(100).build())
    corridor = (CorridorBuilder().add_baseline_from_alignment(axis)
                .add_region("Curve", 140, 150, _lane(), frequency=5).build())
    line = CorridorFeatureLineExtractor.extract(
        corridor, CorridorFeatureLineSpec("Offset", "offset", offset=1), alignments={axis.name: axis},
    )
    for sample in line.points:
        expected = axis.point_at(sample.station, 1)
        assert (sample.point.x, sample.point.y) == pytest.approx((expected.x, expected.y))
    assert line.points[1].point.y > 0


def test_spec_and_unknown_baseline_validation():
    with pytest.raises(ValueError, match="extraction_method"):
        CorridorFeatureLineSpec("Invalid", "unknown")
    with pytest.raises(ValueError, match="use_start or use_end"):
        CorridorFeatureLineSpec("Invalid", "link_code", link_code=LinkCode.LANE, use_start=False, use_end=False)
    with pytest.raises(ValueError, match="offset must be on the requested side"):
        CorridorFeatureLineSpec("Invalid", "offset", offset=2, side="left")
    with pytest.raises(ValueError, match="Missing baseline"):
        CorridorBuilder().build().extract_feature_lines(alignments={}, baseline_name="unknown")
