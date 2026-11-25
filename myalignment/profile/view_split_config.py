from dataclasses import dataclass
import math

from myalignment.profile.view_split_method import ProfileViewSplitMethod


@dataclass(frozen=True, slots=True)
class ProfileViewSplitConfig:
    """분할 범위와 그리드 배치 설정.

    overlap_station은 인접한 두 패널이 경계 양쪽으로 확장되는 거리다.
    min_view_length는 자동 측점 분할이 가능한 범위에서 적용된다.
    """

    method: ProfileViewSplitMethod = ProfileViewSplitMethod.STATION_RANGE
    max_station_per_view: float = 500.0
    max_pvi_per_view: int = 10
    manual_split_stations: tuple[float, ...] = ()
    min_view_length: float = 100.0
    overlap_station: float = 20.0
    align_to_pvi: bool = True
    columns: int = 1
    column_gap: float = 50.0
    row_gap: float = 50.0
    include_start_label: bool = True

    def __post_init__(self):
        if not isinstance(self.method, ProfileViewSplitMethod):
            raise ValueError("method must be a ProfileViewSplitMethod")
        for name in ("min_view_length", "overlap_station", "column_gap", "row_gap"):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and nonnegative")
        if type(self.columns) is not int or self.columns < 1:
            raise ValueError("columns must be a positive integer")
        if self.method is ProfileViewSplitMethod.STATION_RANGE:
            if not math.isfinite(self.max_station_per_view) or self.max_station_per_view <= 0:
                raise ValueError("max_station_per_view must be finite and positive")
        if self.method is ProfileViewSplitMethod.PVI_COUNT:
            if type(self.max_pvi_per_view) is not int or self.max_pvi_per_view < 1:
                raise ValueError("max_pvi_per_view must be a positive integer")
        stations = tuple(self.manual_split_stations)
        object.__setattr__(self, "manual_split_stations", stations)
        if self.method is ProfileViewSplitMethod.MANUAL and (
            not stations or not all(math.isfinite(station) for station in stations)
            or any(a >= b for a, b in zip(stations, stations[1:]))
        ):
            raise ValueError("manual_split_stations must be finite and strictly increasing")
