from dataclasses import replace
import math
from pathlib import Path
from xml.etree import ElementTree as ET

from cadgeom import Point2d
import pytest

from myalignment.export.aci_color_map import AciColorMap
from myalignment.export.svg_composer import SvgExportComposer
from myalignment.export.svg_exporter import SvgExporter
from myalignment.export.svg_gallery import SvgGallery
from myalignment.export.svg_style import SvgStyle
from myalignment.export.svg_writer import SvgWriter
from myalignment.render.primitives import Primitive, Style
from myalignment.render.scene import Layer, Scene


_NS = {"s": "http://www.w3.org/2000/svg"}


def _elements(root, kind):
    return root.findall(f".//s:{kind}", _NS)


def test_fixed_page_flips_geometry_and_keeps_text_upright():
    style = SvgStyle(page_width_mm=100, page_height_mm=80, margin_mm=5, auto_fit_viewport=False)
    a, b, c = Point2d(3, 4), Point2d(7, 10), Point2d(9, 5)
    scene = Scene((
        Primitive.line(a, b),
        Primitive.polyline((a, b, c)),
        Primitive.polyline((a, b, c), closed=True),
        Primitive.circle(b, 2),
        Primitive.text(a, '한글 <&> "문자"\n두 번째', 2, rotation=math.pi / 2),
    ))
    root = ET.fromstring(SvgWriter(scene, style).to_string())
    assert (root.attrib["width"], root.attrib["height"], root.attrib["viewBox"]) == ("100mm", "80mm", "0 0 100 80")
    line, = _elements(root, "line")
    assert [line.get(k) for k in ("x1", "y1", "x2", "y2")] == ["8", "71", "12", "65"]
    assert _elements(root, "polyline")[0].get("points") == "8,71 12,65 14,70"
    assert _elements(root, "polygon")[0].get("points") == "8,71 12,65 14,70"
    circle, = _elements(root, "circle")
    assert (circle.get("cx"), circle.get("cy"), circle.get("r")) == ("12", "65", "2")
    text, = _elements(root, "text")
    assert text.get("transform") == "rotate(-90 8 71)"
    assert text.text is None
    assert [node.text for node in text] == ['한글 <&> "문자"', "두 번째"]


def test_arcs_use_degrees_y_flip_and_full_circle_two_arc_commands():
    center = Point2d(20, 25)
    scene = Scene((
        Primitive.arc(center, 10, 0, 90),
        Primitive.arc(center, 10, 90, 0),
        Primitive.arc(center, 10, 10, 370),
        Primitive.arc(center, 10, 10, 10),
    ))
    style = SvgStyle(page_height_mm=100, margin_mm=0, auto_fit_viewport=False)
    data = [p.get("d") for p in _elements(ET.fromstring(SvgWriter(scene, style).to_string()), "path")]
    assert data[0] == "M 30 75 A 10 10 0 0 0 20 65"
    assert data[1] == "M 20 65 A 10 10 0 1 0 30 75"
    assert len(data) == 3 and data[2].count(" A ") == 2


def test_auto_fit_uses_circular_extrema_and_ignores_hidden_layers():
    visible = Style(layer="Ring", lineweight=1.0)
    h = Style(layer="Off")
    scene = Scene((
        Primitive.circle(Point2d(1_000_000, 2_000_000), 20, visible),
        Primitive.line(Point2d(-1_000_000, -2_000_000), Point2d(0, 0), h),
    ), (Layer("Off", visible=False),))
    root = ET.fromstring(SvgWriter(scene).to_string())
    circle = _elements(root, "circle")[0]
    assert [float(circle.get(k)) for k in ("cx", "cy", "r")] == pytest.approx([148.5, 105, 94.5])
    groups = {g.get("data-layer"): g for g in _elements(root, "g")}
    assert groups["Off"].get("display") == "none"

    arc = Primitive.arc(Point2d(0, 0), 10, 45, 135, visible)
    narrow = SvgStyle(page_width_mm=30, page_height_mm=30, margin_mm=5)
    root = ET.fromstring(SvgWriter(Scene((arc,)), narrow).to_string())
    path = _elements(root, "path")[0].get("d").split()
    assert (float(path[1]), float(path[-2])) == pytest.approx((24.5, 5.5))
    assert float(path[4]) > 13


