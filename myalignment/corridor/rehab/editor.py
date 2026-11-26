from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
import math
from typing import TYPE_CHECKING

from myalignment.assembly.assembly import Assembly
from myalignment.corridor.feature_line_manager import CorridorFeatureLineManager
from myalignment.corridor.region import CorridorRegion
from myalignment.corridor.rehab.edit_operation import CorridorEditOperation as Operation
from myalignment.corridor.surface_set import CorridorSurfaceSet

if TYPE_CHECKING:
    from myalignment.corridor.corridor import Corridor
    from myalignment.corridor.rehab.edit_command import CorridorEditCommand


def _find(corridor, name, baseline_name):
    matches = []
    for index, region in enumerate(corridor.regions):
        if region.name != name:
            continue
        if baseline_name is not None and region.baseline_name not in (None, baseline_name):
            continue
        baseline = corridor.baseline_for_region(region)
        if baseline_name is None or (baseline is not None and baseline.name == baseline_name):
            matches.append((index, region, baseline))
    if not matches:
        raise ValueError(f"Region {name!r} does not exist")
    if len(matches) > 1:
        raise ValueError(f"Region {name!r} is ambiguous. Specify baseline_name or use a unique region name.")
    return matches[0]


def _replace_regions(corridor, remove, additions):
    remaining = [region for index, region in enumerate(corridor.regions) if index not in remove]
    for region, baseline in additions:
        if baseline is not None and region.baseline_name is None and len(corridor.baselines) > 1:
            region = replace(region, baseline_name=baseline.name)
        if corridor.baseline_for_region(region) != baseline:
            raise ValueError(f"Region {region.name!r} would change baseline")
        for other in remaining:
            overlaps = region.start_station < other.end_station and other.start_station < region.end_station
            identical_range = (region.start_station, region.end_station) == (other.start_station, other.end_station)
            if region.name != other.name and not overlaps and not identical_range:
                continue
            if corridor.baseline_for_region(other) != baseline:
                continue
            if region.name == other.name:
                raise ValueError(f"Region {region.name!r} already exists on this baseline")
            raise ValueError(f"Regions {region.name!r} and {other.name!r} overlap on this baseline")
        remaining.append(region)
    regions = tuple(sorted(remaining, key=lambda region: region.start_station))
    return replace(corridor, regions=regions, surfaces=CorridorSurfaceSet(), feature_lines=CorridorFeatureLineManager())


def _add_region(corridor, command):
    region = CorridorRegion(
        name=command.region_name or "NewRegion",
        start_station=command.add_start_station, end_station=command.add_end_station,
        baseline_name=command.baseline_name,
    )
    baseline = corridor.baseline_for_region(region)
    assembly = command.new_assembly
    mirrored = False
    if assembly is None:
        for candidate in corridor.regions:
            if isinstance(candidate.assembly, Assembly) and corridor.baseline_for_region(candidate) == baseline:
                assembly = candidate.assembly
                mirrored = candidate._mirrored
                break
        if assembly is None:
            raise ValueError("ADD_REGION requires an assembly when the baseline has none to reuse")
    changes = {"assembly": assembly, "_mirrored": mirrored}
    if command.new_frequency is not None:
        changes["frequency"] = command.new_frequency
    if command.new_targets is not None:
        changes["target_mapping"] = command.new_targets
    return _replace_regions(corridor, (), ((replace(region, **changes), baseline),))


def _merge_regions(corridor, command):
    first, second = command._merge_names()
    selected = [_find(corridor, name, command.baseline_name) for name in (first, second)]
    (a_index, a, a_baseline), (b_index, b, b_baseline) = sorted(
        selected, key=lambda item: (item[1].start_station, item[1].end_station),
    )
    if a_baseline != b_baseline:
        raise ValueError("MERGE_REGION requires the same baseline")
    if not math.isclose(a.end_station, b.start_station, rel_tol=0, abs_tol=1e-8):
        raise ValueError("MERGE_REGION requires adjacent regions without a gap or overlap")
    if a.cant_curve != b.cant_curve or a._mirrored != b._mirrored:
        raise ValueError("MERGE_REGION requires compatible cant and assembly orientation")
    if a.context_provider != b.context_provider:
        raise ValueError("MERGE_REGION requires the same section context provider")
    if a._binding_station_map != b._binding_station_map:
        raise ValueError("MERGE_REGION requires compatible binding stations")
    merged = replace(a, name=f"{a.name}_merged", end_station=b.end_station)
    return _replace_regions(corridor, (a_index, b_index), ((merged, a_baseline),))


class CorridorEditor:
    """영역 변경을 검증하고 원본과 독립된 코리더를 반환한다."""

    @staticmethod
    def execute(corridor: Corridor, command: CorridorEditCommand) -> Corridor:
        """명령 하나를 적용한다."""
        operation = command.operation
        if operation is Operation.ADD_REGION:
            return _add_region(corridor, command)
        if operation is Operation.MERGE_REGION:
            return _merge_regions(corridor, command)
        index, region, baseline = _find(corridor, command.region_name, command.baseline_name)
        if operation is Operation.DELETE_REGION:
            return _replace_regions(corridor, (index,), ())
        if operation is Operation.SPLIT_REGION:
            split = command.split_station
            if not region.start_station < split < region.end_station:
                raise ValueError("split_station must be strictly inside the region")
            before = replace(region, name=f"{region.name}_A", end_station=split)
            after = replace(region, name=f"{region.name}_B", start_station=split)
            return _replace_regions(corridor, (index,), ((before, baseline), (after, baseline)))

        updates = {
            "start_station": command.new_start_station,
            "end_station": command.new_end_station,
            "frequency": command.new_frequency,
            "assembly": command.new_assembly,
            "target_mapping": command.new_targets,
        }
        updated = replace(region, **{name: value for name, value in updates.items() if value is not None})
        if updated == region:
            return corridor
        return _replace_regions(corridor, (index,), ((updated, baseline),))

    @classmethod
    def execute_batch(cls, corridor: Corridor, commands: Iterable[CorridorEditCommand]) -> Corridor:
        """명령을 순서대로 적용하고 모두 성공한 결과를 반환한다."""
        result = corridor
        for command in commands:
            result = cls.execute(result, command)
        return result
