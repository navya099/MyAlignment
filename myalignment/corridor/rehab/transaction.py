from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

from myalignment.corridor.rehab.edit_command import CorridorEditCommand
from myalignment.corridor.rehab.edit_operation import CorridorEditOperation as Operation
from myalignment.corridor.rehab.editor import CorridorEditor

if TYPE_CHECKING:
    from myalignment.assembly.assembly import Assembly
    from myalignment.corridor.corridor import Corridor
    from myalignment.target.mapping import TargetMapping


@dataclass(frozen=True, slots=True)
class EditHistory:
    """재실행과 되돌리기에 사용할 명령 및 편집 전후 스냅샷."""

    commands: tuple[CorridorEditCommand, ...] = ()
    snapshot_before: Corridor | None = None
    snapshot_after: Corridor | None = None

    def __post_init__(self):
        object.__setattr__(self, "commands", tuple(self.commands))


class CorridorTransaction:
    """컨텍스트가 정상 종료되면 편집 결과를 공개하는 일회용 트랜잭션."""

    def __init__(self, corridor: Corridor):
        self._original = corridor
        self._pending_commands: list[CorridorEditCommand] = []
        self._active = False
        self._result: Corridor | None = None

    def __enter__(self) -> Self:
        if self._active or self._result is not None:
            raise RuntimeError("Transaction has already been entered")
        self._active = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._active = False
        self._result = self._original
        if exc_type is None:
            self._result = CorridorEditor.execute_batch(self._original, self._pending_commands)

    def add_command(self, command: CorridorEditCommand) -> Self:
        """실행할 명령을 대기열에 추가한다."""
        if self._result is not None:
            raise RuntimeError("Transaction has already completed")
        self._pending_commands.append(command)
        return self

    def update_region(
        self, region_name: str, start_station: float | None = None, end_station: float | None = None, *,
        frequency: float | None = None, assembly: Assembly | None = None, targets: TargetMapping | None = None,
        baseline_name: str | None = None,
    ) -> Self:
        """측점 범위 등을 한 명령으로 변경한다."""
        return self.add_command(CorridorEditCommand(
            Operation.UPDATE_REGION, region_name, new_start_station=start_station, new_end_station=end_station,
            new_frequency=frequency, new_assembly=assembly, new_targets=targets, baseline_name=baseline_name,
        ))

    def replace_region_range(
        self, region_name: str, start_station: float | None = None, end_station: float | None = None, *,
        baseline_name: str | None = None,
    ) -> Self:
        """영역의 시작 또는 끝 측점을 바꾼다."""
        return self.add_command(CorridorEditCommand(
            Operation.REPLACE_REGION_RANGE, region_name, new_start_station=start_station,
            new_end_station=end_station, baseline_name=baseline_name,
        ))

    def update_frequency(self, region_name: str, new_frequency: float, *, baseline_name: str | None = None) -> Self:
        """영역의 표본 간격을 바꾼다."""
        return self.add_command(CorridorEditCommand(
            Operation.UPDATE_FREQUENCY, region_name, new_frequency=new_frequency, baseline_name=baseline_name,
        ))

    def update_assembly(self, region_name: str, new_assembly: Assembly, *, baseline_name: str | None = None) -> Self:
        """영역의 어셈블리를 교체한다."""
        return self.add_command(CorridorEditCommand(
            Operation.UPDATE_ASSEMBLY, region_name, new_assembly=new_assembly, baseline_name=baseline_name,
        ))

    def update_target(self, region_name: str, new_targets: TargetMapping, *, baseline_name: str | None = None) -> Self:
        """영역의 타깃 매핑을 교체한다."""
        return self.add_command(CorridorEditCommand(
            Operation.UPDATE_TARGET, region_name, new_targets=new_targets, baseline_name=baseline_name,
        ))

    def split_region(self, region_name: str, split_station: float, *, baseline_name: str | None = None) -> Self:
        """영역을 내부 측점에서 분할한다."""
        return self.add_command(CorridorEditCommand(
            Operation.SPLIT_REGION, region_name, split_station=split_station, baseline_name=baseline_name,
        ))

    def merge_regions(self, region_a: str, region_b: str, *, baseline_name: str | None = None) -> Self:
        """같은 기준선의 인접 영역 두 개를 병합한다."""
        return self.add_command(CorridorEditCommand(
            Operation.MERGE_REGION, region_a, other_region_name=region_b, baseline_name=baseline_name,
        ))

    def add_region(
        self, region_name: str, start_station: float, end_station: float, assembly: Assembly | None = None, *,
        frequency: float | None = None, targets: TargetMapping | None = None, baseline_name: str | None = None,
    ) -> Self:
        """지정한 범위의 새 영역을 추가한다."""
        return self.add_command(CorridorEditCommand(
            Operation.ADD_REGION, region_name, add_start_station=start_station, add_end_station=end_station,
            new_assembly=assembly, new_frequency=frequency, new_targets=targets, baseline_name=baseline_name,
        ))

    def delete_region(self, region_name: str, *, baseline_name: str | None = None) -> Self:
        """이름으로 영역을 삭제한다."""
        return self.add_command(CorridorEditCommand(
            Operation.DELETE_REGION, region_name, baseline_name=baseline_name,
        ))

    @property
    def result(self) -> Corridor:
        """완료 결과 또는 실패 시 원본을 반환한다."""
        if self._result is None:
            raise RuntimeError("Transaction has not completed")
        return self._result

    @property
    def commands(self) -> list[CorridorEditCommand]:
        """대기열의 복사본을 반환한다."""
        return list(self._pending_commands)

    @property
    def history(self) -> EditHistory:
        """완료된 트랜잭션의 원본, 결과와 시도한 명령을 반환한다."""
        return EditHistory(tuple(self._pending_commands), self._original, self.result)
