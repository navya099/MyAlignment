from __future__ import annotations

import json
from pathlib import Path

from myalignment.drive.camera import DrivePath
from myalignment.drive.drive_config import DriveViewConfig
from myalignment.export.json_3d_exporter import Json3DExporter
from myalignment.export.scene_3d_serializer import Scene3DSerializer
from myalignment.render.primitives_3d import Point3D, Primitive3D, Style3D
from myalignment.render.scene_3d import Scene3D


def _coordinates(point):
    return [point.x, point.y, point.z]


def _route_scene(path, eye_height):
    points = tuple(Point3D(c.position.x, c.position.y, c.position.z - eye_height) for c in path)
    style = Style3D(color=4, layer="C-DRIVE-ROUTE")
    if len(points) > 1:
        return Scene3D((Primitive3D.polyline(points, style=style),))
    if points:
        return Scene3D((Primitive3D.point(points[0], style),))
    return Scene3D()


class DriveViewHTMLExporter:
    """기존 3D 뷰어에 주행 프레임과 재생 설정을 포함해 저장한다."""

    @staticmethod
    def export(
        path: DrivePath, html_path: str | Path, corridor_scene_json: str | None = None,
        title: str = "3D Drive View", *, scene: Scene3D | None = None,
        three_module_base: str | None = None,
    ) -> None:
        """선택한 배경 장면과 주행 제어를 하나의 HTML에 저장한다."""
        if scene is not None and corridor_scene_json is not None:
            raise ValueError("Provide either scene or corridor_scene_json")
        config = path.config or DriveViewConfig()
        if corridor_scene_json is not None:
            data = json.loads(corridor_scene_json)
            if not isinstance(data, dict) or not isinstance(data.get("primitives"), list):
                raise ValueError("corridor_scene_json must contain a Scene3D JSON object")
        else:
            data = Scene3DSerializer.to_dict(scene or Scene3D())
        if not data["primitives"]:
            data["primitives"] = Scene3DSerializer.to_dict(_route_scene(path, config.y_offset))["primitives"]
        metadata = dict(data.get("metadata", {}))
        metadata["drive_view"] = {
            "frames": [
                {
                    "position": _coordinates(camera.position),
                    "target": _coordinates(camera.target),
                    "up": _coordinates(camera.up),
                    "fov": camera.fov,
                    "station": camera.station,
                    "timestamp": camera.timestamp,
                }
                for camera in path
            ],
            "duration": path.duration,
            "speed_kmh": config.speed_kmh,
            "sample_interval": config.sample_interval,
            "direction_mode": config.direction_mode.value,
            "near_plane": config.near_plane,
            "far_plane": config.far_plane,
            "focal_length": config.focal_length,
        }
        data["metadata"] = metadata
        options = {} if three_module_base is None else {"three_module_base": three_module_base}
        Json3DExporter._write_html(data, html_path, title, **options)
