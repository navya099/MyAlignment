from enum import Enum


class ProfileLabelType(Enum):
    LINE = "Line"
    CURVE = "Curve"
    GRADIENT_BREAK = "GradientBreak"
    CREST_CURVE = "CrestCurve"
    SAG_CURVE = "SagCurve"
    PVI = "PVI"
