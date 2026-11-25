from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math
from typing import TYPE_CHECKING

from myalignment.assembly.codes import LinkCode
from myalignment.corridor.slope_pattern import SlopePattern, SlopePatternCollection, SlopePatternElement
from myalignment.corridor.slope_pattern_style import SlopePatternStyle
from myalignment.corridor.slope_pattern_type import SlopePatternType
from myalignment.corridor.surface_builder import _resolve_baseline
from myalignment.render.primitives_3d import Point3D

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.assembly.point import AssemblyPoint
    from myalignment.corridor.corridor import Corridor
    from myalignment.profile.profile import Profile


_EPS = 1e-9


def _interpolate(a: Point3D, b: Point3D, t: float) -> Point3D:
    return Point3D(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t, a.z + (b.z - a.z) * t)


def _interior_fractions(length, spacing):
    if length > _EPS:
        for index in range(1, math.ceil(length / spacing)):
            distance = index * spacing
            if distance < length - _EPS:
                yield distance / length


@dataclass(frozen=True, slots=True)
class _FaceSection:
    station: float
    start_offset: float
    end_offset: float
    start: Point3D
    end: Point3D

    @property
    def width(self):
        return abs(self.end_offset - self.start_offset)

    @property
    def rise(self):
        return self.end.z - self.start.z

    def point(self, fraction, *, elevation=None):
        point = _interpolate(self.start, self.end, fraction)
        return point if elevation is None else Point3D(point.x, point.y, elevation)


def _sample_faces(region, station, alignment, profile):
    grade = profile.elevation_at(station) if profile is not None else 0.0
    _, links = region.cross_section_at(station)
    faces = {}
    occurrences = {}

    def world(point: AssemblyPoint) -> Point3D:
        xy = alignment.point_at(station, point.x)
        return Point3D(xy.x, xy.y, grade + point.z)

    for link in links:
        if link.code is not LinkCode.SLOPE or abs(link.end.x - link.start.x) <= _EPS:
            continue
        start, end = sorted((link.start, link.end), key=lambda point: abs(point.x))
        side = "left" if end.x < 0 else "right"
        key = side, start.code, end.code
        occurrence = occurrences.get(key, 0)
        occurrences[key] = occurrence + 1
        faces[(*key, occurrence)] = _FaceSection(station, start.x, end.x, world(start), world(end))
    return faces


def _hatches(face, following, style):
    cross_reach = min(style.spacing_vertical, style.pattern_size) / face.width
    for t in (0.0, *_interior_fractions(face.width, style.spacing_horizontal)):
        end_fraction = min(1.0, t + cross_reach)
        a, b = face.point(t), face.point(end_fraction)
        if following is not None:
            along = min(1.0, style.pattern_size / (following.station - face.station))
            b = _interpolate(b, following.point(end_fraction), along)
        yield SlopePatternElement((a, b))


def _grid(face, following, style):
    yield SlopePatternElement((face.start, face.end))
    if following is not None:
        for t in (0.0, *_interior_fractions(abs(face.rise), style.spacing_vertical), 1.0):
            yield SlopePatternElement((face.point(t), following.point(t)))


def _steps(face, style, alignment, region):
    if abs(face.rise) <= _EPS:
        return
    count = max(math.ceil(abs(face.rise) / style.step_height), math.ceil(face.width / style.step_width))
    vertices = [face.start]
    for step in range(1, count + 1):
        t = step / count
        tread = face.end if step == count else face.point(t)
        vertices.extend((face.point((step - 1) / count, elevation=tread.z), tread))
        if style.include_berm and step < count:
            offset = face.start_offset + t * (face.end_offset - face.start_offset)
            low = max(region.start_station, face.station - style.berm_width / 2)
            high = min(region.end_station, face.station + style.berm_width / 2)
            if high - low > _EPS:
                a, b = alignment.point_at(low, offset), alignment.point_at(high, offset)
                yield SlopePatternElement((Point3D(a.x, a.y, tread.z), Point3D(b.x, b.y, tread.z)))
    yield SlopePatternElement(tuple(vertices), "polyline")


def _stakes(face, style):
    for t in (0.0, *_interior_fractions(face.start.distance_to(face.end), style.stake_spacing), 1.0):
        base = face.point(t)
        yield SlopePatternElement((base, Point3D(base.x, base.y, base.z + style.stake_length)), "marker")


def _berms(face, style):
    half_width = style.berm_width / (2 * face.width)
    for t in _interior_fractions(abs(face.rise), style.berm_interval):
        elevation = face.point(t).z
        yield SlopePatternElement((
            face.point(max(0.0, t - half_width), elevation=elevation),
            face.point(min(1.0, t + half_width), elevation=elevation),
        ))


class SlopePatternGenerator:
    """샘플링한 코리더 사면 링크에 월드 좌표 표시 패턴을 생성한다."""

    @classmethod
    def generate_for_corridor(
        cls, corridor: Corridor, style: SlopePatternStyle | None = None, *,
        alignments: Mapping[str, Alignment], profiles: Mapping[str, Profile] | None = None,
        sample_frequency: float | None = None, baseline_name: str | None = None,
    ) -> SlopePatternCollection:
        """종단과 캔트를 반영하고, 연결 선은 영역 경계에서 끊는다."""
        style = style or SlopePatternStyle.hatch_style()
        if style.pattern_type is SlopePatternType.NONE:
            return SlopePatternCollection()
        if sample_frequency is not None and (not math.isfinite(sample_frequency) or sample_frequency <= 0):
            raise ValueError("sample_frequency must be finite and positive")
        if baseline_name is not None and all(baseline.name != baseline_name for baseline in corridor.baselines):
            raise ValueError(f"Missing baseline: {baseline_name}")

        patterns = []
        for region, baseline in corridor._regions_with_baselines(None, None, baseline_name):
            if region.assembly is None:
                continue
            alignment, profile = _resolve_baseline(corridor, region, alignments, profiles)
            frequency = sample_frequency
            if frequency is None and style.pattern_type is SlopePatternType.GRID:
                frequency = style.spacing_horizontal
            stations = iter(region.sample_stations(frequency))
            faces = _sample_faces(region, next(stations), alignment, profile)
            for station in stations:
                following = _sample_faces(region, station, alignment, profile)
                patterns.extend(cls._patterns(faces, following, region, baseline.name, alignment, style))
                faces = following
            patterns.extend(cls._patterns(faces, {}, region, baseline.name, alignment, style))
        return SlopePatternCollection(tuple(patterns))

    @staticmethod
    def _patterns(faces, following, region, baseline_name, alignment, style):
        for key, face in faces.items():
            match style.pattern_type:
                case SlopePatternType.HATCH:
                    elements = tuple(_hatches(face, following.get(key), style))
                case SlopePatternType.GRID:
                    elements = tuple(_grid(face, following.get(key), style))
                case SlopePatternType.STEPS:
                    elements = tuple(_steps(face, style, alignment, region))
                case SlopePatternType.STAKES:
                    elements = tuple(_stakes(face, style))
                case SlopePatternType.BERMS:
                    elements = tuple(_berms(face, style))
                case _:
                    continue
            if elements:
                yield SlopePattern(
                    region.name, face.station, key[0], elements, face.start, face.end,
                    slope=face.rise / face.width, style=style,
                    start_offset=face.start_offset, end_offset=face.end_offset, baseline_name=baseline_name,
                )
