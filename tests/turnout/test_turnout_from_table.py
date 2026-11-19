# tests/turnout/test_turnout_from_table.py
import pytest

from myalignment.turnout.table_builder import StandardTurnoutCatalog
from myalignment.turnout.turnout import Turnout
from myalignment.turnout.type import TurnoutSide, TurnoutType


def test_turnout_from_table():
    table = StandardTurnoutCatalog.korea_standard()
    t = Turnout.from_table(
        name="T1",
        table=table,
        entry_name="1/12",
        source_alignment_name="본선1",
        branch_alignment_name="분기선",
        station_on_source=100,
    )
    assert t.turnout_type.name == "1/12"
    assert t.table_name == "한국철도표준"
    assert t.table_entry_name == "1/12"
    assert t.side == TurnoutSide.RIGHT   # 기본값


def test_turnout_from_table_invalid_name():
    table = StandardTurnoutCatalog.korea_standard()
    with pytest.raises(KeyError):
        Turnout.from_table(
            name="T1",
            table=table,
            entry_name="존재하지않음",
            source_alignment_name="A",
            branch_alignment_name="B",
            station_on_source=0,
        )

def test_turnout_legacy_positional_constructor():
    tt = TurnoutType(
        name="1/12",
        frog_number=12,
        lead_length=17,
        radius=373,
    )

    t = Turnout(
        "T1", tt, "본선1", "분기선1",
        100.0, TurnoutSide.LEFT
    )

    assert t.source_alignment_name == "본선1"
    assert t.branch_alignment_name == "분기선1"
    assert t.station_on_source == 100.0
    assert t.side == TurnoutSide.LEFT
    assert t.table_name == ""