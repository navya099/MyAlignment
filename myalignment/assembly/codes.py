# assembly/codes.py
from enum import Enum


class PointCode(Enum):
    """C3D Point 코드 (표준)."""
    # 기준
    PAVEMENT_BOTTOM = "Pavement_Bottom"
    CENTERLINE = "Centerline"
    BASELINE = "Baseline"
    # 차로
    LANE_INNER = "LaneInner"
    LANE_OUTER = "LaneOuter"
    LANE_EDGE = "LaneEdge"
    # 갓길
    SHOULDER_INNER = "ShoulderInner"
    SHOULDER_OUTER = "ShoulderOuter"
    # 사면
    CATCH_POINT = "CatchPoint"
    HINGE_POINT = "HingePoint"
    DAYLIGHT = "Daylight"
    # 배수
    DITCH_INNER = "DitchInner"
    DITCH_OUTER = "DitchOuter"
    DITCH_BOTTOM = "DitchBottom"
    # 철도
    LEFT_RAIL = "LeftRail"
    RIGHT_RAIL = "RightRail"
    # 일반
    CROWN = "Crown"
    EDGE = "Edge"


class LinkCode(Enum):
    """C3D Link 코드."""
    PAVEMENT_SIDE = "Pavement_Side"
    PAVEMENT_BOTTOM = "Pavement_Bottom"
    LANE = "Lane"
    PAVEMENT_TOP = "Pavement_Top"
    PAVEMENT = "Pavement"
    SUBBASE = "Subbase"
    SHOULDER = "Shoulder"
    SLOPE = "Slope"
    DITCH = "Ditch"
    CURB = "Curb"
    DATUM = "Datum"
    BALLAST = "Ballast"
    TOP = "Top"


class ShapeCode(Enum):
    """C3D Shape 코드 (물량 산출용)."""
    PAVEMENT = "Pavement"
    SUBBASE = "Subbase"
    SHOULDER = "Shoulder"
    CURB = "Curb"
    SIDEWALK = "Sidewalk"
    MEDIAN = "Median"