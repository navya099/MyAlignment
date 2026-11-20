import json
import re

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.corridor.corridor_3d_preview import Corridor3DPreview
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.export.json_3d_exporter import Json3DExporter
from myalignment.export.scene_3d_serializer import Scene3DSerializer
from myalignment.render.primitives_3d import Point3D, Primitive3D, Style3D
from myalignment.render.scene_3d import Scene3D


def _payload(html):
    return json.loads(re.search(r'id="scene-data">([^<]+)</script>', html).group(1))


def test_json_scene_serializes_all_visible_primitive_types(tmp_path):
    a, b, c = Point3D(1, 2, 3), Point3D(4, 5, 6), Point3D(7, 8, 9)
    red = Style3D(color=1, layer="철도")
    scene = Scene3D((
        Primitive3D.point(a), Primitive3D.line(a, b, red),
        Primitive3D.polyline((a, b, c), closed=True), Primitive3D.triangle(a, b, c),
        Primitive3D.mesh((a, b, c), ((0, 1, 2),)),
        Primitive3D.line(a, b, Style3D(visible=False)),
    ), {"name": "철도"})
    payload = Scene3DSerializer.to_dict(scene)
    assert [p["type"] for p in payload["primitives"]] == ["point", "line", "polyline", "mesh", "mesh"]
    assert payload["primitives"][1] == {
        "type": "line", "start": [1, 2, 3], "end": [4, 5, 6], "color": "#FF0000", "layer": "철도",
    }
    assert payload["primitives"][2]["closed"]
    assert payload["primitives"][3]["indices"] == [[0, 1, 2]]
    output = tmp_path / "scene.json"
    Json3DExporter.export(scene, output)
    assert json.loads(output.read_text(encoding="utf-8")) == payload


def test_html_embeds_model_data_and_escapes_markup(tmp_path):
    value = '</script><script>alert(1)</script>'
    scene = Scene3D(metadata={"name": value})
    path = tmp_path / "view.html"
    Json3DExporter.export_to_html(scene, path, title=value)
    html = path.read_text(encoding="utf-8")
    assert value not in html and "&lt;/script&gt;" in html
    assert _payload(html)["metadata"] == {"name": value}
    assert "OrbitControls.js" in html


def test_corridor_preview_builds_each_mode(tmp_path):
    alignment = AlignmentBuilder("Axis").with_pi_coords([(500000, 400000), (500045, 400000)]).build()
    assembly = AssemblyBuilder().add_right(BasicLane()).build()
    corridor = (
        CorridorBuilder("도로").add_baseline("Axis", "Axis", "", 0, 45)
        .add_region("Lane", 0, 45, assembly).build()
    )
    for method, types in (
        (Corridor3DPreview.wireframe, {"line"}), (Corridor3DPreview.mesh, {"mesh"}),
        (Corridor3DPreview.combined, {"line", "mesh"}),
    ):
        path = tmp_path / f"{method.__name__}.html"
        method(corridor, alignment, path, sample_frequency=10, three_module_base="./vendor")
        assert "./vendor/build/three.module.js" in path.read_text(encoding="utf-8")
        assert {p["type"] for p in _payload(path.read_text(encoding="utf-8"))["primitives"]} == types
    path = tmp_path / "surface.html"
    Corridor3DPreview.surface(corridor, path, alignments={"Axis": alignment})
    assert {p["type"] for p in _payload(path.read_text(encoding="utf-8"))["primitives"]} == {"mesh"}
