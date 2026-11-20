from collections.abc import Sequence
import math

from myalignment.cant.curve import CantCurve
from myalignment.profile.cant_band_segment import CantBandSegment
from myalignment.superelevation.critical_station import TransitionRegionType


class CantBandSegmentExtractor:
    """캔트의 크기 변화로 정상, 진입, 완전 캔트, 진출 구간을 구분한다."""

    @classmethod
    def extract(cls, cant_curves: Sequence[CantCurve]) -> list[CantBandSegment]:
        segments = [segment for curve in cant_curves for segment in cls._extract_curve(curve)]
        return sorted(segments, key=lambda segment: segment.start_station)

    @classmethod
    def _extract_curve(cls, curve: CantCurve):
        critical = curve.critical_stations
        if not critical:
            return
        if any(not math.isfinite(p.station) or not math.isfinite(p.cant_value) for p in critical):
            raise ValueError("Cant critical stations and values must be finite")
        if any(a.station >= b.station for a, b in zip(critical, critical[1:])):
            raise ValueError("Cant critical stations must be strictly increasing")

        start, end = curve.start_station, curve.end_station
        if not math.isfinite(start) or not math.isfinite(end):
            raise ValueError("Cant curve bounds must be finite")
        if end <= start:
            start, end = critical[0].station, critical[-1].station
        if end <= start:
            return
        stations = [start, *(p.station for p in critical if start < p.station < end), end]
        values = [(station, curve.cant_at(station).cant_value) for station in stations]
        for (left, a), (right, b) in zip(values, values[1:]):
            if (a < 0 < b) or (b < 0 < a):
                zero = left + (right - left) * abs(a) / (abs(a) + abs(b))
                yield cls._segment(left, zero, a, 0.0, curve)
                yield cls._segment(zero, right, 0.0, b, curve)
            else:
                yield cls._segment(left, right, a, b, curve)

    @staticmethod
    def _segment(left, right, a, b, curve):
        a, b = abs(a) * 1000, abs(b) * 1000
        kind = TransitionRegionType
        if math.isclose(a, b, rel_tol=0.0, abs_tol=1e-9):
            region = kind.NORMAL if max(a, b) <= 1e-9 else kind.FULL_SUPERELEVATION
        else:
            region = kind.TRANSITION_IN if b > a else kind.TRANSITION_OUT
        return CantBandSegment(left, right, a, b, region, curve.pivot_method)
