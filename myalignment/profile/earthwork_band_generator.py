from __future__ import annotations

import math
from typing import TYPE_CHECKING

from myalignment.profile.earthwork_band_data import EarthworkBandData, EarthworkSample
from myalignment.profile.earthwork_band_style import EarthworkBandStyle
from myalignment.profile.hatch_generator import ProfileHatchGenerator

if TYPE_CHECKING:
    from myalignment.profile.profile import Profile


class EarthworkBandGenerator:
    """계획·현황 종단이 겹치는 구간의 밴드 샘플과 추정 체적을 계산한다."""

    @staticmethod
    def generate(
        fg_profile: Profile, eg_profile: Profile, style: EarthworkBandStyle | None = None,
        road_width: float = 10.0, *, station_range: tuple[float, float] | None = None,
    ) -> EarthworkBandData:
        """공통 구간의 양 끝을 포함하고 분할 뷰에서도 동일한 샘플 간격을 유지한다."""
        if not math.isfinite(road_width) or road_width < 0:
            raise ValueError("road_width must be finite and nonnegative")
        if station_range is not None and (
            not all(map(math.isfinite, station_range)) or station_range[0] >= station_range[1]
        ):
            raise ValueError("station_range must be finite and increasing")
        if not fg_profile.is_valid or not eg_profile.is_valid:
            return EarthworkBandData()

        origin = max(fg_profile.start_station, eg_profile.start_station)
        start, end = origin, min(fg_profile.end_station, eg_profile.end_station)
        if station_range is not None:
            start, end = max(start, station_range[0]), min(end, station_range[1])
        if start >= end:
            return EarthworkBandData()

        style = style or EarthworkBandStyle.standard()
        step = style.sample_interval
        first = math.floor((start - origin) / step) + 1
        last = math.ceil((end - origin) / step)
        stations = [start]
        for index in range(first, last):
            station = origin + index * step
            if station - stations[-1] > math.ulp(stations[-1]) and end - station > math.ulp(end):
                stations.append(station)
        stations.append(end)
        samples = tuple(
            EarthworkSample(station, fg_profile.elevation_at(station), eg_profile.elevation_at(station))
            for station in stations
        )

        # 해치와 같은 교차점 분할을 적용해 절토·성토 체적을 각각 적분한다.
        if road_width == 0:
            return EarthworkBandData(samples)
        volume = ProfileHatchGenerator.generate(
            fg_profile, eg_profile, sample_step=step, road_width=road_width, station_range=(start, end),
        )
        return EarthworkBandData(samples, volume.cut_volume_estimate, volume.fill_volume_estimate)
