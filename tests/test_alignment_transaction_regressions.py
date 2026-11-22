import pytest
from cadgeom import Point2d

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.profile.profile import ProfileBuilder
from myalignment.profile.profiletype import ProfileType
from myalignment.structure.bridge import Bridge


def _alignment():
    profile = ProfileBuilder("Original").add_tangent(100, 200, 10, 10).build()
    return (
        AlignmentBuilder("Axis").with_pi_coords([(0, 0), (50, 0), (100, 0)])
        .with_start_station(100).with_profile(profile).build()
        .add_station_equation(150, 500)
    )


def test_transaction_commits_pi_and_profile_edits_without_mutating_original():
    alignment = _alignment()
    profile = ProfileBuilder("Updated").add_tangent(100, 200, 10, 11).build()
    with alignment.modify() as transaction:
        transaction.rename("Updated Axis").update_pi_and_radius(1, point=Point2d(50, 5)).update_profile(profile)
        with pytest.raises(RuntimeError):
            _ = transaction.result

    result = transaction.result
    assert result.name == "Updated Axis"
    assert result.profiles == (profile,)
    assert result.entities[1].start_coord == Point2d(50, 5)
    assert result.start_station == 100
    assert result.raw_to_display_station(150) == 500
    assert alignment.name == "Axis"
    assert alignment.entities[1].start_coord == Point2d(50, 0)
    assert alignment.profiles[0].name == "Original"


@pytest.mark.parametrize("index", [0, 2])
def test_invalid_pi_edit_aborts_transaction(index):
    alignment = _alignment()
    with pytest.raises(IndexError):
        with alignment.modify() as transaction:
            transaction.rename("Pending").update_pi_and_radius(index, point=Point2d(12, 2))
    with pytest.raises(RuntimeError):
        _ = transaction.result
    assert alignment.name == "Axis"


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="update_profile reads the original tuple after each edit")
def test_transaction_accumulates_updates_for_different_profile_types():
    alignment = _alignment()
    ground = ProfileBuilder("Ground").add_tangent(100, 200, 15, 15).build()
    design = ProfileBuilder("Design", ProfileType.FG).add_tangent(100, 200, 12, 12).build()
    with alignment.modify() as transaction:
        transaction.update_profile(ground).update_profile(design)
    assert transaction.result.profiles == (ground, design)


@pytest.mark.xfail(strict=True, raises=AttributeError, reason="add_structure calls append on the immutable StructureCollection")
def test_transaction_adds_structure_to_result_only():
    alignment = _alignment()
    bridge = Bridge.create("Bridge", 120, 130)
    with alignment.modify() as transaction:
        transaction.add_structure(bridge)
    assert tuple(transaction.result.structures) == (bridge,)
    assert not alignment.structures
