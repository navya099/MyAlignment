from collections.abc import Iterable
from dataclasses import replace
from itertools import pairwise
import math
from typing import TypeAlias

from myalignment.profile.profile_asymmetric_parabola import ProfileAsymmetricParabola
from myalignment.profile.profile_symmetric_parabola import ProfileSymmetricParabola
from myalignment.profile.profileentity import ProfileEntity
from myalignment.profile.profiletangent import ProfileTangent

Number: TypeAlias = float | str
ProfilePoint: TypeAlias = tuple[Number, Number]
CurveSpec: TypeAlias = Number | tuple[Number, Number] | None
ProfilePVI: TypeAlias = ProfilePoint | tuple[Number, Number, CurveSpec]


def _ordered_rows(rows, *, allow_curves=False):
    previous = None
    for index, row in enumerate(rows, start=1):
        try:
            if isinstance(row, (str, bytes)):
                raise ValueError()
            station, elevation, *spec = row
            if len(spec) > int(allow_curves):
                raise ValueError()
            station, elevation = float(station), float(elevation)
        except (TypeError, ValueError, OverflowError) as error:
            suffix = " and optional curve length" if allow_curves else ""
            raise ValueError(f"Profile row {index}: expected a numeric station and elevation{suffix}") from error
        if not math.isfinite(station) or not math.isfinite(elevation):
            raise ValueError(f"Profile row {index}: station and elevation must be finite")
        if previous is not None and station <= previous:
            raise ValueError(f"Profile row {index}: raw stations must be strictly increasing")
        yield station, elevation, spec[0] if spec else None
        previous = station


def _point_tangents(points: Iterable[ProfilePoint]) -> list[ProfileTangent]:
    tangents = [
        ProfileTangent.create(a[0], b[0], a[1], b[1])
        for a, b in pairwise(_ordered_rows(points))
    ]
    if not tangents:
        raise ValueError("At least two profile points are required")
    return tangents


def _curve_lengths(spec: CurveSpec, row: int) -> tuple[float, float] | None:
    if spec is None:
        return None
    try:
        if isinstance(spec, (tuple, list)):
            left, right = (float(value) for value in spec)
            if all(math.isfinite(value) and value > 0 for value in (left, right)):
                return left, right
        else:
            total = float(spec)
            if total == 0:
                return None
            if math.isfinite(total) and total / 2 > 0:
                return total / 2, total / 2
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"Profile row {row}: invalid curve length") from error
    raise ValueError(f"Profile row {row}: curve lengths must be finite and positive")


def _same_station(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=0, abs_tol=max(1e-12, 2 * math.ulp(a), 2 * math.ulp(b)))


def _pvi_curve(previous, current, following, lengths, row):
    left, right = lengths
    station, elevation, _ = current
    start, end = station - left, station + right
    if not start < station < end or not math.isfinite(left + right):
        raise ValueError(f"Profile row {row}: invalid curve bounds")
    if _same_station(start, previous[0]):
        start = previous[0]
    if _same_station(end, following[0]):
        end = following[0]
    if start < previous[0] or end > following[0]:
        raise ValueError(f"Profile row {row}: curve extends beyond an adjacent PVI")
    grade_in = (elevation - previous[1]) / (station - previous[0])
    grade_out = (following[1] - elevation) / (following[0] - station)
    try:
        if left == right:
            curve = ProfileSymmetricParabola.create(station, elevation, grade_in, grade_out, left + right)
        else:
            curve = ProfileAsymmetricParabola.create(station, elevation, grade_in, grade_out, left, right)
        if not all(map(math.isfinite, (grade_in, grade_out, curve.start_elevation, curve.end_elevation))):
            raise ValueError("curve grades and elevations must be finite")
    except ValueError as error:
        raise ValueError(f"Profile row {row}: {error}") from error
    return replace(curve, start_station=start, end_station=end)


def _pvi_entities(pvis: Iterable[ProfilePVI]) -> list[ProfileEntity]:
    rows = list(_ordered_rows(pvis, allow_curves=True))
    if len(rows) < 2:
        raise ValueError("At least two profile PVIs are required")
    lengths = [_curve_lengths(spec, index) for index, (_, _, spec) in enumerate(rows, start=1)]
    if lengths[0] or lengths[-1]:
        raise ValueError("The first and last PVI cannot have a curve")

    entities = []
    cursor, elevation, _ = rows[0]
    for index, (station, z, _) in enumerate(rows[1:], start=1):
        curve = None
        if lengths[index] is not None:
            curve = _pvi_curve(rows[index - 1], rows[index], rows[index + 1], lengths[index], index + 1)
        join_station = station if curve is None else curve.start_station
        join_elevation = z if curve is None else curve.start_elevation
        if curve is not None and _same_station(cursor, join_station) and cursor < curve.pvi_station:
            curve = replace(curve, start_station=cursor)
        elif join_station > cursor:
            entities.append(ProfileTangent.create(cursor, join_station, elevation, join_elevation))
        elif join_station < cursor:
            raise ValueError(f"Profile row {index + 1}: vertical curves overlap")
        if curve is not None:
            entities.append(curve)
            cursor, elevation = curve.end_station, curve.end_elevation
        else:
            cursor, elevation = station, z
    return entities
