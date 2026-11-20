from dataclasses import replace

import pytest

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.subassemblies.rail_track import SingleTrack
from myalignment.cant.curve import CantCriticalStation, CantCurve, CantPivotMethod
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.export.dxf_writer import DxfWriter
from myalignment.profile.profile import ProfileBuilder
from myalignment.render.primitives import PrimitiveType
from myalignment.render.scene import Scene
from myalignment.render.section_view_renderer import SectionViewRenderer
from myalignment.section.section_view_builder import SectionViewBuilder
from myalignment.section.section_view_composer import SectionViewComposer
from myalignment.section.section_view_data import SectionLink, SectionPoint, SectionViewData
from myalignment.section.section_view_set import SectionViewSet
from myalignment.section.section_view_style import SectionViewStyle
from myalignment.surface.tin_point import TinPoint
from myalignment.surface.tin_surface import TinSurface
from myalignment.surface.triangle import Triangle


def _track():
    profile = ProfileBuilder("Grade").add_tangent(100, 120, 50, 52).build()
    alignment = (
        AlignmentBuilder("Rail").with_pi_coords([(100, 200), (100, 220)])
        .with_start_station(100).with_profile(profile).as_rail_alignment().build()
    )
    cant = CantCurve(start_station=100, end_station=120, pivot_method=CantPivotMethod.LEFT_RAIL,
                     critical_stations=(CantCriticalStation(100, .15),))
    assembly = AssemblyBuilder().add_center(SingleTrack(gauge=1.5)).build()
    corridor = (
        CorridorBuilder().add_baseline("Rail", "Rail", "Grade", 100, 120)
        .add_region_with_assembly("Track", 100, 120, assembly, cant_curve=cant).build()
    )
    return corridor, alignment


def test_section_data_preserves_cant_profile_offsets_and_link_codes():
    corridor, alignment = _track()
    data = SectionViewBuilder.build_data(corridor, alignment, 110, offset_elevation=1)
    rail = next(link for link in data.links if link.code == "Pavement")
    assert (rail.start.offset, rail.end.offset) == pytest.approx((-.75, .75))
    assert (rail.start.elevation, rail.end.elevation) == pytest.approx((52, 52.15))
    assert rail.slope == pytest.approx(10)
    original = SectionViewSet()
    view_set = original.add(data)
    assert not len(original) and tuple(view_set) == (data,)
    assert view_set.get_by_station(110.0001) is data
    assert view_set.stations() == [110]


def test_section_renderer_applies_exaggeration_to_geometry_and_honors_labels():
    start, end = SectionPoint(-5, 5), SectionPoint(5, 7)
    data = SectionViewData(10, (start, end), (SectionLink(start, end, slope=20),))
    style = SectionViewStyle(show_offset_labels=False, show_elevation_labels=False, show_slope_labels=True)
    flat = SectionViewRenderer.render(Scene(), data, style)
    exaggerated = SectionViewRenderer.render(Scene(), data, replace(style, vertical_exaggeration=3))

    def visible_slope_ratio(scene):
        design_line = next(p for p in scene.primitives
                           if p.type is PrimitiveType.LINE and p.style.lineweight == style.section_lineweight
                           and abs(p.points[1].x - p.points[0].x) > 2)
        a, b = design_line.points
        return (b.y - a.y) / (b.x - a.x)

    assert visible_slope_ratio(flat) == pytest.approx(.2)
    assert visible_slope_ratio(exaggerated) == pytest.approx(.6)
    labels = [p.text for p in exaggerated.primitives if p.type is PrimitiveType.TEXT]
    assert labels == ["+20.0%", "Section View — STA 10.00", "Offset (m)", "Elevation (m)"]


def test_surface_overlay_does_not_bridge_tin_gaps():
    corridor, alignment = _track()
    # 두 면이 STA 110에서 각각 좌측과 우측에만 걸친다.
    surface = TinSurface(points=tuple(TinPoint(*p) for p in (
        (90, 208, 49), (90, 212, 49), (95, 210, 50),
        (105, 210, 53), (110, 208, 54), (110, 212, 54),
    )), triangles=(Triangle(0, 1, 2), Triangle(3, 4, 5)))
    style = SectionViewStyle()
    scene = SectionViewComposer.with_surface(corridor, alignment, 110, surface, style)
    terrain = [p for p in scene.primitives if p.style.color == style.surface_color]
    assert len(terrain) == 2
    assert terrain[0].points[-1].x < terrain[1].points[0].x
    assert all(p.type is PrimitiveType.LINE for p in terrain)


def test_grid_layout_skips_missing_sections_and_exports_dxf(tmp_path):
    corridor, alignment = _track()
    style = SectionViewStyle()
    scene = SectionViewBuilder.grid_layout(corridor, alignment, [100, 90, 110, 120], style, columns=2)
    titles = [p for p in scene.primitives if p.text.startswith("Section View")]
    assert scene.metadata["section_stations"] == (100, 110, 120)
    assert {layer.name for layer in scene.layers} == {"C-SECTION-VIEW", "C-SECTION-LABEL"}
    assert titles[1].points[0].x - titles[0].points[0].x == style.width + 20
    assert titles[2].points[0].y - titles[0].points[0].y == -(style.height + 20)
    path = tmp_path / "sections.dxf"
    DxfWriter(scene).write(path)
    assert "STA 120.00" in path.read_text("cp949")
