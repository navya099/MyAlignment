import math

from cadgeom import Point2d

from myalignment.alignment.alignment import Alignment
from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.alignment.style.alignment_style import AlignmentStyle
from myalignment.alignment.style.display_rule import AlignmentComponent, DisplayRule, ViewType
from myalignment.corridor.corridor import Corridor
from myalignment.enitity.arc_entity import ArcEntity
from myalignment.enitity.entity_collection import AlignmentEntityCollection
from myalignment.enitity.spiral_entity import SpiralEntity
from myalignment.enum.spiraltype import SpiralType
from myalignment.export.dxf_writer import DxfWriter
from myalignment.profile.profile import ProfileBuilder
from myalignment.profile.profiletype import ProfileType
from myalignment.render.alignment_renderer import AlignmentRenderer
from myalignment.render.composer import RenderOptions, SceneComposer
from myalignment.render.primitives import Primitive, PrimitiveType, Style
from myalignment.render.scene import Layer, Scene
from myalignment.render.viewport import Viewport, ViewportType
from myalignment.surface.boundary import Boundary
from myalignment.surface.boundary_set import BoundarySet
from myalignment.surface.tin_surface import TinSurface
from myalignment.utils import CurveDirection


def test_plan_respects_view_visibility_and_arrow_style():
    styles = AlignmentStyle.basic().with_rule(
        DisplayRule(AlignmentComponent.LINE, ViewType.PLAN, visible=False)
    ).with_rule(DisplayRule(AlignmentComponent.ARROW, ViewType.PLAN, color=3, linetype="DASHED", lineweight=0.35))
    alignment = (
        AlignmentBuilder("Main").with_pi_coords([(10, 20), (10, 100)]).with_style(styles).build()
    )
    incoming = Scene(metadata={"project": "Rail"})
    rendered = AlignmentRenderer.render_plan(alignment, incoming)
    arrow, = rendered.primitives
    assert arrow.points[0] == Point2d(10, 20)
    assert arrow.closed
    assert arrow.style == Style(3, "DASHED", 0.35, "C-ALIGN-ARROW")
    assert rendered.metadata == {"project": "Rail", "alignment_name": "Main", "start_station": 0, "end_station": 80}
    assert not incoming.primitives


def test_plan_samples_curves_and_spirals_to_their_world_endpoints():
    spiral = SpiralEntity.create(
        start_coord=Point2d(100, 200), start_azimuth=0.5, start_station=25,
        radius=200, length=20, spiral_type=SpiralType.Clothoid,
        direction=CurveDirection.LEFT,
    )
    arc = ArcEntity.create(
        start_coord=spiral.end_coord, start_azimuth=spiral.end_azimuth,
        start_station=spiral.end_station, radius=200, delta=0.3,
        direction=CurveDirection.LEFT,
    )
    alignment = Alignment(entities=AlignmentEntityCollection((spiral, arc)))
    rendered = AlignmentRenderer.render_plan(alignment, sample_step=2)
    for primitive, entity in zip(rendered.primitives[:2], (spiral, arc)):
        assert primitive.type is PrimitiveType.POLYLINE
        assert not primitive.closed
        assert primitive.points[0] == entity.start_coord
        assert primitive.points[-1] == entity.end_coord
        assert len(primitive.points) == math.ceil(entity.length / 2) + 1


def test_composer_accumulates_multiple_alignments_profiles_and_surfaces():
    profile = ProfileBuilder("Grade", ProfileType.FG).add_tangent(0, 12, 3, 7).build()
    surface = TinSurface.from_points(
        [(0, 0, 1), (10, 0, 2), (10, 10, 3), (0, 10, 4)],
        boundaries=BoundarySet((Boundary.rectangle(0, 0, 10, 10),)),
    )
    a = (
        AlignmentBuilder("A").with_pi_coords([(0, 0), (12, 0)])
        .with_profile(profile).with_corridor(Corridor().with_surface(surface)).build()
    )
    b = AlignmentBuilder("B").with_pi_coords([(0, 2), (12, 2)]).build()

    scene = SceneComposer.compose_multiple([a, b], RenderOptions(vertical_exaggeration=2))
    assert scene.metadata["alignment_names"] == ("A", "B")
    assert sum(p.type is PrimitiveType.LINE for p in scene.primitives) == 2
    assert len({layer.name for layer in scene.layers}) == len(scene.layers)
    profile_primitive = next(p for p in scene.primitives if p.style.layer == "C-PROF-FG")
    assert profile_primitive.points[0] == Point2d(0, 6)
    assert profile_primitive.points[-1] == Point2d(12, 14)
    assert sum(p.style.layer == "C-TIN-TRI" for p in scene.primitives) == 2
    assert sum(p.style.layer == "C-TIN-BND" and p.closed for p in scene.primitives) == 1
    assert len(SceneComposer.compose_alignment(a, RenderOptions(False, False, False))) == 0
    assert Viewport(ViewportType.SECTION, 2, 10, 20).project(-3, 4) == Point2d(7, 28)


def test_dxf_r12_exports_entities_layer_visibility_linetype_and_unicode(tmp_path):
    p1, p2, p3 = Point2d(0, 0), Point2d(4, 0), Point2d(4, 3)
    style = Style(color=1, linetype="DASHED", layer="Geometry")
    label = Primitive.text(p2, "본선", height=2, rotation=math.pi / 2)
    scene = Scene(layers=(Layer("Geometry", color=3, visible=False),)).add_all((
        Primitive.line(p1, p2, style),
        Primitive.polyline((p1, p2, p3), closed=True, style=style),
        Primitive.arc(p1, 4, 10, 80),
        Primitive.circle(p2, 3),
        label,
    ))
    path = tmp_path / "alignment.dxf"
    DxfWriter(scene).write(path)
    data = path.read_text("cp949").splitlines()
    tags = list(zip(data[::2], data[1::2]))
    assert label.text == "본선"
    assert ("1", "AC1009") in tags
    assert ("62", "-3") in tags
    assert ("6", "DASHED") in tags
    assert [value for code, value in tags if code == "0" and value in {
        "LINE", "POLYLINE", "VERTEX", "SEQEND", "ARC", "CIRCLE", "TEXT",
    }] == ["LINE", "POLYLINE", "VERTEX", "VERTEX", "VERTEX", "SEQEND", "ARC", "CIRCLE", "TEXT"]
    assert ("1", "본선") in tags
    assert ("3", "ANSI_949") in tags
    assert ("50", "90.0") in tags
    assert tags[-1] == ("0", "EOF")
