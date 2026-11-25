from enum import Enum


class ProjectionObjectType(Enum):
    """종단 뷰에서 사용할 투영 객체 유형."""

    STRUCTURE = "Structure"
    FEATURE_LINE = "FeatureLine"
    ALIGNMENT = "Alignment"
    POINT = "Point"
    BLOCK = "Block"
    PIPE = "Pipe"
