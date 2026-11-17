# tests/target/test_mapping.py
import pytest

from myalignment.target.mapping import TargetMapping
from myalignment.target.reference import TargetReference, TargetObjectType
from myalignment.target.target_type import TargetType


def test_mapping_get():
    ref = TargetReference(
        logical_name="TargetDTM",
        target_type=TargetType.SURFACE,
        object_type=TargetObjectType.SURFACE,
        object_name="지표면1",
    )
    m = TargetMapping(references=(ref,))
    assert m.get("TargetDTM") is ref
    assert m.get("Unknown") is None


def test_mapping_add_replaces():
    ref1 = TargetReference(
        logical_name="TargetDTM",
        target_type=TargetType.SURFACE,
        object_type=TargetObjectType.SURFACE,
        object_name="지표면1",
    )
    ref2 = TargetReference(
        logical_name="TargetDTM",
        target_type=TargetType.SURFACE,
        object_type=TargetObjectType.SURFACE,
        object_name="지표면2",
    )
    m = TargetMapping(references=(ref1,))
    m2 = m.add(ref2)
    assert m2.get("TargetDTM").object_name == "지표면2"
    assert m.get("TargetDTM").object_name == "지표면1"   # 원본 불변


def test_mapping_duplicate_logical_name():
    ref1 = TargetReference(
        logical_name="X",
        target_type=TargetType.SURFACE,
        object_type=TargetObjectType.SURFACE,
        object_name="A",
    )
    ref2 = TargetReference(
        logical_name="X",
        target_type=TargetType.SURFACE,
        object_type=TargetObjectType.SURFACE,
        object_name="B",
    )
    with pytest.raises(ValueError):
        TargetMapping(references=(ref1, ref2))