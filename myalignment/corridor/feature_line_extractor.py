from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from itertools import chain
import math
from typing import TYPE_CHECKING

from myalignment.corridor.corridor_feature_line import CorridorFeatureLine, FeatureLinePoint
from myalignment.corridor.surface_builder import _resolve_baseline
from myalignment.render.primitives_3d import Point3D

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.corridor.corridor import Corridor
    from myalignment.corridor.feature_line_spec import CorridorFeatureLineSpec
    from myalignment.profile.profile import Profile


_TOLERANCE = 1e-8


def _select(spec, points, links):
    if spec.extraction_method == "offset":
        heights = [p.z for p in points if abs(p.x - spec.offset) <= _TOLERANCE]
        for link in links:
            a, b = link.start, link.end
            if min(a.x, b.x) < spec.offset < max(a.x, b.x):
                fraction = (spec.offset - a.x) / (b.x - a.x)
                heights.append(a.z + fraction * (b.z - a.z))
        return (spec.offset, max(heights)) if heights else None

    if spec.extraction_method == "point_code":
        candidates = ((p.x, p.z) for p in points if p.code == spec.point_code)
    else:
        candidates = (_link_point(link, spec) for link in links if link.code == spec.link_code)

    if spec.side == "left":
        return min((p for p in candidates if p[0] < -_TOLERANCE), key=lambda p: (p[0], -p[1]), default=None)
    if spec.side == "right":
        return max((p for p in candidates if p[0] > _TOLERANCE), key=lambda p: (p[0], p[1]), default=None)
    return min(candidates, key=lambda p: (abs(p[0]), -p[1], p[0]), default=None)


def _link_point(link, spec):
    if spec.use_start and spec.use_end:
        return (link.start.x + link.end.x) / 2, (link.start.z + link.end.z) / 2
    point = link.start if spec.use_start else link.end
    return point.x, point.z


def _append_runs(existing, runs, region_start):
    if existing and runs and runs[0][0].station == region_start:
        a, b = existing[-1][-1], runs[0][0]
        if abs(a.station - b.station) <= _TOLERANCE and a.point.distance_to(b.point) <= _TOLERANCE:
            existing[-1].extend(runs[0][1:])
            runs = runs[1:]
    existing.extend(runs)


class CorridorFeatureLineExtractor:
    """코리더 횡단면의 지정 위치를 월드 좌표 종방향 선으로 추출한다."""

    @classmethod
    def extract(
        cls, corridor: Corridor, spec: CorridorFeatureLineSpec, *, alignments: Mapping[str, Alignment],
        profiles: Mapping[str, Profile] | None = None, sample_frequency: float | None = None,
        baseline_name: str | None = None,
    ) -> CorridorFeatureLine:
        """한 사양을 추출한다."""
        return cls.extract_multiple(
            corridor, (spec,), alignments=alignments, profiles=profiles,
            sample_frequency=sample_frequency, baseline_name=baseline_name,
        )[0]

    @classmethod
    def extract_multiple(
        cls, corridor: Corridor, specs: Sequence[CorridorFeatureLineSpec], *,
        alignments: Mapping[str, Alignment], profiles: Mapping[str, Profile] | None = None,
        sample_frequency: float | None = None, baseline_name: str | None = None,
    ) -> list[CorridorFeatureLine]:
        """각 횡단면을 한 번 샘플링해 사양별로 추출하고 기하 단절부를 보존한다."""
        if sample_frequency is not None and (not math.isfinite(sample_frequency) or sample_frequency <= 0):
            raise ValueError("sample_frequency must be finite and positive")
        if baseline_name is not None and all(b.name != baseline_name for b in corridor.baselines):
            raise ValueError(f"Missing baseline: {baseline_name}")
        if not specs:
            return []
        by_spec = [defaultdict(list) for _ in specs]
        for region, baseline in corridor._regions_with_baselines(None, None, baseline_name):
            if region.assembly is None:
                continue

            alignment, profile = _resolve_baseline(corridor, region, alignments, profiles)
            runs_by_spec = [[] for _ in specs]
            active = [[] for _ in specs]
            for station in region.sample_stations(sample_frequency):
                points, links = region.cross_section_at(station)
                # 링크에 남아 있는 코드를 포함한다. 어셈블리는 같은 위치에 있는 점을 병합한다.
                coded_points = tuple(dict.fromkeys(chain(points, (p for link in links for p in (link.start, link.end)))))
                grade = profile.elevation_at(station) if profile is not None else 0.0
                for i, spec in enumerate(specs):
                    selected = _select(spec, coded_points, links)
                    if selected is None:
                        if active[i]:
                            runs_by_spec[i].append(active[i])
                            active[i] = []
                        continue
                    offset, local_z = selected
                    xy = alignment.point_at(station, offset)
                    active[i].append(FeatureLinePoint(station, Point3D(xy.x, xy.y, grade + local_z)))
            for i, runs in enumerate(runs_by_spec):
                if active[i]:
                    runs.append(active[i])
                _append_runs(by_spec[i][baseline], runs, region.start_station)

        results = []
        for spec, groups in zip(specs, by_spec):
            points = []
            breaks = []
            for run in chain.from_iterable(groups.values()):
                if points:
                    breaks.append(len(points))
                points.extend(run)
            results.append(CorridorFeatureLine(spec.name, tuple(points), spec, tuple(breaks)))
        return results
