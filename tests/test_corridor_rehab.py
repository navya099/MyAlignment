import pytest

from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.assembly.assembly import AssemblyBuilder
from myalignment.assembly.subassemblies.basic_lane import BasicLane
from myalignment.cant.curve import CantCriticalStation, CantCurve
from myalignment.corridor.corridor import Corridor
from myalignment.corridor.corridor_builder import CorridorBuilder
from myalignment.corridor.rehab.edit_command import CorridorEditCommand
from myalignment.corridor.rehab.edit_operation import CorridorEditOperation as Op
from myalignment.corridor.rehab.report import CorridorRehabReport
from myalignment.corridor.surface_builder import CorridorSurfaceSpec
from myalignment.target.mapping import TargetMapping
from myalignment.target.reference import TargetReference


def _lane(width=3.5):
    return AssemblyBuilder().add_both(lambda side: BasicLane(width=width, side=side)).build()


def _road():
    alignment = AlignmentBuilder("Main").with_pi_coords([(0, 0), (100, 0)]).build()
    corridor = (
        CorridorBuilder("Road").add_baseline_from_alignment(alignment)
        .add_region("First", 0, 40, _lane())
        .add_region("Second", 40, 80, _lane())
        .build()
    )
    return alignment, corridor


def test_batch_updates_all_region_properties_and_invalidates_sampled_artifacts():
    axis, corridor = _road()
    alignments = {axis.name: axis}
    surface = corridor.build_surface(CorridorSurfaceSpec("Design"), alignments=alignments)
    original = corridor.with_surface(surface).extract_feature_lines(alignments=alignments)
    assembly = _lane(4.25)
    targets = TargetMapping.empty().add(TargetReference("TargetDTM", object_name="Ground"))

    commands = (
        CorridorEditCommand(Op.REPLACE_REGION_RANGE, "First", new_end_station=30),
        CorridorEditCommand(Op.UPDATE_FREQUENCY, "First", new_frequency=6),
        CorridorEditCommand(Op.UPDATE_ASSEMBLY, "First", new_assembly=assembly),
        CorridorEditCommand(Op.UPDATE_TARGET, "First", new_targets=targets),
        CorridorEditCommand(Op.UPDATE_REGION, "Second", new_start_station=30, new_frequency=4),
    )
    edited = original.edit(iter(commands))
    first, second = edited.regions
    assert first.assembly is assembly and first.target_mapping is targets
    assert (first.end_station, first.frequency, second.start_station, second.frequency) == (30, 6, 30, 4)
    assert edited.baselines is original.baselines
    assert len(edited.surfaces) == len(edited.feature_lines) == 0
    assert len(original.surfaces) == 1 and len(original.feature_lines) == 5
    assert original.edit([CorridorEditCommand(Op.UPDATE_FREQUENCY, "First", new_frequency=10)]) is original
    assert original.edit([]) is original
    assert edited.cross_section_at(30) == edited.sample_cross_sections()[30]


def test_split_pins_inferred_baseline_and_preserves_cant_and_orientation():
    assembly = _lane()
    cant = CantCurve(start_station=0, end_station=80, critical_stations=(CantCriticalStation(0, 0.15),))
    targets = TargetMapping.empty().add(TargetReference("TargetDTM", object_name="Existing"))
    corridor = (
        CorridorBuilder().add_baseline("Main", "Main", "", 0, 100)
        .add_baseline("Spur", "Spur", "", 0, 50)
        .add_region_with_assembly("Track", 0, 80, assembly, targets=targets, cant_curve=cant)
        .build()
    )
    original = corridor.regions[0]
    with corridor.transaction() as tx:
        tx.split_region("Track", 40)
    edited = tx.result
    assert [r.name for r in edited.regions] == ["Track_A", "Track_B"]
    assert [r.baseline_name for r in edited.regions] == ["Main", "Main"]
    assert all(r.cant_curve is cant and r.target_mapping is targets for r in edited.regions)
    assert edited.cross_section_at(40, baseline_name="Main") == original.cross_section_at(40)
    with edited.transaction() as merge:
        merge.merge_regions("Track_B", "Track_A")
    assert merge.result.regions[0].name == "Track_A_merged"
    assert merge.result.regions[0].end_station == 80
    assert merge.result.regions[0].cant_curve is cant


def test_add_and_merge_use_same_baseline_and_earlier_settings():
    _, corridor = _road()
    with corridor.transaction() as tx:
        tx.update_region("Second", end_station=70, frequency=5, assembly=_lane(5))
        tx.add_region("Tail", 70, 100, baseline_name="Main")
        tx.merge_regions("Tail", "Second")
        tx.delete_region("First")
    result = tx.result
    merged, = result.regions
    assert (merged.name, merged.start_station, merged.end_station) == ("Second_merged", 40, 100)
    assert merged.frequency == 5 and merged.assembly.right_subassemblies[0].width == 5
    assert merged.target_mapping == TargetMapping.empty()

    empty = Corridor()
    added = empty.edit([CorridorEditCommand(Op.ADD_REGION, add_start_station=0, add_end_station=5,
                                            new_assembly=_lane())])
    assert added.regions[0].name == "NewRegion"
    assert added.regions[0].target_mapping == TargetMapping.empty()


