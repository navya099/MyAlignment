# turnout/table_builder.py
from __future__ import annotations
from myalignment.turnout.table import TurnoutTable
from myalignment.turnout.table_entry import TurnoutTableEntry, SwitchType
from myalignment.turnout.table_set import TurnoutTableSet
from myalignment.turnout.type import TurnoutSide


class TurnoutTableBuilder:
    """TurnoutTable 선언적 빌더."""

    def __init__(self, name: str = "Turnout Table"):
        self._name = name
        self._entries: list[TurnoutTableEntry] = []

    def add(
            self,
            name: str,
            frog_number: float,
            lead_length: float,
            radius: float,
            max_speed_main: float = 0.0,
            max_speed_branch: float = 0.0,
            switch_type: SwitchType = SwitchType.SINGLE,
            gauge: float = 1.435,
            default_side: TurnoutSide = TurnoutSide.RIGHT,
            description: str = "",
    ) -> "TurnoutTableBuilder":
        self._entries.append(
            TurnoutTableEntry(
                name=name,
                description=description,
                frog_number=frog_number,
                lead_length=lead_length,
                radius=radius,
                switch_type=switch_type,
                max_speed_main=max_speed_main,
                max_speed_branch=max_speed_branch,
                gauge=gauge,
                default_side=default_side,
            )
        )
        return self

    def add_entry(self, entry: TurnoutTableEntry) -> "TurnoutTableBuilder":
        self._entries.append(entry)
        return self

    def build(self) -> TurnoutTable:
        return TurnoutTable(name=self._name, entries=tuple(self._entries))


# ================================================================
# 표준 카탈로그 (C3D 기본)
# ================================================================
class StandardTurnoutCatalog:
    """
    표준 턴아웃 카탈로그.

    C3D 기본 턴아웃 유형 제공.
    """

    @staticmethod
    def korea_standard() -> TurnoutTable:
        """
        한국 철도 표준 턴아웃 (예시).

        실제 표준은 KR C-08080 참조.
        """
        return (
            TurnoutTableBuilder("한국철도표준")
            .add("1/9", frog_number=9, lead_length=25, radius=200,
                 max_speed_main=80, max_speed_branch=35)
            .add("1/12", frog_number=12, lead_length=30, radius=300,
                 max_speed_main=100, max_speed_branch=50)
            .add("1/15", frog_number=15, lead_length=35, radius=400,
                 max_speed_main=120, max_speed_branch=60)
            .add("1/18", frog_number=18, lead_length=40, radius=600,
                 max_speed_main=150, max_speed_branch=80)
            .add("1/20", frog_number=20, lead_length=45, radius=800,
                 max_speed_main=170, max_speed_branch=90)
            .build()
        )

    @staticmethod
    def ktx_standard() -> TurnoutTable:
        """KTX 표준 (고속)."""
        return (
            TurnoutTableBuilder("KTX표준")
            .add("1/18", frog_number=18, lead_length=42, radius=800,
                 max_speed_main=300, max_speed_branch=80)
            .add("1/25", frog_number=25, lead_length=55, radius=1200,
                 max_speed_main=300, max_speed_branch=120)
            .add("1/32", frog_number=32, lead_length=70, radius=1800,
                 max_speed_main=300, max_speed_branch=160)
            .build()
        )

    @staticmethod
    def all_standard() -> TurnoutTableSet:
        """모든 표준 통합."""
        korea = StandardTurnoutCatalog.korea_standard()
        ktx = StandardTurnoutCatalog.ktx_standard()

        tables = TurnoutTableSet(
            tables=(korea, ktx)
        )
        return tables