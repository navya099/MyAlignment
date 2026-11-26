from dataclasses import replace
import math
from xml.etree import ElementTree as ET

import pytest
from shapely.geometry import Point, Polygon

from myalignment.export.dxf_writer import DxfWriter
from myalignment.export.svg_writer import SvgWriter
from myalignment.profile.hatch_generator import ProfileHatchGenerator
from myalignment.profile.hatch_pattern import HatchPattern
from myalignment.profile.hatch_style import ProfileHatchStyle
from myalignment.profile.profile import Profile, ProfileBuilder
from myalignment.profile.profile_symmetric_parabola import ProfileSymmetricParabola
from myalignment.profile.profileentitycollection import ProfileEntityCollection
from myalignment.profile.view_split_config import ProfileViewSplitConfig
from myalignment.profile.view_split_method import ProfileViewSplitMethod
from myalignment.profile.view_style import ProfileViewStyle
from myalignment.render.primitives import PrimitiveType
from myalignment.render.profile_hatch_renderer import ProfileHatchRenderer
from myalignment.render.profile_view_renderer import ProfileViewRenderer
from myalignment.render.profile_view_split_composer import ProfileViewSplitComposer
from myalignment.render.scene import Scene


def _tangent(name, start, end, z0, z1):
    return ProfileBuilder(name).add_tangent(start, end, z0, z1).build()


def test_cut_fill_crossing_contributes_to_both_areas_and_estimated_volumes():
    fg = _tangent("FG", 1_000_000, 1_000_100, 100, 110)
    eg = _tangent("EG", 1_000_000, 1_000_100, 104, 104)
    hatches = ProfileHatchGenerator.generate(fg, eg, sample_step=100, road_width=7)
    cut, fill = hatches.regions
    assert cut.area_type == "cut" and fill.area_type == "fill"
    assert cut.end_station == fill.start_station == pytest.approx(1_000_040)
    assert cut.top_points[-1] == cut.bottom_points[-1] == fill.top_points[0] == fill.bottom_points[0]
    assert hatches.total_area("cut") == pytest.approx(80)
    assert hatches.total_area("fill") == pytest.approx(180)
    assert hatches.net_area == pytest.approx(-100)
    assert hatches.cut_volume_estimate == pytest.approx(560)
    assert hatches.fill_volume_estimate == pytest.approx(1260)


def test_curve_finds_two_crossings_with_large_sample_step():
    curve = ProfileSymmetricParabola.create(
        pvi_station=50, pvi_elevation=15, grade_in=0.2, grade_out=-0.2, curve_length=100,
    )
    fg = Profile("FG", entities=ProfileEntityCollection((curve,)))
    eg = _tangent("EG", 0, 100, 8, 8)
    regions = ProfileHatchGenerator.generate(fg, eg, sample_step=1000).regions
    assert [region.area_type for region in regions] == ["cut", "fill", "cut"]
    x = 50 - math.sqrt(1000)
    assert regions[0].end_station == pytest.approx(x)
    assert regions[1].end_station == pytest.approx(100 - x)


def test_generator_intersects_profile_ranges_and_splits_at_equal_span():
    fg = ProfileBuilder("FG").add_tangent(0, 20, 1, 0).add_tangent(20, 30, 0, 0).add_tangent(30, 60, 0, 3).build()
    eg = _tangent("EG", 5, 50, 0, 0)
    result = ProfileHatchGenerator.generate(fg, eg, station_range=(10, 47))
    assert [(r.start_station, r.end_station) for r in result.fill_regions()] == [(10, 20), (30, 47)]
    assert not len(ProfileHatchGenerator.generate(fg, eg, station_range=(70, 90)))


