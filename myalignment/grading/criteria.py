# grading/criteria.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import math
from enum import Enum


class ProjectionType(Enum):
    """경사 투영 방향."""
    OUTSIDE = "outside"
    INSIDE = "inside"
    LEFT = "left"
    RIGHT = "right"


class SlopeFormat(Enum):
    """경사 표현 형식."""
    RATIO = "ratio"  # 1:n
    PERCENT = "percent"  # %
    DEGREE = "degree"  # °


@dataclass(frozen=True, slots=True)
class Slope:
    """
    경사 값 (불변).

    예: 1:2 = RATIO(2), 5% = PERCENT(5), 26.57° = DEGREE(26.57)
    """
    value: float = 0.0
    format: SlopeFormat = SlopeFormat.RATIO

    def __post_init__(self):
        if self.value <= 0:
            raise ValueError(f"경사 > 0 필요: {self.value}")

    @property
    def ratio(self) -> float:
        """1:n 형식의 n."""
        if self.format == SlopeFormat.RATIO:
            return self.value
        elif self.format == SlopeFormat.PERCENT:
            return 100.0 / self.value
        elif self.format == SlopeFormat.DEGREE:
            return 1.0 / math.tan(math.radians(self.value))

    @property
    def percent(self) -> float:
        """% 형식."""
        if self.format == SlopeFormat.PERCENT:
            return self.value
        elif self.format == SlopeFormat.RATIO:
            return 100.0 / self.value
        elif self.format == SlopeFormat.DEGREE:
            return math.tan(math.radians(self.value)) * 100

    @property
    def degree(self) -> float:
        """° 형식."""
        if self.format == SlopeFormat.DEGREE:
            return self.value
        elif self.format == SlopeFormat.RATIO:
            return math.degrees(math.atan(1.0 / self.value))
        elif self.format == SlopeFormat.PERCENT:
            return math.degrees(math.atan(self.value / 100))


@dataclass(frozen=True, slots=True)
class GradingCriteria(ABC):
    """
    경사 기준 (불변, 추상).

    C3D의 GradingCriteria와 호환.
    - 발자국에서 경사를 적용해 목표까지 투영.
    """
    name: str = ""
    slope: Slope = field(default_factory=lambda: Slope(1.5))   # 기본 1:5
    projection: ProjectionType = ProjectionType.OUTSIDE

    def __post_init__(self):
        if self.slope is None:
            raise ValueError("slope가 None입니다.")

    @abstractmethod
    def compute_daylight(
            self,
            footprint_point: "Point2d",
            footprint_elevation: float,
            direction: float,  # 경사 방향 (rad)
            target_context: "TargetContext",
    ) -> "DaylightResult | None":
        """
        발자국 점에서 경사를 투영해 자연 지표선 계산.

        Returns:
            DaylightResult | None — 목표 도달점 (없으면 None).
        """
        ...


@dataclass(frozen=True, slots=True)
class DaylightResult:
    """자연 지표선 결과."""
    point: "Point2d"
    elevation: float
    distance: float  # 발자국에서의 수평 거리