from dataclasses import dataclass
import math

from myalignment.drive.camera_direction import CameraDirectionMode


@dataclass(frozen=True, slots=True)
class DriveViewConfig:
    """주행 구간, 카메라 오프셋, 시야각과 속도."""

    station_offset: float = 0.0
    x_offset: float = 0.0
    y_offset: float = 1.5
    direction_mode: CameraDirectionMode = CameraDirectionMode.FORWARD
    fixed_azimuth: float = 0.0
    look_ahead_distance: float = 30.0
    focal_length: float = 35.0
    field_of_view: float = 60.0
    near_plane: float = 0.1
    far_plane: float = 10000.0
    speed_kmh: float = 60.0
    sample_interval: float = 5.0
    start_station: float | None = None
    end_station: float | None = None

    def __post_init__(self):
        if not isinstance(self.direction_mode, CameraDirectionMode):
            raise ValueError("direction_mode must be a CameraDirectionMode")
        for name in ("station_offset", "x_offset", "y_offset", "fixed_azimuth",
                     "look_ahead_distance", "focal_length", "field_of_view", "near_plane", "far_plane",
                     "speed_kmh", "sample_interval"):
            if not math.isfinite(getattr(self, name)):
                raise ValueError(f"{name} must be finite")
        for name in ("look_ahead_distance", "focal_length", "near_plane", "speed_kmh", "sample_interval"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.speed_ms == 0:
            raise ValueError("speed_kmh is too small")
        if not 0 < self.field_of_view < 180 or self.far_plane <= self.near_plane:
            raise ValueError("invalid field_of_view or near/far planes")
        if any(value is not None and not math.isfinite(value) for value in (self.start_station, self.end_station)):
            raise ValueError("station bounds must be finite")
        if self.start_station is not None and self.end_station is not None and self.end_station < self.start_station:
            raise ValueError("end_station precedes start_station")

    @property
    def speed_ms(self) -> float:
        """m/s 단위 주행 속도."""
        return self.speed_kmh / 3.6
