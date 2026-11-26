from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
import math

from myalignment.drive.drive_config import DriveViewConfig
from myalignment.render.primitives_3d import Point3D


def _mix(a, b, fraction):
    return a + fraction * (b - a)


def _point_between(a, b, fraction):
    return Point3D(_mix(a.x, b.x, fraction), _mix(a.y, b.y, fraction), _mix(a.z, b.z, fraction))


@dataclass(frozen=True, slots=True)
class DriveCamera:
    """CAD 월드 좌표의 카메라 위치, 주시점과 재생 시각."""

    position: Point3D
    target: Point3D
    up: Point3D = Point3D(0, 0, 1)
    fov: float = 60.0
    station: float = 0.0
    timestamp: float = 0.0

    def __post_init__(self):
        if self.up is None:
            object.__setattr__(self, "up", Point3D(0, 0, 1))
        if not all(isinstance(p, Point3D) for p in (self.position, self.target, self.up)):
            raise TypeError("position, target and up must be Point3D")
        if not math.isfinite(self.station) or not math.isfinite(self.timestamp) or self.timestamp < 0:
            raise ValueError("station must be finite and timestamp finite and nonnegative")
        if not 0 < self.fov < 180:
            raise ValueError("fov must be between 0 and 180 degrees")
        if self.up == Point3D():
            raise ValueError("up vector must be nonzero")

    @property
    def forward(self) -> tuple[float, float, float]:
        """정규화한 주시 방향."""
        x, y, z = self.target.x - self.position.x, self.target.y - self.position.y, self.target.z - self.position.z
        length = math.hypot(x, y, z)
        return (x / length, y / length, z / length) if length > 1e-9 else (1.0, 0.0, 0.0)


@dataclass(frozen=True, slots=True)
class DrivePath:
    """시간순으로 정렬한 프레임과 주행 설정."""

    cameras: tuple[DriveCamera, ...] = ()
    config: DriveViewConfig | None = None

    def __post_init__(self):
        cameras = tuple(self.cameras)
        if any(a.timestamp >= b.timestamp for a, b in zip(cameras, cameras[1:])):
            raise ValueError("camera timestamps must strictly increase")
        object.__setattr__(self, "cameras", cameras)

    def __len__(self) -> int:
        return len(self.cameras)

    def __iter__(self):
        return iter(self.cameras)

    @property
    def duration(self) -> float:
        return self.cameras[-1].timestamp if self.cameras else 0.0

    def at_time(self, t: float) -> DriveCamera | None:
        """시각에 해당하는 프레임을 보간하고 범위 밖에서는 끝 프레임을 사용한다."""
        if not math.isfinite(t):
            raise ValueError("time must be finite")
        if not self.cameras:
            return None
        index = bisect_left(self.cameras, t, key=lambda frame: frame.timestamp)
        if index == 0:
            return self.cameras[0]
        if index == len(self.cameras):
            return self.cameras[-1]
        b = self.cameras[index]
        if b.timestamp == t:
            return b
        a = self.cameras[index - 1]
        fraction = (t - a.timestamp) / (b.timestamp - a.timestamp)
        up = _point_between(a.up, b.up, fraction)
        return DriveCamera(
            _point_between(a.position, b.position, fraction),
            _point_between(a.target, b.target, fraction),
            up if up != Point3D() else a.up, _mix(a.fov, b.fov, fraction),
            _mix(a.station, b.station, fraction), t,
        )
