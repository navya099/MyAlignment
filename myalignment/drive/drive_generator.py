from __future__ import annotations

from collections.abc import Callable
import math
from typing import TYPE_CHECKING

from myalignment.drive.camera import DriveCamera, DrivePath
from myalignment.drive.camera_direction import CameraDirectionMode as Direction
from myalignment.drive.drive_config import DriveViewConfig
from myalignment.render.primitives_3d import Point3D

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.profile.profile import Profile


class DriveViewGenerator:
    """선형에 따라 배치한 카메라를 일정한 측점 속도로 샘플링한다."""

    @staticmethod
    def generate(
        alignment: Alignment, config: DriveViewConfig,
        surface_elevation_func: Callable[[float, float], float] | None = None, *,
        profile: Profile | None = None,
    ) -> DrivePath:
        """표고는 지정 표면 함수, 설계 종단, 영 표고 순으로 결정한다."""
        if not alignment.is_valid:
            return DrivePath(config=config)
        first, last = alignment.start_station, alignment.end_station
        grade = profile if profile is not None else alignment.fg_profile
        camera_start, camera_end = first, last
        if grade is not None and surface_elevation_func is None:
            if not grade.is_valid:
                raise ValueError("profile must have elevation geometry")
            camera_start = max(camera_start, grade.start_station)
            camera_end = min(camera_end, grade.end_station)
        requested_start = config.start_station if config.start_station is not None else first
        requested_end = config.end_station if config.end_station is not None else last
        start = max(first, camera_start - config.station_offset, requested_start)
        end = min(last, camera_end - config.station_offset, requested_end)
        if end < start:
            return DrivePath(config=config)

        def position(station):
            xy = alignment.point_at(station, config.x_offset)
            if surface_elevation_func is not None:
                elevation = surface_elevation_func(xy.x, xy.y)
            else:
                elevation = grade.elevation_at(station) if grade is not None else 0.0
            return Point3D(xy.x, xy.y, elevation + config.y_offset)

        def frame(station):
            camera_station = min(camera_end, max(camera_start, station + config.station_offset))
            camera = position(camera_station)
            direction = config.direction_mode
            azimuth = alignment.tangent_at(camera_station)
            target = None
            pitch = 0.0
            if direction is Direction.FIXED:
                azimuth = config.fixed_azimuth
            else:
                if grade is not None and surface_elevation_func is None:
                    pitch = grade.grade_at(camera_station)
                if direction is Direction.BACKWARD:
                    azimuth += math.pi
                    pitch = -pitch
                if direction is Direction.LOOK_AHEAD:
                    ahead = min(camera_end, camera_station + config.look_ahead_distance)
                    if ahead > camera_station:
                        target = position(ahead)
            if target is None or target.distance_to(camera) <= 1e-8:
                target = Point3D(camera.x + 10 * math.cos(azimuth), camera.y + 10 * math.sin(azimuth),
                                 camera.z + 10 * pitch)
            return DriveCamera(
                camera, target, fov=config.field_of_view, station=station,
                timestamp=(station - start) / config.speed_ms,
            )

        step = config.sample_interval
        stations = [start + i * step for i in range(math.ceil((end - start) / step))]
        if stations and stations[-1] >= end:
            stations.pop()
        stations.append(end)
        return DrivePath(tuple(frame(station) for station in stations), config)
