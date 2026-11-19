# tests/turnout/test_crossover_set.py
from myalignment.turnout.crossover_builder import CrossoverBuilder
from myalignment.turnout.crossover_set import CrossoverSet
from myalignment.turnout.type import TurnoutType


def test_crossover_set_filter():
    tt = TurnoutType(
        name="1/12",
        frog_number=12,
        lead_length=30,
        radius=300,
    )
    c1 = (
        CrossoverBuilder("C1")
        .with_alignments("A1", "A2")
        .with_turnout_type(tt)
        .at_stations(100, 100)
        .build()
    )
    c2 = (
        CrossoverBuilder("C2")
        .with_alignments("A2", "A3")
        .with_turnout_type(tt)
        .at_stations(200, 200)
        .build()
    )
    cset = CrossoverSet(crossovers=(c1, c2))


    a2_crossovers = cset.by_alignment("A2")
    assert len(a2_crossovers) == 2

    a1_crossovers = cset.by_alignment("A1")
    assert len(a1_crossovers) == 1