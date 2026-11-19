# turnout/table.py
from __future__ import annotations
from dataclasses import dataclass, field, replace
from myalignment.turnout.table_entry import TurnoutTableEntry


@dataclass(frozen=True, slots=True)
class TurnoutTable:
    """
    턴아웃 테이블 (불변).

    C3D Turnout Table과 호환.
    - 이름으로 턴아웃 유형 관리.
    - 편집/삭제/보완 가능 (불변 → 새 테이블).
    - CSV/XML 임포트/익스포트.
    """
    name: str = "Turnout Table"
    entries: tuple[TurnoutTableEntry, ...] = field(default_factory=tuple)

    def __post_init__(self):
        # 이름 중복 검사
        names = [e.name for e in self.entries]
        if len(names) != len(set(names)):
            duplicates = [n for n in names if names.count(n) > 1]
            raise ValueError(f"턴아웃 이름 중복: {set(duplicates)}")

    # ================================================================
    # 조회
    # ================================================================
    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self):
        return iter(self.entries)

    def get(self, name: str) -> TurnoutTableEntry | None:
        """이름으로 항목 조회."""
        for e in self.entries:
            if e.name == name:
                return e
        return None

    def get_or_raise(self, name: str) -> TurnoutTableEntry:
        """이름으로 항목 조회 (없으면 예외)."""
        e = self.get(name)
        if e is None:
            raise KeyError(f"턴아웃 유형 '{name}'이 테이블에 없음")
        return e

    def by_gauge(self, gauge: float, tol: float = 1e-3) -> tuple[TurnoutTableEntry, ...]:
        """궤간별 항목."""
        return tuple(e for e in self.entries if e.is_compatible_with_gauge(gauge, tol))

    def by_speed_range(self, min_branch_speed: float) -> tuple[TurnoutTableEntry, ...]:
        """최소 분기 속도 이상 항목."""
        return tuple(e for e in self.entries if e.max_speed_branch >= min_branch_speed)

    def names(self) -> tuple[str, ...]:
        """모든 이름."""
        return tuple(e.name for e in self.entries)

    # ================================================================
    # 편집 (불변)
    # ================================================================
    def add(self, entry: TurnoutTableEntry) -> "TurnoutTable":
        """항목 추가한 새 테이블."""
        if self.get(entry.name) is not None:
            raise ValueError(f"'{entry.name}' 이미 존재")
        return replace(
            self,
            entries=self.entries + (entry,),
        )

    def update(self, entry: TurnoutTableEntry) -> "TurnoutTable":
        """항목 교체한 새 테이블."""
        new_entries = tuple(
            entry if e.name == entry.name else e
            for e in self.entries
        )
        if not any(e.name == entry.name for e in self.entries):
            raise KeyError(f"'{entry.name}'이 테이블에 없음")
        return replace(self, entries=new_entries)

    def remove(self, name: str) -> "TurnoutTable":
        """항목 삭제한 새 테이블."""
        if self.get(name) is None:
            raise KeyError(f"'{name}'이 테이블에 없음")
        return replace(
            self,
            entries=tuple(e for e in self.entries if e.name != name),
        )

    def replace_all(self, entries: list[TurnoutTableEntry]) -> "TurnoutTable":
        """전체 항목 교체."""
        return TurnoutTable(name=self.name, entries=tuple(entries))

    def rename(self, new_name: str) -> "TurnoutTable":
        return replace(self, name=new_name)

    # ================================================================
    # CSV 임포트/익스포트
    # ================================================================
    def to_csv(self, path: str) -> None:
        """CSV로 익스포트."""
        import csv
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'name', 'description', 'frog_number', 'lead_length', 'radius',
                'switch_type', 'max_speed_main', 'max_speed_branch',
                'gauge', 'default_side',
            ])
            for e in self.entries:
                writer.writerow([
                    e.name, e.description, e.frog_number, e.lead_length, e.radius,
                    e.switch_type.value, e.max_speed_main, e.max_speed_branch,
                    e.gauge, e.default_side.value,
                ])

    @classmethod
    def from_csv(cls, path: str, name: str = "Turnout Table") -> "TurnoutTable":
        """CSV에서 임포트."""
        import csv
        from myalignment.turnout.type import TurnoutSide
        from myalignment.turnout.table_entry import SwitchType

        entries = []
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                entries.append(
                    TurnoutTableEntry(
                        name=row['name'],
                        description=row.get('description', ''),
                        frog_number=float(row['frog_number']),
                        lead_length=float(row['lead_length']),
                        radius=float(row['radius']),
                        switch_type=SwitchType(row['switch_type']),
                        max_speed_main=float(row['max_speed_main']),
                        max_speed_branch=float(row['max_speed_branch']),
                        gauge=float(row['gauge']),
                        default_side=TurnoutSide(row['default_side']),
                    )
                )
        return cls(name=name, entries=tuple(entries))

    def __repr__(self) -> str:
        return f"TurnoutTable('{self.name}', n={len(self.entries)})"