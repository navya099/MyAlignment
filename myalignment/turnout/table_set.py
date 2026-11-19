# turnout/table_set.py
from __future__ import annotations
from dataclasses import dataclass, field, replace
from myalignment.turnout.table import TurnoutTable


@dataclass(frozen=True, slots=True)
class TurnoutTableSet:
    """
    프로젝트 턴아웃 테이블 집합 (불변).

    여러 테이블을 이름으로 관리.
    """
    tables: tuple[TurnoutTable, ...] = field(default_factory=tuple)

    def __post_init__(self):
        names = [t.name for t in self.tables]
        if len(names) != len(set(names)):
            raise ValueError(f"테이블 이름 중복: {names}")

    def __len__(self) -> int:
        return len(self.tables)

    def __iter__(self):
        return iter(self.tables)

    def get(self, name: str) -> TurnoutTable | None:
        for t in self.tables:
            if t.name == name:
                return t
        return None

    def add(self, table: TurnoutTable) -> "TurnoutTableSet":
        if self.get(table.name) is not None:
            raise ValueError(f"테이블 '{table.name}' 이미 존재")
        return replace(self, tables=self.tables + (table,))

    def update(self, table: TurnoutTable) -> "TurnoutTableSet":
        new_tables = tuple(
            table if t.name == table.name else t
            for t in self.tables
        )
        if not any(t.name == table.name for t in self.tables):
            raise KeyError(f"테이블 '{table.name}' 없음")
        return replace(self, tables=new_tables)

    def remove(self, name: str) -> "TurnoutTableSet":
        return replace(
            self,
            tables=tuple(t for t in self.tables if t.name != name),
        )

    @property
    def total_entries(self) -> int:
        return sum(len(t) for t in self.tables)

    def __repr__(self) -> str:
        return (
            f"TurnoutTableSet(n={len(self.tables)}, "
            f"total_entries={self.total_entries})"
        )