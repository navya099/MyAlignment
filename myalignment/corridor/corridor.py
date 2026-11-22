# corridor/corridor.py
from __future__ import annotations
from dataclasses import dataclass, field, replace
from collections.abc import Mapping
from typing import Iterator, TYPE_CHECKING

from myalignment.corridor.baseline import CorridorBaseline
from myalignment.corridor.region import CorridorRegion
from myalignment.corridor.surface_set import CorridorSurfaceSet

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.corridor.surface_builder import CorridorSurfaceSpec
    from myalignment.profile.profile import Profile
    from myalignment.surface.tin_surface import TinSurface


@dataclass(frozen=True, slots=True)
class Corridor:
    """
    코리더 (불변).

    C3D의 Corridor와 호환.
    - 기준선(Baseline) + 영역(Region) + 어셈블리(Assembly) 조합.
    - 3D 표면/피처라인/수량 산출의 기반.
    """
    name: str = ""
    baselines: tuple[CorridorBaseline, ...] = field(default_factory=tuple)
    regions: tuple[CorridorRegion, ...] = field(default_factory=tuple)

    surfaces: CorridorSurfaceSet = field(default_factory=CorridorSurfaceSet)

    def __post_init__(self):
        # 영역 정렬 검증
        for i in range(len(self.regions) - 1):
            if self.regions[i].start_station > self.regions[i + 1].start_station:
                raise ValueError(f"영역 순서 오류: [{i}]")
        for region in self.regions:
            if region.baseline_name is not None:
                self.baseline_for_region(region)

    # ---- 조회 ----
    @property
    def start_station(self) -> float:
        return self.regions[0].start_station if self.regions else 0.0

    @property
    def end_station(self) -> float:
        return max((region.end_station for region in self.regions), default=0.0)

    @property
    def length(self) -> float:
        return self.end_station - self.start_station if self.regions else 0.0

    def baseline_for_region(self, region: CorridorRegion) -> CorridorBaseline | None:
        """명시한 기준선 또는 영역 전체를 포함하는 유일한 기준선을 반환한다."""
        if not self.baselines and region.baseline_name is None:
            return None
        candidates = [
            baseline for baseline in self.baselines
            if (region.baseline_name is None or baseline.name == region.baseline_name)
            and baseline.start_station <= region.start_station
            and region.end_station <= baseline.end_station
        ]
        if len(candidates) != 1:
            name = f" {region.baseline_name!r}" if region.baseline_name is not None else ""
            raise ValueError(f"{region.name}: expected exactly one baseline{name} covering the region")
        return candidates[0]

    def region_at(
        self, station: float, *, alignment_name: str | None = None,
        baseline_name: str | None = None,
    ) -> CorridorRegion | None:
        """측점에 해당하는 영역을 기준선이나 선형으로 구분한다."""
        selected = list(self._regions_with_baselines(station, alignment_name, baseline_name))
        if len({baseline for _, baseline in selected}) > 1:
            raise ValueError(f"STA {station}: 여러 기준선이 겹칩니다. baseline_name을 지정하세요.")
        return selected[0][0] if selected else None

    def _regions_with_baselines(
        self, station: float | None, alignment_name: str | None, baseline_name: str | None,
    ) -> Iterator[tuple[CorridorRegion, CorridorBaseline | None]]:
        for region in self.regions:
            if station is not None and not region.start_station <= station <= region.end_station:
                continue
            baseline = self.baseline_for_region(region)
            if baseline_name is not None and (baseline is None or baseline.name != baseline_name):
                continue
            if alignment_name is not None and baseline is not None and baseline.alignment_name != alignment_name:
                continue
            yield region, baseline

    def region_by_name(self, name: str) -> CorridorRegion | None:
        for r in self.regions:
            if r.name == name:
                return r
        return None

    def total_surface_area(self) -> float:
        """총 표면적 (근사) — 영역 길이 × 어셈블리 폭."""
        # 실제로는 어셈블리 폭 정보 필요
        return sum(r.length for r in self.regions)

    # ---- 불변 변환 ----
    def add_region(self, region: CorridorRegion) -> "Corridor":
        """새 영역 추가한 새 코리더."""
        new_list = list(self.regions) + [region]
        new_list.sort(key=lambda r: r.start_station)
        return replace(self, regions=tuple(new_list))

    def build_surface(
        self,
        spec: CorridorSurfaceSpec,
        *,
        alignments: Mapping[str, Alignment],
        profiles: Mapping[str, Profile] | None = None,
    ) -> TinSurface:
        """연결된 선형과 종단의 월드 좌표에서 표면을 추출한다."""
        from myalignment.corridor.surface_builder import CorridorSurfaceBuilder

        return CorridorSurfaceBuilder.build(self, spec, alignments=alignments, profiles=profiles)

    def with_surface(self, surface: TinSurface) -> Corridor:
        return replace(self, surfaces=self.surfaces.add(surface))

    def __repr__(self) -> str:
        return (
            f"Corridor('{self.name}', "
            f"baselines={len(self.baselines)}, "
            f"regions={len(self.regions)}, "
            f"len={self.length:.1f}m)"
        )

    def cross_section_at(
        self, station: float, *, alignment_name: str | None = None, baseline_name: str | None = None,
    ) -> tuple[tuple, tuple]:
        """측점의 횡단면."""
        region = self.region_at(station, alignment_name=alignment_name, baseline_name=baseline_name)
        if region is None:
            return (), ()
        return region.cross_section_at(station)

    def sample_cross_sections(
        self, *, alignment_name: str | None = None, baseline_name: str | None = None,
    ) -> dict[float, tuple[tuple, tuple]]:
        """선택 영역의 횡단면 샘플."""
        result = {}
        owners = {}
        for region, baseline in self._regions_with_baselines(None, alignment_name, baseline_name):
            for sta in region.sample_stations():
                if sta in owners and owners[sta] != baseline:
                    raise ValueError(f"STA {sta}: 여러 기준선이 겹칩니다. baseline_name을 지정하세요.")
                owners[sta] = baseline
                result[sta] = region.cross_section_at(sta)
        return result
