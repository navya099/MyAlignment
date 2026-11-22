from dataclasses import replace

import pytest

from myalignment.featureline.builder import FeatureLineBuilder
from myalignment.featureline.set import FeatureLineSet
from myalignment.rail.rail_alignment import RailAlignment
from myalignment.turnout.table import TurnoutTable
from myalignment.turnout.table_entry import TurnoutTableEntry
from myalignment.turnout.table_set import TurnoutTableSet


def test_feature_line_set_filters_sites_and_sums_closed_3d_length():
    closed = (
        FeatureLineBuilder("Boundary").with_site("North").close()
        .add_coords([(0, 0, 0), (3, 0, 4), (3, 4, 4)]).build()
    )
    other = (
        FeatureLineBuilder("Toe").with_site("South")
        .add_coords([(0, 0, 0), (0, 0, 2)]).build()
    )
    original = FeatureLineSet((closed,))
    both = original.add(other)
    assert tuple(both) == (closed, other)
    assert both.by_site("South") == (other,)
    assert both.by_site("Missing") == ()
    assert both.total_length_3d() == pytest.approx(11 + 41 ** .5)
    assert both.remove("Toe") == original
    assert len(original) == 1


def test_turnout_tables_are_immutable_and_rail_lookup_uses_updated_entries():
    entry = TurnoutTableEntry("1/12", frog_number=12, lead_length=30, radius=300)
    table = TurnoutTable("Main", (entry,))
    original = TurnoutTableSet().add(table)
    updated_entry = entry.with_speed(100, 40)
    updated = original.update(table.update(updated_entry))
    rail = RailAlignment(turnout_tables=updated)

    assert rail.turnout_entry("Main", "1/12") is updated_entry
    assert rail.turnout_entry("Main", "Missing") is None
    assert rail.turnout_entry("Missing", "1/12") is None
    assert original.total_entries == updated.total_entries == 1
    assert tuple(original) == (table,)
    assert original.get("Main").get("1/12").max_speed_branch == 0
    assert len(updated.remove("Main")) == 0
    with pytest.raises(ValueError):
        original.add(table)
    with pytest.raises(ValueError):
        TurnoutTableSet((table, table))
    with pytest.raises(KeyError):
        original.update(replace(table, name="Missing"))
