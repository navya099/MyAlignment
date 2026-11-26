from __future__ import annotations

import math
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.profile.hatch_region import HatchCollection, HatchRegion
from myalignment.profile.hatch_style import ProfileHatchStyle

if TYPE_CHECKING:
    from myalignment.profile.profile import Profile


_HEIGHT_TOL = 1e-8


def _overlaps(fg, eg, station_range):
    design, existing = iter(fg.entities), iter(eg.entities)
    a, b = next(design, None), next(existing, None)
    low, high = station_range
    while a is not None and b is not None:
        start = max(a.start_station, b.start_station, low)
        end = min(a.end_station, b.end_station, high)
        if start < end:
            yield a, b, start, end
        if min(a.end_station, b.end_station) >= high:
            break
        a_end, b_end = a.end_station, b.end_station
        if a_end <= b_end:
            a = next(design, None)
        if b_end <= a_end:
            b = next(existing, None)


def _root(function, left, right, a):
    # Bisect using the actual profile functions and stop at floating point resolution.
    for _ in range(64):
        middle = left + (right - left) / 2
        if middle in (left, right):
            return middle
        value = function(middle)
        if value == 0:
            return middle
        if (value < 0) == (a < 0):
            left = middle
        else:
            right = middle
    return left + (right - left) / 2


def _sample_intervals(a, b, start, end, step):
    length = end - start
    count = max(1, math.ceil(length / step))
    stations = {start, end, *(start + length * i / count for i in range(1, count))}
    for entity in (a, b):
        stations.update(s for s in getattr(entity, "pvi_stations", lambda: ())() if start < s < end)

    def grades(station):
        return a.grade_at(station) - b.grade_at(station)

    def difference(station):
        return a.elevation_at(station) - b.elevation_at(station)

    stations = sorted(stations)
    turning = set()
    for low, high in zip(stations, stations[1:]):
        g1, g2 = grades(low), grades(high)
        if (g1 < 0 < g2) or (g2 < 0 < g1):
            turning.add(_root(grades, low, high, g1))
    stations = sorted(set(stations) | turning)
    sampled = []

    def sample(station, *, crossing=False):
        fg, eg = a.elevation_at(station), b.elevation_at(station)
        if crossing or abs(fg - eg) <= _HEIGHT_TOL:
            fg = eg = fg + (eg - fg) / 2
        return station, fg, eg

    for low, high in zip(stations, stations[1:]):
        sample_low = sample(low)
        sampled.append(sample_low)
        d1 = sample_low[1] - sample_low[2]
        d2 = difference(high)
        if (d1 < 0 and d2 > _HEIGHT_TOL) or (d1 > 0 and d2 < -_HEIGHT_TOL):
            crossing = _root(difference, low, high, d1)
            if low < crossing < high:
                sampled.append(sample(crossing, crossing=True))
    sampled.append(sample(end))
    for left, right in zip(sampled, sampled[1:]):
        delta = (left[1] - left[2]) + (right[1] - right[2])
        if delta:
            yield ("fill" if delta > 0 else "cut"), left, right


def _region(kind, run, style):
    top_index, bottom_index = (2, 1) if kind == "cut" else (1, 2)
    return HatchRegion(
        kind, run[0][0], run[-1][0],
        tuple(Point2d(p[0], p[top_index]) for p in run), tuple(Point2d(p[0], p[bottom_index]) for p in run),
        getattr(style, f"{kind}_pattern"), getattr(style, f"{kind}_color"), getattr(style, f"{kind}_opacity"),
    )


class ProfileHatchGenerator:
    """설계·현황 종단 사이에서 교차점을 찾아 절토와 성토를 분리한다."""

    @staticmethod
    def generate(
        fg_profile: Profile, eg_profile: Profile, style: ProfileHatchStyle | None = None,
        sample_step: float = 5.0, *, road_width: float = 10.0,
        station_range: tuple[float, float] | None = None,
    ) -> HatchCollection:
        """종단면 근사 면적과 일정 폭으로 환산한 추정 체적을 반환한다."""
        if not math.isfinite(sample_step) or sample_step <= 0:
            raise ValueError("sample_step must be finite and positive")
        if not math.isfinite(road_width) or road_width < 0:
            raise ValueError("road_width must be finite and nonnegative")
        if station_range is not None and (
            not all(map(math.isfinite, station_range)) or station_range[0] >= station_range[1]
        ):
            raise ValueError("station_range must be finite and increasing")
        style = style or ProfileHatchStyle.standard()
        bounds = station_range or (-math.inf, math.inf)
        run, kind, regions = [], None, []
        for a, b, start, end in _overlaps(fg_profile, eg_profile, bounds):
            for side, left, right in _sample_intervals(a, b, start, end, sample_step):
                if run and (side != kind or left != run[-1] or left[1] == left[2]):
                    regions.append(_region(kind, run, style))
                    run = []
                if not run:
                    run = [left]
                    kind = side
                run.append(right)
        if run:
            regions.append(_region(kind, run, style))
        result = HatchCollection(tuple(regions))
        return HatchCollection(result.regions, result.total_area("cut") * road_width,
                               result.total_area("fill") * road_width)
