# profile/profile_entity.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import math
from typing import Self

from myalignment.profile.profileentitytype import ProfileEntityType
from myalignment.utils.utils import generate_entity_id


@dataclass(frozen=True, slots=True)
class ProfileEntity(ABC):
    """
    종단 요소 (불변).

    C3D의 ProfileEntity와 호환.
    - start_station/end_station 사이의 표고를 정의.
    - start_elevation/end_elevation은 **요소 경계의 실제 종단 표고**
      (elevation_at(start_station) == start_elevation 이 성립).
    """
    entity_id: int = field(default_factory=generate_entity_id)
    entity_type: ProfileEntityType = ProfileEntityType.Tangent
    start_station: float = 0.0
    end_station: float = 0.0
    start_elevation: float = 0.0
    end_elevation: float = 0.0

    def __post_init__(self):
        if self.end_station < self.start_station:
            raise ValueError(
                f"end_station({self.end_station}) < "
                f"start_station({self.start_station})"
            )
        if not (math.isfinite(self.start_elevation)
                and math.isfinite(self.end_elevation)):
            raise ValueError("표고가 유한하지 않음")

    # ---- 필수 속성 ----
    @property
    def length(self) -> float:
        """수평 길이 (m)."""
        return self.end_station - self.start_station

    @property
    def start_grade(self) -> float:
        return self.grade_at(self.start_station)

    @property
    def end_grade(self) -> float:
        return self.grade_at(self.end_station)

    # ---- 필수 메서드 ----
    @abstractmethod
    def elevation_at(self, station: float) -> float:
        """주어진 측점의 표고 (범위 밖은 경계값으로 클램프)."""
        ...

    @abstractmethod
    def grade_at(self, station: float) -> float:
        """주어진 측점의 구배 (범위 밖은 경계값으로 클램프)."""
        ...

    # ---- 불변 변환 ----
    @abstractmethod
    def reversed(self, total_length: float) -> Self:
        """
        전체 프로파일 길이(total_length) 기준으로 station을 L - s 로
        재매핑한 뒤집힌 새 요소를 반환한다.

        - start_station' = total_length - end_station
        - end_station'   = total_length - start_station
        - start_elevation' = end_elevation, end_elevation' = start_elevation
        - 내부 파라미터(PVI, 구배 등)도 반전에 맞게 재계산한다.
        """
        ...

    # ---- 검증 ----
    def contains_station(self, station: float) -> bool:
        return self.start_station <= station <= self.end_station

    def _clamp_station(self, station: float) -> float:
        return max(self.start_station, min(self.end_station, station))