# tests/target/test_reference.py
import pytest

from myalignment.target.reference import TargetReference, TargetObjectType
from myalignment.target.target_type import TargetType


def test_surface_target_valid():
    ref = TargetReference(
        logical_name="TargetDTM",
        target_type=TargetType.SURFACE,
        object_type=TargetObjectType.SURFACE,
        object_name="기존지표면",
    )
    assert ref.logical_name == "TargetDTM"


def test_surface_target_invalid_object():
    with pytest.raises(ValueError):
        TargetReference(
            logical_name="TargetDTM",
            target_type=TargetType.SURFACE,
            object_type=TargetObjectType.ALIGNMENT,   # 잘못됨
            object_name="선형1",
        )


def test_offset_target_valid():
    ref = TargetReference(
        logical_name="EdgeOffset",
        target_type=TargetType.OFFSET,
        object_type=TargetObjectType.ALIGNMENT,
        object_name="외곽선형",
    )
    assert ref.target_type == TargetType.OFFSET