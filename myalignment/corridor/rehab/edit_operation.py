from enum import Enum


class CorridorEditOperation(Enum):
    """코리더 영역에 적용하는 편집 작업."""

    UPDATE_REGION = "UpdateRegion"
    UPDATE_FREQUENCY = "UpdateFrequency"
    UPDATE_ASSEMBLY = "UpdateAssembly"
    UPDATE_TARGET = "UpdateTarget"
    SPLIT_REGION = "SplitRegion"
    MERGE_REGION = "MergeRegion"
    ADD_REGION = "AddRegion"
    DELETE_REGION = "DeleteRegion"
    REPLACE_REGION_RANGE = "ReplaceRange"
