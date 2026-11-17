# target/reference.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

from myalignment.target.target_type import TargetType


class TargetObjectType(Enum):
    """Target으로 사용 가능한 객체 유형."""
    ALIGNMENT = "Alignment"
    PROFILE = "Profile"
    SURFACE = "Surface"
    POLYLINE = "Polyline"
    FEATURE_LINE = "FeatureLine"
    SURVEY_FIGURE = "SurveyFigure"
    PIPE_NETWORK = "PipeNetwork"


@dataclass(frozen=True, slots=True)
class TargetReference:
    """
    Target 참조 (불변).

    C3D의 Target 매핑을 표현.
    - logical_name: 서브어셈블리가 참조하는 이름 (예: "TargetDTM")
    - target_type: Offset/Elevation/Surface
    - object_type: 실제 매핑된 객체 유형
    - object_name: 실제 객체 이름
    """
    logical_name: str = ""
    target_type: TargetType = TargetType.SURFACE
    object_type: TargetObjectType = TargetObjectType.SURFACE
    object_name: str = ""

    def __post_init__(self):
        if not self.logical_name:
            raise ValueError("logical_name이 비어있습니다.")
        # 유효성: target_type에 따라 object_type 제한
        if self.target_type == TargetType.SURFACE:
            if self.object_type != TargetObjectType.SURFACE:
                raise ValueError(
                    f"Surface Target은 Surface 객체만 가능: {self.object_type}"
                )
        if self.target_type == TargetType.OFFSET:
            if self.object_type not in (
                    TargetObjectType.ALIGNMENT,
                    TargetObjectType.POLYLINE,
                    TargetObjectType.FEATURE_LINE,
                    TargetObjectType.SURVEY_FIGURE,
            ):
                raise ValueError(
                    f"Offset Target 부적합 객체: {self.object_type}"
                )
        if self.target_type == TargetType.ELEVATION:
            if self.object_type not in (
                    TargetObjectType.PROFILE,
                    TargetObjectType.FEATURE_LINE,
                    TargetObjectType.SURVEY_FIGURE,
            ):
                raise ValueError(
                    f"Elevation Target 부적합 객체: {self.object_type}"
                )

    def __repr__(self) -> str:
        return (
            f"Target('{self.logical_name}' → {self.object_name}, "
            f"{self.target_type.name}, {self.object_type.name})"
        )