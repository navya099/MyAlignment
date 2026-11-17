# structure/structure.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import math
from typing import Self

from myalignment.structure.struturetype import StructureType
from myalignment.utils.utils import generate_entity_id


@dataclass(frozen=True, slots=True)
class Structure(ABC):
    """
    선형 위의 구조물 (불변).

    C3D의 Structure와 호환.
    - Alignment의 station 범위를 점유.
    - 상세 부재(거더/교각)는 Revit/해석 모듈의 영역.

    Attributes:
        structure_id: 고유 식별자 (UUID 기반).
        name: 구조물 이름.
        structure_type: 구조물 종류.
        start_station: 시작 측점 (m).
        end_station: 끝 측점 (m).
        metadata: 추가 메타데이터 (설계 정보 등).
    """
    structure_id: int = field(default_factory=generate_entity_id)
    name: str = ""
    structure_type: StructureType = StructureType.BRIDGE
    start_station: float = 0.0
    end_station: float = 0.0
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.end_station < self.start_station:
            raise ValueError(
                f"end_station({self.end_station}) < "
                f"start_station({self.start_station})"
            )
        if not (math.isfinite(self.start_station) and math.isfinite(self.end_station)):
            raise ValueError("측점이 유한하지 않음")
        if not isinstance(self.structure_type, StructureType):
            raise TypeError(
                f"structure_type은 StructureType이어야 함: {type(self.structure_type)}"
            )

    # ---- 필수 속성 ----
    @property
    def length(self) -> float:
        """구조물 길이 (m)."""
        return self.end_station - self.start_station

    # ---- 조회 ----
    def contains_station(self, station: float) -> bool:
        """측점이 구조물 범위 내인지 (경계 포함)."""
        return self.start_station <= station <= self.end_station

    def overlaps_with(self, other: "Structure") -> bool:
        """다른 구조물과 구간 겹침 여부."""
        return not (
                self.end_station < other.start_station
                or other.end_station < self.start_station
        )

    def overlap_length(self, other: "Structure") -> float:
        """겹치는 구간 길이."""
        if not self.overlaps_with(other):
            return 0.0
        return min(self.end_station, other.end_station) - max(
            self.start_station, other.start_station
        )

    # ---- 불변 변환 ----
    @abstractmethod
    def reversed(self) -> Self:
        """뒤집힌 새 구조물."""
        ...

    def with_station_range(
            self, start_station: float, end_station: float
    ) -> Self:
        """측점 범위 변경한 새 구조물."""
        from dataclasses import replace
        return replace(self, start_station=start_station, end_station=end_station)

    def with_metadata(self, **kwargs) -> Self:
        """메타데이터 갱신한 새 구조물."""
        from dataclasses import replace
        new_meta = {**self.metadata, **kwargs}
        return replace(self, metadata=new_meta)

    # ---- 표현 ----
    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"name='{self.name}', "
            f"type={self.structure_type.name}, "
            f"sta=[{self.start_station:.3f}, {self.end_station:.3f}], "
            f"len={self.length:.3f})"
        )

    def __str__(self) -> str:
        return (
            f"{self.structure_type.value} '{self.name}' "
            f"({self.start_station:.1f} ~ {self.end_station:.1f}, "
            f"L={self.length:.1f}m)"
        )