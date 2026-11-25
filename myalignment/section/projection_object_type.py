from enum import Enum


class SectionProjectionObjectType(Enum):
    """횡단 뷰에 표시하는 원본 객체 유형."""

    STRUCTURE = "Structure"
    PIPE = "Pipe"
    POINT = "Point"
    FEATURE_LINE = "FeatureLine"
    ALIGNMENT = "Alignment"
