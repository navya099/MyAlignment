import pytest

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.assembly.subassemblies.rail_track import SingleTrack
from myalignment.cant.curve import CantCriticalStation, CantCurve, CantPivotMethod
from myalignment.corridor.corridor_3d_renderer import Corridor3DRenderer
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.corridor.corridor_mesh import CorridorMesh
from myalignment.corridor.cross_section_3d import CrossSection3D
from myalignment.export.dxf_3d_writer import Dxf3DWriter
from myalignment.profile.profile import ProfileBuilder
from myalignment.render.corridor_surface_3d import CorridorSurface3DRenderer
from myalignment.render.primitives_3d import Point3D, Primitive3D, PrimitiveType3D, Style3D
from myalignment.render.scene_3d import Scene3D
from myalignment.render.tin_surface_3d_renderer import TinSurface3DRenderer


def test_3d_sections_use_right_positive_offset_profile_and_region_cant():
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
        .add_region_with_assembly("Track", 100, 120, assembly, frequency=50, cant_curve=cant).build()
    )
    sections = Corridor3DRenderer.render_sections_only(corridor, alignment, 7, 1)
    rail_links = [p for p in sections.primitives if p.style.color == 1]
    assert [p.points[0].y for p in rail_links] == pytest.approx([200, 207, 214, 220])
    left, right = rail_links[1].points
    assert (left.x, right.x) == pytest.approx((99.25, 100.75))
    assert (left.z, right.z) == pytest.approx((51.7, 51.85))
    assert {p.points[0].y for p in Corridor3DRenderer.render_sections_only(corridor, alignment).primitives} == {200, 220}

    wire = Corridor3DRenderer.render_wireframe(corridor, alignment, 7)
    mesh = Corridor3DRenderer.render_mesh(corridor, alignment, 7)
    assert len(wire) > len(sections)
    assert all(p.type is PrimitiveType3D.MESH for p in mesh.primitives)
    pavement = next(p for p in mesh.primitives if p.style.color == 1)
    assert len(pavement.indices) == 6
    assert len(pavement.points) == 8
    with pytest.raises(ValueError, match="sample_frequency"):
        Corridor3DRenderer.render_mesh(corridor, alignment, 0)


def test_mesh_refuses_to_connect_different_section_topology():
    points = (Point3D(), Point3D(0, 1, 0))
    section = CrossSection3D(0, points, ((0, 1),))
    with pytest.raises(ValueError, match="topology"):
        CorridorMesh.from_sections([section, CrossSection3D(5, points)])


def test_corridor_surface_can_extract_or_render_stored_tin():
    alignment = AlignmentBuilder("Road").with_pi_coords([(0, 0), (10, 0)]).build()
    assembly = AssemblyBuilder().add_right(BasicLane()).build()
    corridor = (
        CorridorBuilder("Road").add_baseline("Road", "Road", "", 0, 10)
        .add_region("Lane", 0, 10, assembly).build()
    )
    surface = CorridorSurface3DRenderer.render(corridor, alignments={"Road": alignment})
    mesh, = surface.primitives
    assert mesh.indices and any(p.y < 0 and p.z != 0 for p in mesh.points)
    from myalignment.corridor.surface_builder import CorridorSurfaceSpec
    tin = corridor.build_surface(CorridorSurfaceSpec(), alignments={"Road": alignment})
    stored = CorridorSurface3DRenderer.render(corridor.with_surface(tin))
    assert stored == surface
    wire = TinSurface3DRenderer.render(tin)
    assert len(wire) == len({frozenset(p.points) for p in wire.primitives})


def test_dxf_3d_writes_polyline_flags_layers_z_and_faces(tmp_path):
    a, b, c = Point3D(0, 0, 1), Point3D(1, 0, 2), Point3D(1, 1, 3)
    style = Style3D(color=3, layer="Rail")
    scene = Scene3D((
        Primitive3D.point(a, style), Primitive3D.line(a, b, style),
        Primitive3D.polyline((a, b, c), True, style),
        Primitive3D.triangle(a, b, c, style),
        Primitive3D.mesh((a, b, c), ((0, 1, 2),), style),
        Primitive3D.line(a, c, Style3D(layer="Hidden", visible=False)),
    ))
    path = tmp_path / "rail3d.dxf"
    Dxf3DWriter(scene).write(path)
    data = path.read_text("cp949").splitlines()
    groups = list(zip(data[::2], data[1::2]))
    assert ("1", "AC1009") in groups and ("2", "Rail") in groups
    assert ("2", "Hidden") not in groups and ("8", "Hidden") not in groups
    assert ("70", "9") in groups and groups.count(("70", "32")) == 3
    assert ("31", "2") in groups and groups.count(("33", "3")) == 2
    assert groups.count(("0", "3DFACE")) == 2 and groups.count(("0", "LINE")) == 1
