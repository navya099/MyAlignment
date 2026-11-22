from dataclasses import replace

import pytest
from cadgeom import Point2d

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.enitity.entity_collection import AlignmentEntityCollection
from myalignment.enitity.spiral_entity import SpiralEntity
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


def test_transaction_accumulates_updates_for_different_profile_types():
    alignment = _alignment()
    ground = ProfileBuilder("Ground").add_tangent(100, 200, 15, 15).build()
    design = ProfileBuilder("Design", ProfileType.FG).add_tangent(100, 200, 12, 12).build()
    with alignment.modify() as transaction:
        transaction.update_profile(ground).update_profile(design)
    assert transaction.result.profiles == (ground, design)


def test_transaction_adds_structure_to_result_only():
    alignment = _alignment()
    bridge = Bridge.create("Bridge", 120, 130)
    with alignment.modify() as transaction:
        transaction.add_structure(bridge)
    assert tuple(transaction.result.structures) == (bridge,)
    assert not alignment.structures


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("has_pi_input", [False, True])
def test_transaction_preserves_asymmetric_curve_specs_through_multiple_edits(reverse, has_pi_input):
    original_coords = [(0, 0), (150, 0), (150, 150), (300, 150)]
    coords = [(0, 0), (145, 5), (150, 150), (300, 150)]

    def build(points, radii):
        return (
            AlignmentBuilder().with_pi_coords(points)
            .with_radii(radii)
            .with_spiral_lengths([0, 10, 15, 0], [0, 20, 5, 0])
            .with_start_station(1000)
            .build()
        )

    original = build(original_coords, [None, 35, 40, None])
    expected = build(coords, [None, 35, 45, None])
    if reverse:
        original, expected = original.reversed_alignment(), expected.reversed_alignment()
    if not has_pi_input:
        original = replace(original, entities=AlignmentEntityCollection(tuple(original.entities)))

    with original.modify() as transaction:
        transaction.update_pi_and_radius(2 if reverse else 1, point=Point2d(145, 5))
        transaction.update_pi_and_radius(1 if reverse else 2, radius=45)

    result = transaction.result
    assert result.start_station == expected.start_station
    assert result.end_station == pytest.approx(expected.end_station)
    assert len(result.entities) == len(expected.entities)
    for entity, reference in zip(result.entities, expected.entities):
        assert type(entity) is type(reference)
        assert entity.start_coord.distance_to(reference.start_coord) < 1e-6
        assert entity.end_coord.distance_to(reference.end_coord) < 1e-6
        if isinstance(entity, SpiralEntity):
            assert entity.geometry.params == reference.geometry.params


def test_transaction_preserves_sorted_structures_and_rolls_back_failed_edit():
    alignment = _alignment()
    late = Bridge.create("Late", 150, 160)
    early = Bridge.create("Early", 125, 130)
    transaction = alignment.modify()
    with pytest.raises(IndexError):
        with transaction:
            transaction.add_structure(late).update_pi_and_radius(0, radius=20)
    with pytest.raises(RuntimeError):
        _ = transaction.result

    with transaction:
        transaction.add_structure(late).add_structure(early)
    assert tuple(transaction.result.structures) == (early, late)
    assert not alignment.structures
