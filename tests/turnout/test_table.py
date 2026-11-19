# tests/turnout/test_table.py
import math
import pytest
from myalignment.turnout.table import TurnoutTable
from myalignment.turnout.table_entry import TurnoutTableEntry, SwitchType
from myalignment.turnout.table_builder import TurnoutTableBuilder, StandardTurnoutCatalog
from myalignment.turnout.type import TurnoutSide


def test_entry_validation():
    with pytest.raises(ValueError):
        TurnoutTableEntry(name="", lead_length=30, radius=300)
    with pytest.raises(ValueError):
        TurnoutTableEntry(name="X", lead_length=0, radius=300)
    with pytest.raises(ValueError):
        TurnoutTableEntry(name="X", lead_length=30, radius=0)


def test_table_add_entry():
    e1 = TurnoutTableEntry(name="1/12", lead_length=30, radius=300)
    table = TurnoutTable(name="T1", entries=(e1,))
    assert len(table) == 1
    assert table.get("1/12") is e1
    assert table.get("1/9") is None


def test_table_duplicate_name():
    e1 = TurnoutTableEntry(name="1/12", lead_length=30, radius=300)
    e2 = TurnoutTableEntry(name="1/12", lead_length=35, radius=400)
    with pytest.raises(ValueError):
        TurnoutTable(name="T1", entries=(e1, e2))


def test_table_add():
    e1 = TurnoutTableEntry(name="1/12", lead_length=30, radius=300)
    table = TurnoutTable(name="T1", entries=(e1,))
    e2 = TurnoutTableEntry(name="1/9", lead_length=25, radius=200)
    table2 = table.add(e2)
    assert len(table) == 1   # 원본 불변
    assert len(table2) == 2


def test_table_update():
    e1 = TurnoutTableEntry(name="1/12", lead_length=30, radius=300)
    table = TurnoutTable(name="T1", entries=(e1,))
    e1_new = TurnoutTableEntry(name="1/12", lead_length=35, radius=350)
    table2 = table.update(e1_new)
    assert table2.get("1/12").lead_length == 35
    assert table.get("1/12").lead_length == 30   # 원본 불변


def test_table_remove():
    e1 = TurnoutTableEntry(name="1/12", lead_length=30, radius=300)
    e2 = TurnoutTableEntry(name="1/9", lead_length=25, radius=200)
    table = TurnoutTable(name="T1", entries=(e1, e2))
    table2 = table.remove("1/12")
    assert len(table2) == 1
    assert table2.get("1/9") is e2


def test_table_by_gauge():
    e1 = TurnoutTableEntry(name="1/12", lead_length=30, radius=300, gauge=1.435)
    e2 = TurnoutTableEntry(name="1/12_narrow", lead_length=30, radius=300, gauge=1.067)
    table = TurnoutTable(name="T1", entries=(e1, e2))
    standard = table.by_gauge(1.435)
    assert len(standard) == 1
    assert standard[0].name == "1/12"


def test_table_by_speed():
    e1 = TurnoutTableEntry(name="1/9", lead_length=25, radius=200, max_speed_branch=35)
    e2 = TurnoutTableEntry(name="1/12", lead_length=30, radius=300, max_speed_branch=50)
    e3 = TurnoutTableEntry(name="1/15", lead_length=35, radius=400, max_speed_branch=60)
    table = TurnoutTable(name="T1", entries=(e1, e2, e3))

    fast = table.by_speed_range(45)
    assert len(fast) == 2
    assert e1 not in fast


def test_builder():
    table = (
        TurnoutTableBuilder("T1")
        .add("1/12", frog_number=12, lead_length=30, radius=300)
        .add("1/15", frog_number=15, lead_length=35, radius=400)
        .build()
    )
    assert len(table) == 2
    assert table.get("1/12") is not None


def test_standard_catalog():
    korea = StandardTurnoutCatalog.korea_standard()
    assert len(korea) >= 3
    assert korea.get("1/12") is not None

    ktx = StandardTurnoutCatalog.ktx_standard()
    assert len(ktx) >= 2

    all_std = StandardTurnoutCatalog.all_standard()

    all_std = StandardTurnoutCatalog.all_standard()

    assert len(all_std) == 2
    assert sum(len(table) for table in all_std.tables) == len(korea) + len(ktx)
