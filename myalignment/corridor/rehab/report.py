from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from myalignment.corridor.corridor import Corridor
    from myalignment.corridor.rehab.edit_command import CorridorEditCommand
    from myalignment.corridor.rehab.transaction import EditHistory


def _regions_by_key(corridor):
    groups = defaultdict(list)
    for region in corridor.regions:
        baseline = corridor.baseline_for_region(region)
        baseline_name = baseline.name if baseline else None
        groups[baseline_name, region.name].append(region)
    return groups


@dataclass(frozen=True, slots=True)
class CorridorRehabReport:
    """편집 전후 스냅샷과 적용을 시도한 명령을 비교한다."""

    original: Corridor
    modified: Corridor
    commands: tuple[CorridorEditCommand, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "commands", tuple(self.commands))

    @classmethod
    def from_history(cls, history: EditHistory) -> CorridorRehabReport:
        """트랜잭션 이력에서 보고서를 만든다."""
        if history.snapshot_before is None or history.snapshot_after is None:
            raise ValueError("Both corridor snapshots are required")
        return cls(history.snapshot_before, history.snapshot_after, history.commands)

    @property
    def region_count_before(self) -> int:
        return len(self.original.regions)

    @property
    def region_count_after(self) -> int:
        return len(self.modified.regions)

    def _changes(self):
        before = _regions_by_key(self.original)
        after = _regions_by_key(self.modified)
        owners = defaultdict(set)
        for baseline, name in before.keys() | after.keys():
            owners[name].add(baseline)

        def labels(keys):
            return sorted(f"{baseline} / {name}" if len(owners[name]) > 1 else name for baseline, name in keys)

        return (
            labels(after.keys() - before.keys()),
            labels(before.keys() - after.keys()),
            labels(key for key in before.keys() & after.keys() if before[key] != after[key]),
        )

    @property
    def added_regions(self) -> list[str]:
        return self._changes()[0]

    @property
    def removed_regions(self) -> list[str]:
        return self._changes()[1]

    @property
    def modified_regions(self) -> list[str]:
        return self._changes()[2]

    def to_text(self) -> str:
        """영역 수와 변경 목록을 텍스트로 출력한다."""
        lines = ["Corridor Rehab Report", f"Regions {self.region_count_before} → {self.region_count_after}"]
        if self.commands:
            lines.append(f"Commands ({len(self.commands)})")
            for command in self.commands:
                description = f"{command.operation.value} {command.region_name or 'NewRegion'}"
                if command.other_region_name is not None:
                    description += f", {command.other_region_name}"
                if command.baseline_name:
                    description += f" ({command.baseline_name})"
                if command.comment:
                    description += f" — {command.comment}"
                lines.append(f"  - {description}")
        for label, names in zip(("Added", "Removed", "Modified"), self._changes()):
            if names:
                lines.append(f"{label}: {', '.join(names)}")
        return "\n".join(lines)
