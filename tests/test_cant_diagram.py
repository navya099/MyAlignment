import pytest

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.cant.curve import CantCriticalStation, CantCurve
from myalignment.export.dxf_writer import DxfWriter
from myalignment.profile.profile import ProfileBuilder
from myalignment.profile.view_style import ProfileViewStyle
from myalignment.render.cant_diagram_composer import CantDiagramComposer
from myalignment.render.cant_diagram_renderer import CantDiagramRenderer
from myalignment.render.cant_diagram_style import CantDiagramStyle
from myalignment.render.primitives import PrimitiveType
from myalignment.render.scene import Scene


def _rail():
    cant = CantCurve(start_station=100, end_station=200, critical_stations=(
        CantCriticalStation(100, 0), CantCriticalStation(125, -.12),
        CantCriticalStation(175, -.12), CantCriticalStation(200, 0),
    ))
    return (
        AlignmentBuilder("철도").with_pi_coords([(0, 0), (100, 0)]).with_start_station(100)
        .as_rail_alignment(gauge=1.5, cant_curves=[cant]).build()
    )


def test_diagram_renders_millimetres_and_critical_stations():
    style = CantDiagramStyle(grid_x_interval=25, cant_lineweight=0.7)
    scene = CantDiagramComposer.separate(_rail(), style)
    labels = [p.text for p in scene.primitives if p.type is PrimitiveType.TEXT]
    assert {"TI", "FC", "TO", "Cant (mm)", "120 mm", "Cant Diagram — 철도"} <= set(labels)
    lines = [p for p in scene.primitives if p.type is PrimitiveType.LINE
             and p.style.lineweight == style.cant_lineweight]
    assert [p.style.color for p in lines] == [3, 1, 3]
    assert lines[0].points[0].y == 60
    assert lines[0].points[1].y == pytest.approx(style.cant_to_y(120, 132))
    assert lines[0].points[1] == lines[1].points[0]
    assert sum(p.style.linetype == "DASHED" for p in scene.primitives) == 2


def test_percentage_uses_track_gauge_and_dxf_exports_combined_layers(tmp_path):
    style = CantDiagramStyle(unit="%")
    rail = _rail()
    diagram = CantDiagramComposer.separate(rail, style)
    assert "8.00%" in [p.text for p in diagram.primitives]
    profile = ProfileBuilder().add_tangent(100, 200, -150, -140).build()
    scene = CantDiagramComposer.below_profile_view(
        rail, [profile], ProfileViewStyle(vertical_exaggeration=2), style,
    )
    profile_points = [pt for p in scene.primitives if p.style.layer != style.layer for pt in p.points]
    diagram_points = [pt for p in scene.primitives if p.style.layer == style.layer for pt in p.points]
    assert max(pt.y for pt in diagram_points) < min(pt.y for pt in profile_points)
    assert {layer.name for layer in scene.layers} >= {"C-PROF-GRID", "C-PROF-EG", style.layer}

    path = tmp_path / "cant-diagram.dxf"
    DxfWriter(scene).write(path)
    data = path.read_text("cp949").splitlines()
    assert "8.00%" in data and "C-CANT-DIAGRAM" in data


def test_empty_diagram_keeps_scene_and_rejects_invalid_plot_settings():
    ordinary = AlignmentBuilder().with_pi_coords([(0, 0), (10, 0)]).build()
    scene = Scene(metadata={"project": "A"})
    assert CantDiagramRenderer.render(scene, ordinary) is scene
    with pytest.raises(ValueError, match="positive"):
        CantDiagramStyle(grid_x_interval=0)
    with pytest.raises(ValueError, match="Margins"):
        CantDiagramStyle(width=100)
