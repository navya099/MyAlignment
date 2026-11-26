from __future__ import annotations

from myalignment.drive.camera import DrivePath
from myalignment.render.primitives_3d import Point3D, Primitive3D, Style3D
from myalignment.render.scene_3d import Scene3D


class DriveView3DRenderer:
    """주행 경로, 방향선과 프레임 마커를 3D 장면에 추가한다."""

    @staticmethod
    def render_cameras(scene: Scene3D, path: DrivePath) -> Scene3D:
        if not len(path):
            return scene
        path_style = Style3D(color=1, layer="C-DRIVE-CAMERA-PATH")
        direction_style = Style3D(color=2, layer="C-DRIVE-CAMERA-DIR")
        positions = tuple(camera.position for camera in path)
        primitives = [Primitive3D.polyline(positions, style=path_style)] if len(path) > 1 else [
            Primitive3D.point(positions[0], path_style),
        ]
        for camera in path:
            p = camera.position
            x, y, z = camera.forward
            primitives.append(Primitive3D.line(p, Point3D(p.x + x * 5, p.y + y * 5, p.z + z * 5), direction_style))
        return scene.add_all(primitives)

    @staticmethod
    def render_camera_markers(scene: Scene3D, path: DrivePath, skip: int = 5) -> Scene3D:
        if type(skip) is not int or skip < 1:
            raise ValueError("skip must be a positive integer")
        style = Style3D(color=1, layer="C-DRIVE-MARKER")
        return scene.add_all(Primitive3D.point(frame.position, style) for frame in path.cameras[::skip])