@pytest.mark.parametrize(("pattern", "primitive_kind"), [
    (HatchPattern.SOLID, PrimitiveType.POLYGON), (HatchPattern.DIAGONAL, PrimitiveType.LINE),
    (HatchPattern.CROSS, PrimitiveType.LINE), (HatchPattern.HORIZONTAL, PrimitiveType.LINE),
    (HatchPattern.VERTICAL, PrimitiveType.LINE), (HatchPattern.DOTS, PrimitiveType.CIRCLE),
])
def test_patterns_are_clipped_and_use_projected_height(pattern, primitive_kind):
    fg = ProfileBuilder("FG").add_tangent(0, 10, 1, 5).add_tangent(10, 20, 5, 1).build()
    eg = _tangent("EG", 0, 20, 0, 0)
    appearance = ProfileHatchStyle(fill_pattern=pattern, fill_spacing=1, show_net=True, net_color=6)
    hatches = ProfileHatchGenerator.generate(fg, eg)
    view = ProfileViewStyle(vertical_exaggeration=2)
    scene = ProfileHatchRenderer.render(Scene(), hatches, view, style=appearance, station_range=(2, 18))
    boundary, = [p for p in scene.primitives if p.style.layer == appearance.boundary_layer]
    polygon = Polygon([(p.x, p.y) for p in boundary.points])
    assert polygon.bounds == pytest.approx((2, 0, 18, 10))
    drawn = [p for p in scene.primitives if p.style.layer == appearance.fill_layer]
    assert drawn and all(p.type is primitive_kind and p.style.color == 6 for p in drawn)
    for primitive in drawn:
        assert all(polygon.buffer(1e-8).covers(Point(p.x, p.y)) for p in primitive.points)
        if primitive.type is PrimitiveType.LINE:
            a, b = primitive.points
            assert polygon.buffer(1e-8).covers(Point((a.x + b.x) / 2, (a.y + b.y) / 2))


def test_profile_views_and_real_solid_exports(tmp_path):
    fg = _tangent("Design", 0, 100, 0, 10)
    eg = _tangent("Existing", 0, 100, 5, 5)
    appearance = ProfileHatchStyle(cut_pattern=HatchPattern.SOLID, fill_pattern=HatchPattern.SOLID)
    view = ProfileViewStyle(vertical_exaggeration=3)
    scene = ProfileViewRenderer.render([fg, eg], "Road", view, render_labels=False, hatch_style=appearance,
                                       fg_profile_name="Design", eg_profile_name="Existing", station_range=(20, 80))
    fills = [p for p in scene.primitives if p.type is PrimitiveType.POLYGON]
    assert len(fills) == 2
    assert [(min(pt.x for pt in p.points), max(pt.x for pt in p.points)) for p in fills] == [(20, 50), (50, 80)]
    line_index = next(i for i, p in enumerate(scene.primitives) if p.style.layer == "C-PROF-EG")
    assert all(scene.primitives.index(p) < line_index for p in fills)

    svg = ET.fromstring(SvgWriter(scene).to_string())
    nodes = [p for p in svg.iter("{http://www.w3.org/2000/svg}polygon") if p.get("opacity") == "0.3"]
    assert {p.get("fill") for p in nodes} == {"#FF0000", "#0000FF"}
    dxf = tmp_path / "profile.dxf"
    DxfWriter(scene).write(dxf)
    assert dxf.read_text("cp949").splitlines().count("SOLID") >= 2

    split = ProfileViewSplitConfig(method=ProfileViewSplitMethod.MANUAL, manual_split_stations=(60,),
                                   overlap_station=0, columns=2)
    sheets = ProfileViewSplitComposer.compose([fg, eg], "Road", view, split, hatch_style=appearance,
                                              fg_profile_name="Design", eg_profile_name="Existing")
    fills = [p for p in sheets.primitives if p.type is PrimitiveType.POLYGON]
    assert len(fills) == 3
    first, second = sheets.metadata["panels"]
    assert max(p.x for p in fills[1].points) - first["translation"][0] == pytest.approx(60)
    assert min(p.x for p in fills[2].points) - second["translation"][0] == pytest.approx(60)


def test_hidden_fill_and_invalid_style():
    style = ProfileHatchStyle(show_fill=False)
    result = ProfileHatchGenerator.generate(_tangent("FG", 0, 10, 4, 4), _tangent("EG", 0, 10, 1, 1))
    assert result.total_area("fill") == 30
    assert not ProfileHatchRenderer.render(Scene(), result, ProfileViewStyle(), style=style).primitives
    with pytest.raises(ValueError, match="spacing"):
        replace(style, fill_spacing=0)
