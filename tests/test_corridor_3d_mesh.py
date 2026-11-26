import json
import re

import pytest
from shapely.geometry import Polygon

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.assembly.subassemblies.rail_track import SingleTrack
from myalignment.cant.curve import CantCriticalStation, CantCurve, CantPivotMethod
from myalignment.corridor.corridor_3d_renderer import Corridor3DRenderer
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.corridor.mesh_mode import MeshMode
from myalignment.export.json_3d_exporter import Json3DExporter
from myalignment.profile.profile import ProfileBuilder
from myalignment.render.corridor_3d_mesh_renderer import Corridor3DMeshPreview, Corridor3DMeshRenderer


def _road():
    axis = (
        AlignmentBuilder("Road").with_pi_coords([(500000, 400000), (500000, 400060)])
        .with_start_station(100).build()
    )
    assembly = AssemblyBuilder().add_right(BasicLane(width=4, slope=-0.025)).build()
    corridor = (
        CorridorBuilder("Road").add_baseline_from_alignment(axis)
        .add_region("First", 100, 120, assembly, frequency=11)
        .add_region("Second", 130, 150, assembly, frequency=13).build()
    )
    return axis, corridor


def _payload(path):
    html = path.read_text(encoding="utf-8")
    return html, json.loads(re.search(r'id="scene-data">([^<]+)</script>', html).group(1))


def test_link_mode_preserves_codes_even_for_links_of_same_color():
    axis, corridor = _road()
    link = corridor.build_3d_mesh(axis, sample_frequency=7, z_offset=1)
    layers = link.metadata["mesh_layers"]
    assert link.metadata["mesh_mode"] == MeshMode.LINK_BASED.value
    assert layers["C-CORRIDOR-MESH-LANE"] == "Lane"
    assert layers["C-CORRIDOR-MESH-PAVEMENT_TOP"] == "Pavement_Top"
    assert layers["C-CORRIDOR-MESH-PAVEMENT_SIDE"] == "Pavement_Side"
    lane, _ = [p for p in link.primitives if p.style.layer == "C-CORRIDOR-MESH-LANE"]
    pavement, _ = [p for p in link.primitives if p.style.layer == "C-CORRIDOR-MESH-PAVEMENT_TOP"]
    assert lane.points == pavement.points
    assert sorted({p.y for p in pavement.points}) == [400000, 400007, 400014, 400020]
    assert {p.z for p in pavement.points} == {1, 0.9}
    assert len(pavement.indices) == 6 and len(pavement.points) == 8


def test_quad_strip_reuses_vertices_and_matches_link_mesh_faces():
    axis, corridor = _road()
    quad = corridor.build_3d_mesh(axis, MeshMode.QUAD_STRIP)
    link = corridor.build_3d_mesh(axis, MeshMode.LINK_BASED)
    legacy = Corridor3DRenderer.render_mesh(corridor, axis)

    def faces(scene):
        return sorted(
            (p.points[a].y, p.points[b].y, p.points[c].y)
            for p in scene.primitives for a, b, c in p.indices
        )

    assert len(quad.primitives) == 2
    assert all(p.style.layer == "C-CORRIDOR-MESH-QUAD" for p in quad.primitives)
    assert faces(quad) == faces(link) == faces(legacy)
    assert [len(p.points) for p in quad.primitives] == [12, 12]
    assert [sorted({p.y for p in mesh.points}) for mesh in quad.primitives] == [
        [400000, 400011, 400020], [400030, 400043, 400050],
    ]


def test_tin_uses_highest_sample_at_xy_and_preserves_region_gaps():
    axis, corridor = _road()
    grade = ProfileBuilder("Explicit").add_tangent(100, 160, 20, 26).build()
    scene = corridor.build_3d_mesh(axis, MeshMode.TRIANGULATED, 7, z_offset=2, profile=grade)
    assert len(scene.primitives) == 2
    for mesh, (lo, hi) in zip(scene.primitives, [(400000, 400020), (400030, 400050)], strict=True):
        assert mesh.style.layer == "C-CORRIDOR-MESH-TIN"
        assert mesh.indices and all(lo <= p.y <= hi for p in mesh.points)
        assert len({(p.x, p.y) for p in mesh.points}) == len(mesh.points)
        for point in mesh.points:
            expected = 22 + (point.y - 400000) * 0.1 - (point.x - 500000) * 0.025
            assert point.z == pytest.approx(expected)