def test_rejects_bad_edits_and_rolls_back_failed_transaction():
    _, corridor = _road()
    with pytest.raises(ValueError, match="overlap"):
        corridor.edit([CorridorEditCommand(Op.REPLACE_REGION_RANGE, "First", new_end_station=41)])
    with pytest.raises(ValueError, match="covering the region"):
        corridor.edit([CorridorEditCommand(Op.REPLACE_REGION_RANGE, "Second", new_end_station=101)])
    with pytest.raises(ValueError, match="strictly inside"):
        corridor.edit([CorridorEditCommand(Op.SPLIT_REGION, "Second", split_station=40)])
    with pytest.raises(ValueError, match="already exists"):
        corridor.edit([CorridorEditCommand(Op.ADD_REGION, "First", add_start_station=90, add_end_station=100)])
    with pytest.raises(ValueError, match="requires adjacent"):
        with corridor.transaction() as tx:
            tx.replace_region_range("First", end_station=39)
            tx.merge_regions("First", "Second")
    assert tx.result is corridor
    assert tx.history.snapshot_before is tx.history.snapshot_after is corridor
    with pytest.raises(RuntimeError, match="already completed"):
        tx.delete_region("First")
    with pytest.raises(RuntimeError, match="already been entered"):
        with tx:
            pass

    with pytest.raises(RuntimeError, match="body failure"):
        with corridor.transaction() as aborted:
            with pytest.raises(RuntimeError, match="not completed"):
                _ = aborted.result
            aborted.update_frequency("First", 2)
            raise RuntimeError("body failure")
    assert aborted.result is corridor
    assert len(aborted.commands) == 1


def test_parallel_baselines_can_use_same_region_name_and_report_is_unambiguous():
    corridor = (
        CorridorBuilder().add_baseline("A", "Axis A", "", 0, 100)
        .add_baseline("B", "Axis B", "", 0, 100)
        .add_region("Shared", 0, 25, _lane(), baseline_name="A")
        .add_region("Shared", 0, 25, _lane(), baseline_name="B")
        .add_region("Other", 25, 50, _lane(), baseline_name="B").build()
    )
    with pytest.raises(ValueError, match="ambiguous"):
        corridor.edit([CorridorEditCommand(Op.DELETE_REGION, "Shared")])
    with corridor.transaction() as tx:
        tx.update_frequency("Shared", 3, baseline_name="A")
        tx.delete_region("Other")
        tx.add_region("New", 25, 40, baseline_name="A")
    report = CorridorRehabReport.from_history(tx.history)
    assert (report.region_count_before, report.region_count_after) == (3, 3)
    assert report.modified_regions == ["A / Shared"]
    assert report.removed_regions == ["Other"]
    assert report.added_regions == ["New"]
    assert "UpdateFrequency Shared (A)" in report.to_text()
    assert tx.result.region_at(10, baseline_name="B").frequency == 10


def test_merge_rejects_different_baselines_and_incompatible_cant():
    cant = CantCurve(start_station=0, end_station=20)
    separate = (
        CorridorBuilder().add_baseline("A", "Axis A", "", 0, 40)
        .add_baseline("B", "Axis B", "", 0, 40)
        .add_region("R1", 0, 10, _lane(), baseline_name="A")
        .add_region("R2", 10, 20, _lane(), baseline_name="B").build()
    )
    with pytest.raises(ValueError, match="same baseline"):
        separate.edit([CorridorEditCommand(Op.MERGE_REGION, "R1,R2")])
    incompatible = (
        CorridorBuilder().add_region_with_assembly("Left", 0, 10, _lane(), cant_curve=cant)
        .add_region("Right", 10, 20, _lane()).build()
    )
    with pytest.raises(ValueError, match="compatible cant"):
        incompatible.edit([CorridorEditCommand(Op.MERGE_REGION, "Left,Right")])


def test_command_validation():
    with pytest.raises(ValueError, match="finite and positive"):
        CorridorEditCommand(Op.UPDATE_FREQUENCY, "R", new_frequency=float("nan"))
    with pytest.raises(ValueError, match="requires new_targets"):
        CorridorEditCommand(Op.UPDATE_TARGET, "R")
    with pytest.raises(ValueError, match="does not accept new_targets"):
        CorridorEditCommand(Op.DELETE_REGION, "R", new_targets=TargetMapping.empty())
    with pytest.raises(ValueError, match="requires two different"):
        CorridorEditCommand(Op.MERGE_REGION, "R,R")
