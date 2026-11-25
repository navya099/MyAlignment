from __future__ import annotations

from dataclasses import dataclass
import math
from typing import TYPE_CHECKING

from myalignment.profile.vertical_geometry_extractor import VerticalGeometryExtractor
from myalignment.profile.vertical_geometry_type import VerticalGeometryPointType
from myalignment.profile.view_split_method import ProfileViewSplitMethod

if TYPE_CHECKING:
    from myalignment.profile.profile import Profile
    from myalignment.profile.view_split_config import ProfileViewSplitConfig


@dataclass(frozen=True, slots=True)
class ProfileViewSegment:
    """한 패널에 표시할 원시 측점의 닫힌 구간."""

    start_station: float = 0.0
    end_station: float = 0.0
    view_index: int = 0
    total_views: int = 1

    @property
    def length(self) -> float:
        return self.end_station - self.start_station

    def contains(self, station: float) -> bool:
        """시작과 끝을 포함해 패널에 속하는 측점인지 확인한다."""
        return self.start_station <= station <= self.end_station


class ProfileViewSplitter:
    """종단 뷰의 원시 측점 범위를 분할한다."""

    @classmethod
    def split(
        cls,
        profile: Profile,
        config: ProfileViewSplitConfig,
        *,
        station_range: tuple[float, float] | None = None,
    ) -> list[ProfileViewSegment]:
        """분할 경계를 정하고 원본 범위 안에서 인접 패널에 겹침을 더한다.

        station_range는 여러 종단을 한꺼번에 그릴 때 전체 도면 범위를
        공급할 수 있다. PVI 기준은 profile에서 읽는다.
        """
        if not profile.is_valid and station_range is None:
            return []
        start, end = (profile.start_station, profile.end_station) if station_range is None else station_range
        if not math.isfinite(start) or not math.isfinite(end) or start >= end:
            raise ValueError("station_range must be finite and increasing")

        method = config.method
        pvis = ()
        if method is ProfileViewSplitMethod.PVI_COUNT or (
            method is ProfileViewSplitMethod.STATION_RANGE and config.align_to_pvi
        ):
            pvis = tuple(sorted({
                point.station for point in VerticalGeometryExtractor.extract(profile)
                if point.point_type is VerticalGeometryPointType.PVI
                and profile.start_station < point.station < profile.end_station
                and start < point.station < end
            }))
        cuts = []
        if method is ProfileViewSplitMethod.STATION_RANGE:
            cuts = cls._station_cuts(start, end, pvis, config)
        elif method is ProfileViewSplitMethod.PVI_COUNT:
            limit = config.max_pvi_per_view
            cuts = list(pvis[limit - 1:-1:limit])
        elif method is ProfileViewSplitMethod.MANUAL:
            cuts = [station for station in config.manual_split_stations if start < station < end]

        bounds = [start, *cuts, end]
        count = len(bounds) - 1
        overlap = config.overlap_station
        return [
            ProfileViewSegment(
                max(start, left - overlap) if index else left,
                min(end, right + overlap) if index < count - 1 else right,
                index, count,
            )
            for index, (left, right) in enumerate(zip(bounds, bounds[1:]))
        ]

    @staticmethod
    def _station_cuts(start, end, pvis, config):
        maximum = config.max_station_per_view
        count = math.ceil((end - start) / maximum)
        step = (end - start) / count
        minimum = min(config.min_view_length, step)
        cuts = []
        previous = start
        for index in range(1, count):
            remaining = count - index
            ideal = start + index * step
            low = max(previous + minimum, end - remaining * maximum)
            high = min(previous + maximum, end - remaining * minimum)
            candidates = (station for station in pvis if low <= station <= high and station > previous)
            cut = min(candidates, key=lambda station: (abs(station - ideal), station),
                      default=max(low, min(high, ideal)))
            if cut <= previous or cut >= end:
                raise ValueError("station cuts cannot be represented at this spacing")
            cuts.append(cut)
            previous = cut
        return cuts