def test_layer_color_linetype_and_presets(tmp_path):
    layer = Layer("Road & A", color=1, linetype="DASHED", lineweight=0.6)
    scene = Scene((
        Primitive.line(Point2d(0, 0), Point2d(3, 0), Style(layer="road & a", linetype="BYLAYER")),
        Primitive.line(Point2d(0, 1), Point2d(3, 1), Style(color=7, layer="Road--A")),
    ), (layer,))
    style = SvgStyle(auto_fit_viewport=False, stroke_width_scale=2)
    root = ET.fromstring(SvgWriter(scene, style).to_string())
    groups = _elements(root, "g")
    assert [g.get("data-layer") for g in groups] == ["Road & A", "Road--A"]
    assert len({g.get("id") for g in groups}) == 2
    inherited, neutral = _elements(root, "line")
    assert (inherited.get("stroke"), inherited.get("stroke-width"), inherited.get("stroke-dasharray")) == (
        "#FF0000", "1.2", "0.5 0.25",
    )
    assert neutral.get("stroke") == "#000000"
    print_path, dark_path, web_path = (tmp_path / f"{preset}.svg" for preset in ("print", "dark", "web"))
    SvgExporter.export_print(scene, print_path)
    SvgExporter.export_dark(scene, dark_path)
    SvgExporter.export_web(scene, web_path)
    assert {_line.get("stroke") for _line in _elements(ET.parse(print_path), "line")} == {"#000000"}
    assert _elements(ET.parse(dark_path), "line")[1].get("stroke") == "#FFFFFF"
    assert ET.parse(web_path).getroot().get("width") == "297mm"
    assert AciColorMap.to_css(250) == "#333333" and AciColorMap.to_css(256, dark_mode=True) == "#FFFFFF"


def test_batch_and_gallery_uses_relative_encoded_paths_and_escaped_titles(tmp_path):
    scenes = {"A": Scene(), "도면 & B": Scene()}
    outputs = SvgExportComposer.export_all(scenes, tmp_path / "svg files", {"도면 & B": SvgStyle.dark()})
    assert {Path(p).name for p in outputs.values()} == {"A.svg", "도면 & B_1a1a2e.svg"}
    html = tmp_path / "preview" / "index.html"
    SvgGallery.create(outputs.items(), html, title="<Gallery>")
    body = html.read_text(encoding="utf-8")
    assert "&lt;Gallery&gt;" in body and "<Gallery>" not in body
    assert "../svg%20files/%EB%8F%84%EB%A9%B4%20%26%20B_1a1a2e.svg" in body
    assert "도면 &amp; B" in body
    with pytest.raises(ValueError, match="Invalid"):
        SvgExportComposer.export_all({"../outside": Scene()}, tmp_path)
    with pytest.raises(ValueError, match="Duplicate"):
        SvgExportComposer.export_all({"A": Scene(), "a": Scene()}, tmp_path)


def test_bad_geometry_and_page_settings_fail_before_writing(tmp_path):
    target = tmp_path / "invalid.svg"
    with pytest.raises(ValueError, match="radius"):
        SvgWriter(Scene((Primitive.circle(Point2d(0, 0), 0),))).write(target)
    with pytest.raises(ValueError, match="invalid XML"):
        SvgWriter(Scene((Primitive.text(Point2d(0, 0), "bad\x01char", 1),))).write(target)
    with pytest.raises(ValueError, match="margin_mm"):
        replace(SvgStyle(), page_width_mm=10)
    assert not target.exists()
