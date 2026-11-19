# tests/turnout/test_csv.py
import tempfile
import os
from myalignment.turnout.table import TurnoutTable
from myalignment.turnout.table_entry import TurnoutTableEntry


def test_csv_round_trip():
    e1 = TurnoutTableEntry(name="1/12", lead_length=30, radius=300, max_speed_main=100, max_speed_branch=50)
    e2 = TurnoutTableEntry(name="1/15", lead_length=35, radius=400)
    table = TurnoutTable(name="T1", entries=(e1, e2))

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        path = f.name

    try:
        table.to_csv(path)
        loaded = TurnoutTable.from_csv(path)
        assert len(loaded) == 2
        assert loaded.get("1/12").lead_length == 30
        assert loaded.get("1/12").max_speed_main == 100
    finally:
        os.unlink(path)
