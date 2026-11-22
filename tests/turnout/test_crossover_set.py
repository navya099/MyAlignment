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

def test_rail_reversal_remaps_owned_turnouts_and_invalidates_crossover_geometry():
    from dataclasses import replace
    import math

    from myalignment.alignment.alignment_builder import AlignmentBuilder
    from myalignment.turnout.crossover_builder import CrossoverBuilder
    from myalignment.turnout.type import TurnoutSide, TurnoutType

    a = AlignmentBuilder("A").with_pi_coords([(0, 0), (200, 0)]).as_rail_alignment().build()
    b = AlignmentBuilder("B").with_pi_coords([(0, 5), (200, 5)]).as_rail_alignment().build()
    turnout_type = TurnoutType("T", frog_number=10, radius=40)
    distance = 2 * turnout_type.run + (5 - 2 * turnout_type.rise) / math.tan(turnout_type.frog_angle)
    crossover = (
        CrossoverBuilder().with_alignments("A", "B").with_turnout_type(turnout_type)
        .at_stations(20, 20 + distance).build()
    )
    geometry = crossover.compute_geometry(a, b)
    assert geometry.is_valid
    original = crossover.with_geometry(geometry)
    a = replace(a, crossovers=CrossoverSet((original,)))
    reverse = a.reversed_alignment()
    transformed, = reverse.crossovers
    assert transformed.turnout1.station_on_source == 180
    assert transformed.turnout1.side is TurnoutSide.RIGHT
    assert reverse.point_at(180).distance_to(a.point_at(20)) < 1e-9
    assert transformed.turnout2 is original.turnout2
    assert transformed.geometry is None
    assert not reverse.crossovers.valid_only()
    assert original.is_valid


def test_rail_reversal_remaps_additional_turnouts_on_only_owned_alignment():
    from dataclasses import replace

    from myalignment.alignment.alignment_builder import AlignmentBuilder
    from myalignment.turnout.crossover_builder import CrossoverBuilder
    from myalignment.turnout.type import TurnoutSide, TurnoutType

    a = AlignmentBuilder("A").with_pi_coords([(0, 0), (100, 0)]).as_rail_alignment().build()
    original = (
        CrossoverBuilder().with_alignments("A", "B").with_turnout_type(TurnoutType("T", 10, 0, 40))
        .as_double().at_stations(10, 70).build()
    )
    a = replace(a, crossovers=CrossoverSet((original,)))
    result, = a.reversed_alignment().crossovers
    assert result.turnouts[2] is original.turnouts[2]
    assert result.turnouts[3].station_on_source == 30
    assert result.turnouts[3].side is TurnoutSide.RIGHT
