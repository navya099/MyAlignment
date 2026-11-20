from enum import Enum


class SectionLabelType(Enum):
    OFFSET_ELEVATION = "OffsetElevation"
    SLOPE = "Slope"
    DISTANCE = "Distance"
    GRADE_BREAK = "GradeBreak"
    SECTION_SEGMENT = "SectionSegment"
