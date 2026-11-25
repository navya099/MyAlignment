import json
from pathlib import Path
import re

import pytest

from myalignment.assembly.codes import LinkCode
from myalignment.corridor.link_surface_manager import LinkSurfaceManager
from myalignment.corridor.multi_link_surface_builder import LinkSurfaceResult
from myalignment.export.link_surface_3d_export import LinkSurface3DExport
from myalignment.export.scene_3d_serializer import Scene3DSerializer
from myalignment.render.link_surface_3d_renderer import LinkSurface3DPreview, LinkSurface3DRenderer
from myalignment.render.link_surface_3d_scene import LinkSurface3DScene
from myalignment.render.primitives_3d import Point3D, Primitive3D, PrimitiveType3D
from myalignment.render.scene_3d import Scene3D
from myalignment.surface.tin_point import TinPoint
from myalignment.surface.tin_surface import TinSurface
from myalignment.surface.triangle import Triangle


def _surface(name, z):
    return TinSurface(
        name,
        tuple(TinPoint(x, y, z) for x, y in ((0, 0), (4, 0), (4, 3), (0, 3))),
        (Triangle(0, 1, 2), Triangle(0, 2, 3)),
    )


@pytest.fixture
def manager():
    return LinkSurfaceManager((
        LinkSurfaceResult(_surface("Paving", 10), LinkCode.PAVEMENT_TOP),
        LinkSurfaceResult(_surface("Shoulder </script>", 8), LinkCode.SHOULDER, color=30),
        LinkSurfaceResult(_surface("Combined", 6)),
        LinkSurfaceResult(_surface("Second paving", 9), LinkCode.PAVEMENT_TOP, color=2),
    ))


def test_combined_mesh_wire_and_legend_keep_layers_and_colors(manager):
    mark = Primitive3D.point(Point3D(20, 20, 20))
    existing = Scene3D((mark,), {"source": "Road"})
    scene = LinkSurface3DRenderer.render_3d(existing, manager, show_wireframe=True, z_scale=2, opacity=0.4)
    assert scene.primitives[0] is mark
    assert existing.primitives == (mark,)
    assert scene.metadata["source"] == "Road"
    meshes = [item for item in scene.primitives if item.type is PrimitiveType3D.MESH]
    assert [item.style.color for item in meshes] == [1, 30, 7, 2]
    assert [item.style.layer for item in meshes] == [
        "C-CORRIDOR-PAVEMENT_TOP", "C-CORRIDOR-SHOULDER", "C-CORRIDOR-COMBINED", "C-CORRIDOR-PAVEMENT_TOP-2",
    ]
    assert [item.points[0].z for item in meshes] == [20, 16, 12, 18]
    assert all(item.style.opacity == 0.4 for item in meshes)
    wire = [item for item in scene.primitives if item.style.layer == "C-CORRIDOR-PAVEMENT_TOP-WIRE"]
    assert len(wire) == 5  # The two triangles share one edge.
    assert all(item.style.color == 1 and item.style.opacity == 1 for item in wire)
    assert scene.metadata["link_surfaces"]["C-CORRIDOR-SHOULDER"] == {
        "name": "Shoulder </script>", "area_2d": 12, "code": "Shoulder",
    }


def test_z_offset_and_individual_scene_selection(manager):
    scene = LinkSurface3DRenderer.render_combined_flat(manager, z_offset_per_link=5, z_scale=2)
    assert [item.points[0].z for item in scene.primitives] == [20, 21, 22, 33]
    by_code = LinkSurface3DScene.from_manager(manager, z_scale=2)
    assert by_code.available_codes() == [LinkCode.PAVEMENT_TOP, LinkCode.SHOULDER]
    assert len(by_code.get_scene(LinkCode.PAVEMENT_TOP).primitives) == 2
    assert len(by_code.merge_all().primitives) == 3
    selected = by_code.merge_selected([LinkCode.DATUM, LinkCode.SHOULDER, LinkCode.SHOULDER])
    assert len(selected.primitives) == 1
    assert selected.primitives[0].points[0].z == 16
    assert set(selected.metadata["link_surfaces"]) == {"C-CORRIDOR-SHOULDER"}


def test_export_combined_and_per_code_dxf_and_html(manager, tmp_path):
    outputs = LinkSurface3DExport.export_all(manager, tmp_path / "out")
    assert set(outputs) == {"dxf_combined", "html_combined", "dxf_pavement_top", "dxf_shoulder"}

    html = Path(outputs["html_combined"]).read_text(encoding="utf-8")
    match = re.search(r'id="scene-data">(.*?)</script>', html)
    assert match and r"\u003c/script>" in match[1]
    data = json.loads(match[1])
    assert len(data["primitives"]) == 24
    shoulder = next(p for p in data["primitives"] if p["layer"] == "C-CORRIDOR-SHOULDER" and p["type"] == "mesh")
    assert shoulder["color"] == "#FF7F00"
    assert shoulder["opacity"] == pytest.approx(0.8)
    assert data["metadata"]["link_surfaces"]["C-CORRIDOR-SHOULDER"]["name"] == "Shoulder </script>"

    dxf = Path(outputs["dxf_shoulder"]).read_text(encoding="cp949")
    assert "0\n3DFACE\n8\nC-CORRIDOR-SHOULDER\n62\n30\n" in dxf
    assert "C-CORRIDOR-PAVEMENT_TOP" not in dxf

    flat_path = tmp_path / "flat.html"
    flat = LinkSurface3DPreview.preview_flat(manager, flat_path, three_module_base="./vendor")
    assert flat_path.is_file()
    assert "./vendor/build/three.module.js" in flat_path.read_text(encoding="utf-8")
    assert Scene3DSerializer.to_dict(flat)["primitives"][1]["vertices"][0][2] == 13


@pytest.mark.parametrize("options", [{"z_scale": 0}, {"opacity": 1.1}, {"z_offset_per_link": float("nan")}])
def test_invalid_3d_display_options(manager, options):
    with pytest.raises(ValueError):
        LinkSurface3DRenderer.render_3d(Scene3D(), manager, **options)
