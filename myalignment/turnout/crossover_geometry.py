from dataclasses import dataclass, field
from typing import Any

from cadgeom import Point2d

from myalignment.turnout.geometry_sampling import CompleteConnection, SamplePoint

@dataclass(frozen=True, slots=True)
class ConnectionGeometry:
    name: str
    start_point: Any
    end_point: Any
    start_azimuth: float
    end_azimuth: float
    length: float
    start_station: float
    end_station: float

@dataclass(frozen=True, slots=True)
class CrossoverGeometry:
    """검증된 연결 기하와 선택적으로 계산한 렌더링용 평면 좌표."""

    turnout1_station: float = 0.0
    turnout1_point: Any = None
    turnout1_azimuth: float = 0.0
    turnout2_station: float = 0.0
    turnout2_point: Any = None
    turnout2_azimuth: float = 0.0
    connecting_length: float = 0.0
    connecting_azimuth: float = 0.0
    connections: tuple[ConnectionGeometry, ...] = field(default_factory=tuple)
    paths: tuple[CompleteConnection, ...] = field(default_factory=tuple)
    required_station_delta: float = 0.0
    is_valid: bool = False
    error_message: str = ''
    gauge: float | None = field(default=None, kw_only=True)
    main1_left_rail: tuple[Point2d, ...] = field(default=(), kw_only=True)
    main1_right_rail: tuple[Point2d, ...] = field(default=(), kw_only=True)
    main2_left_rail: tuple[Point2d, ...] = field(default=(), kw_only=True)
    main2_right_rail: tuple[Point2d, ...] = field(default=(), kw_only=True)
    connecting_rails: tuple[tuple[tuple[Point2d, ...], tuple[Point2d, ...]], ...] = field(default=(), kw_only=True)
    turnout_markers: tuple[tuple[str, Point2d, float | None], ...] = field(default=(), kw_only=True)
    diamond_center: Point2d | None = field(default=None, kw_only=True)
    diamond_diagonal1: float = field(default=0.0, kw_only=True)
    diamond_diagonal2: float = field(default=0.0, kw_only=True)

    def __post_init__(self):
        if not self.is_valid and not self.error_message:
            raise ValueError('invalid geometry requires error_message')

    def sample_connections(self, step: float = 0.5) -> tuple[tuple[SamplePoint, ...], ...]:
        """Sample each full centre-line, including both turnout curves."""
        if not self.is_valid:
            raise ValueError(self.error_message)
        if not self.paths:
            raise ValueError('full turnout paths are unavailable')
        return tuple(path.sample_points(step) for path in self.paths)
