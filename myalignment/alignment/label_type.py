from enum import Enum


class AlignmentLabelType(Enum):
    MAJOR_STATION = "MajorStation"
    MINOR_STATION = "MinorStation"
    GEOMETRY_POINT = "GeometryPoint"
    LINE = "Line"
    CURVE = "Curve"
    SPIRAL = "Spiral"
    STATION_EQUATION = "StationEquation"
