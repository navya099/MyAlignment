import pytest

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.turnout.scissors_builder import ScissorsCrossoverBuilder
from myalignment.turnout.scissors_crossover import ScissorsCrossover
from myalignment.turnout.scissors_type import ScissorsCrossoverType
from myalignment.turnout.type import TurnoutSide, TurnoutType


TURNOUT_TYPE = TurnoutType(frog_number=12, lead_length=30, radius=300)


def make_alignment(name, start_station, start, end):
    return (
        AlignmentBuilder(name)
        .with_pi_coords([start, end])
        .with_start_station(start_station)
        .build()
    )


def test_manual_scissors_builder_preserves_station_side_and_connection_mapping():
    builder = (
        ScissorsCrossoverBuilder("SC1")
        .with_alignments("A1", "A2")
        .with_turnout_type(TURNOUT_TYPE)
        .with_stations(100, 200, 1100, 1200)
        .with_sides(TurnoutSide.LEFT, TurnoutSide.RIGHT)
    )
    scissors = builder.build()

    assert scissors.crossover_type is ScissorsCrossoverType.STANDARD
    assert [t.name for t in scissors.turnouts] == ["SC1_T1", "SC1_T2", "SC1_T3", "SC1_T4"]
    assert [t.station_on_source for t in scissors.turnouts] == [100, 200, 1100, 1200]
    assert [t.source_alignment_name for t in scissors.turnouts] == ["A1", "A1", "A2", "A2"]
    assert [t.side for t in scissors.turnouts] == [TurnoutSide.LEFT] * 2 + [TurnoutSide.RIGHT] * 2
    assert [t.branch_alignment_name for t in scissors.turnouts] == [
        "SC1_C14", "SC1_C12", "SC1_C32", "SC1_C34",
    ]
    assert scissors.connecting_alignment_names == ("SC1_C14", "SC1_C32", "SC1_C12", "SC1_C34")

    symmetric = builder.symmetric_at(center=200, spacing=50).build()
    assert symmetric.crossover_type is ScissorsCrossoverType.SYMMETRIC
    assert [t.station_on_source for t in symmetric.turnouts] == [150, 250, 150, 250]
    assert symmetric.geometry is None


@pytest.mark.parametrize("distance, first_side, second_side", [
    (5, TurnoutSide.LEFT, TurnoutSide.RIGHT),
    (-5, TurnoutSide.RIGHT, TurnoutSide.LEFT),
])
def test_auto_scissors_uses_physical_center_and_inward_sides(distance, first_side, second_side):
    a1 = make_alignment("A1", 1000, (0, 0), (500, 0))
    a2 = make_alignment("A2", 2000, (40, distance), (500, distance))
    scissors = ScissorsCrossover.symmetric_auto_at("SC1", a1, a2, TURNOUT_TYPE, 1200)

    assert scissors.crossover_type is ScissorsCrossoverType.SYMMETRIC
    t1, t2, t3, t4 = scissors.turnouts
    assert [t.side for t in scissors.turnouts] == [first_side] * 2 + [second_side] * 2
    assert (t1.station_on_source + t2.station_on_source) / 2 == pytest.approx(1200)
    assert (t3.station_on_source + t4.station_on_source) / 2 == pytest.approx(2160)
    assert t2.station_on_source - t1.station_on_source == pytest.approx(
        2 * TURNOUT_TYPE.run + (abs(distance) - 2 * TURNOUT_TYPE.rise) * 12
    )
    assert scissors.is_valid
    assert scissors.geometry.diamond_center.x == pytest.approx(200)
    assert scissors.geometry.diamond_center.y == pytest.approx(distance / 2)


@pytest.mark.parametrize("start, end, center, message", [
    ((500, 5), (0, 5), 200, "같은 방향"),
    ((0, 5), (500, 10), 200, "평행"),
    ((0, 1), (500, 1), 200, "선간 거리"),
    ((0, 5), (500, 5), 10, "범위 밖"),
    ((300, 5), (500, 5), 200, "교차점 없음"),
])
def test_auto_scissors_rejects_invalid_placement(start, end, center, message):
    a1 = make_alignment("A1", 0, (0, 0), (500, 0))
    a2 = make_alignment("A2", 0, start, end)
    builder = ScissorsCrossoverBuilder().symmetric_auto_at(a1, a2, center)

    with pytest.raises(ValueError, match=message):
        builder.with_turnout_type(TURNOUT_TYPE).build()
