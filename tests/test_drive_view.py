from dataclasses import replace
import json
import math
import re

import pytest

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.drive.camera import DriveCamera, DrivePath
from myalignment.drive.camera_direction import CameraDirectionMode as Direction
from myalignment.drive.drive_config import DriveViewConfig
from myalignment.drive.drive_generator import DriveViewGenerator
from myalignment.drive.drive_preview import DriveViewPreview
from myalignment.export.drive_html_exporter import DriveViewHTMLExporter
from myalignment.profile.profile import ProfileBuilder
from myalignment.render.drive_3d_renderer import DriveView3DRenderer
from myalignment.render.primitives_3d import Point3D, PrimitiveType3D
from myalignment.render.scene_3d import Scene3D


def _axis():
    return (AlignmentBuilder("Main").with_pi_coords([(500000, 300000), (500043, 300000)])
            .with_start_station(100).build())


def _payload(path):
    html = path.read_text(encoding="utf-8")
    return html, json.loads(re.search(r'id="scene-data">([^<]+)</script>', html).group(1))


def test_camera_samples_offsets_grade_and_final_timestamp():
    axis = _axis()
    profile = ProfileBuilder("Grade").add_tangent(100, 143, 20, 24.3).build()
    cfg = DriveViewConfig(station_offset=2, x_offset=3, y_offset=1.5, speed_kmh=36, sample_interval=7)
    path = DriveViewGenerator.generate(axis, cfg, profile=profile)
    assert [frame.station for frame in path] == [100, 107, 114, 121, 128, 135, 141]
    assert path.duration == pytest.approx(4.1)
    assert path.cameras[0].position == Point3D(500002, 299997, 21.7)
    assert path.cameras[0].target.z == pytest.approx(22.7)
    assert path.at_time(0.35).position.x == pytest.approx(500005.5)
    assert path.at_time(path.duration + 1) is path.cameras[-1]

    negative = DriveViewGenerator.generate(axis, replace(cfg, station_offset=-2), profile=profile)
    assert negative.cameras[0].station == 102 and negative.cameras[0].timestamp == 0
    assert negative.cameras[-1].station == 143


def test_look_ahead_uses_curved_axis_and_terrain_at_offset():
    axis = (AlignmentBuilder("Curve").with_pi_coords([(0, 0), (50, 0), (50, 50)])
            .with_radii([None, 20, None]).build())
    cfg = DriveViewConfig(direction_mode=Direction.LOOK_AHEAD, x_offset=2, start_station=35, end_station=45,
                          look_ahead_distance=12)

    def terrain(x, y):
        return x * .1 + y * .05

    path = DriveViewGenerator.generate(axis, cfg, terrain)
    start, ahead = axis.point_at(35, 2), axis.point_at(47, 2)
    first = path.cameras[0]
    assert (first.position.x, first.position.y, first.position.z) == pytest.approx(
        (start.x, start.y, terrain(start.x, start.y) + cfg.y_offset),
    )
    assert (first.target.x, first.target.y, first.target.z) == pytest.approx(
        (ahead.x, ahead.y, terrain(ahead.x, ahead.y) + cfg.y_offset),
    )
    last = DriveViewGenerator.generate(axis, replace(cfg, start_station=axis.end_station, end_station=None)).cameras[-1]
    assert last.target.distance_to(last.position) == pytest.approx(10)


@pytest.mark.parametrize(("direction", "heading"), [
    (Direction.FORWARD, (1, 0, 0)), (Direction.BACKWARD, (-1, 0, 0)),
    (Direction.FIXED, (0, 1, 0)), (Direction.FREE, (1, 0, 0)),
])
def test_camera_heading_modes(direction, heading):
    path = DriveViewGenerator.generate(_axis(), DriveViewConfig(direction_mode=direction, fixed_azimuth=math.pi / 2))
    assert path.cameras[0].forward == pytest.approx(heading)


def test_profile_range_limits_path_and_single_frame_can_render():
    profile = ProfileBuilder("Short").add_tangent(115, 128, 5, 6).build()
    cfg = DriveViewConfig(direction_mode=Direction.LOOK_AHEAD, sample_interval=8, station_offset=3)
    path = DriveViewGenerator.generate(_axis(), cfg, profile=profile)
    assert [frame.station for frame in path] == [112, 120, 125]
    one = DrivePath((path.cameras[0],), cfg)
    assert DriveView3DRenderer.render_cameras(Scene3D(), one).primitives[0].type is PrimitiveType3D.POINT
    assert len(DriveView3DRenderer.render_camera_markers(Scene3D(), path, skip=2)) == 2
    assert DriveViewGenerator.generate(_axis(), replace(cfg, start_station=140), profile=profile).at_time(0) is None


def test_preview_uses_baseline_grade_and_embeds_world_mesh_and_controls(tmp_path):
    axis = _axis()
    profile = ProfileBuilder("Design").add_tangent(100, 143, 30, 34.3).build()
    axis = replace(axis, profiles=(profile,))
    assembly = AssemblyBuilder().add_both(lambda side: BasicLane(side=side)).build()
    corridor = (
        CorridorBuilder().add_baseline_from_alignment(axis, profile)
        .add_region("Paving", 100, 143, assembly).build()
    )
    output = tmp_path / "drive.html"
    result = DriveViewPreview.preview(axis, DriveViewConfig(near_plane=.5, far_plane=200), output, corridor,
                                     three_module_base="./vendor")
    assert result == str(output)
    html, payload = _payload(output)
    assert 'id="drive-time"' in html and "./vendor/build/three.module.js" in html
    assert {p["type"] for p in payload["primitives"]} == {"mesh"}
    drive = payload["metadata"]["drive_view"]
    assert drive["frames"][0]["position"] == [500000, 300000, 31.5]
    assert drive["frames"][-1]["station"] == 143
    assert drive["near_plane"] == .5 and drive["far_plane"] == 200


def test_export_escapes_payload_and_generates_background_route(tmp_path):
    path = DriveViewGenerator.generate(_axis(), DriveViewConfig())
    output = tmp_path / "drive.html"
    unsafe = "</script><script>broken</script>"
    background = json.dumps({"primitives": [], "metadata": {"tag": unsafe}})
    DriveViewHTMLExporter.export(path, output, background, unsafe)
    html, payload = _payload(output)
    assert unsafe not in html
    assert payload["metadata"]["tag"] == unsafe
    assert payload["primitives"][0]["layer"] == "C-DRIVE-ROUTE"
    assert payload["primitives"][0]["points"][0][2] == 0


def test_invalid_drive_inputs():
    for kwargs in (dict(speed_kmh=0), dict(sample_interval=float("nan")), dict(near_plane=20, far_plane=10),
                   dict(start_station=10, end_station=0)):
        with pytest.raises(ValueError):
            DriveViewConfig(**kwargs)
    point = Point3D()
    with pytest.raises(ValueError, match="strictly"):
        DrivePath((DriveCamera(point, point), DriveCamera(point, point)))
