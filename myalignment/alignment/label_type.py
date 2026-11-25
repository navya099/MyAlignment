from enum import Enum


class AlignmentLabelType(Enum):
    MAJOR_STATION = "MajorStation"
    MINOR_STATION = "MinorStation"
    GEOMETRY_POINT = "GeometryPoint"
    LINE = "Line"
    CURVE = "Curve"
    SPIRAL = "Spiral"
    CURVE_POINT = "CurvePoint"
    STATION_EQUATION = "StationEquation"
