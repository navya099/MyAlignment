from __future__ import annotations

from dataclasses import dataclass
import math

from myalignment.assembly.assembly import Assembly
from myalignment.corridor.rehab.edit_operation import CorridorEditOperation as Operation
from myalignment.target.mapping import TargetMapping


_UPDATE_FIELDS = ("new_start_station", "new_end_station", "new_frequency", "new_assembly", "new_targets")
_OPERATION_FIELDS = {
    Operation.UPDATE_REGION: _UPDATE_FIELDS,
    Operation.UPDATE_FREQUENCY: ("new_frequency",),
    Operation.UPDATE_ASSEMBLY: ("new_assembly",),
    Operation.UPDATE_TARGET: ("new_targets",),
    Operation.SPLIT_REGION: ("split_station",),
    Operation.MERGE_REGION: ("other_region_name",),
    Operation.ADD_REGION: ("add_start_station", "add_end_station", "new_frequency", "new_assembly", "new_targets"),
    Operation.DELETE_REGION: (),
    Operation.REPLACE_REGION_RANGE: ("new_start_station", "new_end_station"),
}
_EDIT_FIELDS = (*_UPDATE_FIELDS, "split_station", "add_start_station", "add_end_station", "other_region_name")


@dataclass(frozen=True, slots=True)
class CorridorEditCommand:
    """영역 이름과 작업별 인수를 담는 불변 편집 명령."""

    operation: Operation
    region_name: str = ""
    new_start_station: float | None = None
    new_end_station: float | None = None
    new_frequency: float | None = None
    new_assembly: Assembly | None = None
    new_targets: TargetMapping | None = None
    split_station: float | None = None
    add_start_station: float | None = None
    add_end_station: float | None = None
    comment: str = ""
    baseline_name: str | None = None
    other_region_name: str | None = None

    def __post_init__(self):
        op = self.operation
        if not isinstance(op, Operation):
            raise ValueError("operation must be a CorridorEditOperation")
        if not self.region_name.strip() and (self.region_name or op is not Operation.ADD_REGION):
            raise ValueError("region_name is required")
        if self.baseline_name is not None and not self.baseline_name.strip():
            raise ValueError("baseline_name must be nonempty")
        for name in _EDIT_FIELDS:
            if getattr(self, name) is not None and name not in _OPERATION_FIELDS[op]:
                raise ValueError(f"{op.name} does not accept {name}")
        for name in ("new_start_station", "new_end_station", "split_station", "add_start_station", "add_end_station"):
            value = getattr(self, name)
            if value is not None and not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.new_frequency is not None and (not math.isfinite(self.new_frequency) or self.new_frequency <= 0):
            raise ValueError("new_frequency must be finite and positive")
        if self.new_assembly is not None and not isinstance(self.new_assembly, Assembly):
            raise TypeError("new_assembly must be an Assembly")
        if self.new_targets is not None and not isinstance(self.new_targets, TargetMapping):
            raise TypeError("new_targets must be a TargetMapping")

        required = {
            Operation.UPDATE_FREQUENCY: ("new_frequency",),
            Operation.UPDATE_ASSEMBLY: ("new_assembly",),
            Operation.UPDATE_TARGET: ("new_targets",),
            Operation.SPLIT_REGION: ("split_station",),
            Operation.ADD_REGION: ("add_start_station", "add_end_station"),
        }
        for name in required.get(op, ()):
            if getattr(self, name) is None:
                raise ValueError(f"{op.name} requires {name}")
        if op is Operation.REPLACE_REGION_RANGE and self.new_start_station is None and self.new_end_station is None:
            raise ValueError("REPLACE_REGION_RANGE requires a new start or end station")
        if op is Operation.MERGE_REGION:
            self._merge_names()

    def _merge_names(self) -> tuple[str, str]:
        if self.other_region_name is not None:
            names = (self.region_name, self.other_region_name)
        else:
            names = tuple(name.strip() for name in self.region_name.split(","))
        if len(names) != 2 or not all(name.strip() for name in names) or names[0] == names[1]:
            raise ValueError("MERGE_REGION requires two different region names")
        return names[0], names[1]
