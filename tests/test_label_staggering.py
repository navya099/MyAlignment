from dataclasses import replace
import math

import pytest
from cadgeom import Point2d

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.export.dxf_writer import DxfWriter
from myalignment.profile.profile import ProfileBuilder
from myalignment.profile.station_label import StationElevationLabel
from myalignment.profile.view_style import ProfileViewStyle
from myalignment.render.alignment_renderer import AlignmentRenderer
from myalignment.render.composer import RenderOptions, SceneComposer
from myalignment.render.label_box import LabelBox
from myalignment.render.primitives import Primitive, PrimitiveType, Style
from myalignment.render.profile_view_renderer import ProfileViewRenderer
from myalignment.render.scene import Scene
from myalignment.render.stagger_config import StaggerConfig
from myalignment.render.stagger_direction import StaggerDirection, StaggerMethod
from myalignment.render.stagger_presets import StaggerConfigPresets
from myalignment.render.staggered_renderer import StaggeredRenderer
from myalignment.render.staggerer import Staggerer


def test_rotated_box_respects_insertion_point_and_spacing():
    vertical = LabelBox.from_text(5, 7, "AB", 2, rotation=math.pi / 2)
    assert (vertical.x_min, vertical.y_min, vertical.x_max, vertical.y_max) == pytest.approx(
        (3, 7, 5, 9.4),
    )
    negative = LabelBox.from_text(5, 7, "AB", 2, rotation=-math.pi / 2)
    assert (negative.x_min, negative.y_min, negative.x_max, negative.y_max) == pytest.approx(
        (5, 4.6, 7, 7),
    )
    assert LabelBox.from_text(0, 0, "본선", 2).width == 4
    first = LabelBox(0, 0, 1, 1)
    assert not first.intersects(LabelBox(3, 0, 4, 1), padding=2)
    assert first.intersects(LabelBox(2.9, 0, 4, 1), padding=2)


def test_fixed_steps_leave_first_label_and_report_unresolved():
    config = replace(StaggerConfigPresets.up_distance(3), min_spacing=2, max_stagger_count=2)
    boxes = [LabelBox(0, 0, 1, 1, name) for name in ("z", "b", "c", "d")]
    result = Staggerer.stagger(boxes, config)
    assert result.offsets == {"z": (0, 0), "b": (0, 3), "c": (0, 6), "d": (0, 6)}
    assert result.level_map == {"z": 0, "b": 1, "c": 2, "d": 2}
    assert result.unresolved == ("d",)
    assert Staggerer.stagger(boxes, StaggerConfig()).level_map == dict.fromkeys("zbcd", 0)


@pytest.mark.parametrize("direction, expected", [
    (StaggerDirection.UP, (0, 3.5)),
    (StaggerDirection.DOWN, (0, -3.5)),
    (StaggerDirection.LEFT, (-3.5, 0)),
    (StaggerDirection.RIGHT, (3.5, 0)),
])
def test_increment_direction(direction, expected):
    config = StaggerConfig(StaggerMethod.INCREMENT, direction)
    assert config.offset_at_level(0) == (0, 0)
    assert config.offset_at_level(2) == expected


def test_scene_staggers_identical_text_ids_independently_and_preserves_geometry(tmp_path):
    point = Point2d(0, 0)
    text = Primitive.text(point, "본선", 1, rotation=math.pi / 2, style=Style(color=1))
    line = Primitive.line(point, Point2d(1, 0))
    scene = Scene((text, line, text), metadata={"alignment_name": "A"})
    config = replace(StaggerConfigPresets.right_increment(), min_spacing=1)
    assert StaggeredRenderer.apply_stagger(scene, StaggerConfigPresets.none()) is scene
    result = StaggeredRenderer.apply_stagger(scene, config)
    assert result.primitives[0] is text and result.primitives[1] is line
    assert result.primitives[2] == replace(text, points=(Point2d(3, 0),))
    assert result.metadata == {
        "alignment_name": "A", "stagger_levels": {"text_0": 0, "text_2": 1}, "stagger_unresolved": [],
    }
    path = tmp_path / "labels.dxf"
    DxfWriter(result).write(path)
    assert path.read_text("cp949").count("본선") == 2


def test_alignment_profile_and_composer_apply_staggering_to_complete_scene():
    alignment = AlignmentBuilder("A").with_pi_coords([(0, 0), (100, 0)]).build()
    config = replace(StaggerConfigPresets.up_distance(10), min_spacing=0, max_stagger_count=8)
    plan = AlignmentRenderer.render_plan(alignment, render_labels=True, stagger_config=config)
    assert "stagger_levels" in plan.metadata
    combined = SceneComposer.compose_multiple(
        [alignment, AlignmentBuilder("B").with_pi_coords([(0, 0), (100, 0)]).build()],
        RenderOptions(render_alignment_labels=True, stagger_config=config),
    )
    assert combined.metadata["alignment_names"] == ("A", "B")
    matching = [p.points[0] for p in combined.primitives if p.text == "STA 0.00"]
    assert len(matching) == 2 and matching[0] != matching[1]
    assert len(combined.metadata["stagger_levels"]) == sum(
        p.type is PrimitiveType.TEXT for p in combined.primitives
    )

    profile = ProfileBuilder().add_tangent(0, 100, 10, 10).build()
    label = StationElevationLabel(50)
    profile_scene = ProfileViewRenderer.render(
        [profile], "A", ProfileViewStyle(vertical_exaggeration=1),
        labels=[label, label], stagger_config=config,
    )
    assert len(profile_scene.metadata["stagger_levels"]) == 4
    assert not profile_scene.metadata["stagger_unresolved"]