def test_tin_does_not_fill_outside_concave_curved_footprint():
    axis = (
        AlignmentBuilder("Curve").with_pi_coords([(0, 0), (40, 0), (40, 40)])
        .with_radii([None, 15, None]).build()
    )
    assembly = AssemblyBuilder().add_right(BasicLane(width=4)).build()
    corridor = (
        CorridorBuilder().add_baseline_from_alignment(axis)
        .add_region("Bend", 0, axis.end_station, assembly, frequency=5).build()
    )
    mesh, = corridor.build_3d_mesh(axis, MeshMode.TRIANGULATED).primitives
    stations = corridor.regions[0].sample_stations()
    boundary = Polygon(
        [(p.x, p.y) for p in [*(axis.point_at(s, 0) for s in stations),
                              *(axis.point_at(s, 4) for s in reversed(stations))]]
    )
    total_area = 0
    for face in mesh.indices:
        triangle = Polygon([(mesh.points[i].x, mesh.points[i].y) for i in face])
        assert triangle.difference(boundary).area < 1e-8
        total_area += triangle.area
    assert total_area == pytest.approx(boundary.area)


def test_mesh_preserves_cant_and_filters_same_alignment_baselines():
    profile = ProfileBuilder("Grade").add_tangent(100, 120, 50, 52).build()
    axis = (
        AlignmentBuilder("Rail").with_pi_coords([(100, 200), (100, 220)])
        .with_start_station(100).with_profile(profile).as_rail_alignment().build()
    )
    cant = CantCurve(start_station=100, end_station=120, pivot_method=CantPivotMethod.LEFT_RAIL,
                     critical_stations=(CantCriticalStation(100, 0.15),))
    assembly = AssemblyBuilder().add_center(SingleTrack(gauge=1.5)).build()
    corridor = (
        CorridorBuilder().add_baseline_from_alignment(axis, profile, name="Selected")
        .add_baseline_from_alignment(axis, name="Other")
        .add_region_with_assembly("Track", 100, 120, assembly, baseline_name="Selected", cant_curve=cant)
        .add_region("Other track", 100, 120, assembly, baseline_name="Other").build()
    )
    scene = corridor.build_3d_mesh(axis, baseline_name="Selected")
    rail, = [p for p in scene.primitives if p.style.layer == "C-CORRIDOR-MESH-PAVEMENT"]
    section = sorted((p.x, p.z) for p in rail.points if p.y == 200)
    assert [p[0] for p in section] == pytest.approx([99.25, 100.75])
    assert [p[1] for p in section] == pytest.approx([50, 50.15])
    with pytest.raises(ValueError, match="Missing baseline"):
        corridor.build_3d_mesh(axis, baseline_name="Unknown")


def test_preview_embeds_safe_custom_and_layer_legends_and_exports_dxf(tmp_path):
    axis, corridor = _road()
    view, dxf = tmp_path / "mesh.html", tmp_path / "mesh.dxf"
    scene = Corridor3DMeshPreview.preview(corridor, axis, view, dxf, three_module_base="./vendor")
    html, payload = _payload(view)
    assert "./vendor/build/three.module.js" in html
    assert payload["metadata"]["mesh_layers"]["C-CORRIDOR-MESH-PAVEMENT_TOP"] == "Pavement_Top"
    colors = {p["layer"]: p["color"] for p in payload["primitives"]}
    assert colors["C-CORRIDOR-MESH-PAVEMENT_TOP"] == "#FF0000"
    data = dxf.read_text("cp949").splitlines()
    assert data.count("3DFACE") == sum(len(p.indices) for p in scene.primitives)

    value = "</script><script>custom legend</script>"
    Json3DExporter.export_mesh_with_legend(scene, view, title=value, legend=[{"name": value, "color": "#F00"}])
    html, payload = _payload(view)
    assert value not in html
    assert payload["metadata"]["mesh_legend"] == [{"name": value, "color": "#F00"}]


def test_empty_and_invalid_mesh_inputs():
    axis, _ = _road()
    corridor = CorridorBuilder().build()
    for mode in MeshMode:
        assert not corridor.build_3d_mesh(axis, mode).primitives
    with pytest.raises(ValueError, match="mode"):
        Corridor3DMeshRenderer.render_mesh(corridor, axis, "LinkBased")
    with pytest.raises(ValueError, match="sample_frequency"):
        corridor.build_3d_mesh(axis, sample_frequency=0)
