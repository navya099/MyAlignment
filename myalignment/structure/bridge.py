# structure/bridge.py
from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Self

from myalignment.structure.structure import Structure
from myalignment.structure.struturetype import StructureType


@dataclass(frozen=True, slots=True)
class Bridge(Structure):
    """
    교량 (C3D Bridge 호환).

    상세 부재(거더/교각/교대)는 Revit/Structural Bridge Design의 영역.
    여기서는 선형 위의 구간 점유만 담당.

    metadata 예시:
        - 'span_count': 경간 수
        - 'bridge_type': 'RC', 'Steel', 'PSC'
        - 'width': 폭 (m)
    """
    structure_type: StructureType = StructureType.BRIDGE

    @classmethod
    def create(
            cls,
            name: str,
            start_station: float,
            end_station: float,
            **metadata,
    ) -> "Bridge":
        return cls(
            name=name,
            start_station=start_station,
            end_station=end_station,
            structure_type=StructureType.BRIDGE,
            metadata=metadata,
        )

    @property
    def span_count(self) -> int:
        """경간 수 (metadata에서)."""
        return int(self.metadata.get('span_count', 0))

    @property
    def bridge_type(self) -> str:
        """교량 형식 (metadata에서)."""
        return self.metadata.get('bridge_type', '')

    @property
    def width(self) -> float:
        """교량 폭 (metadata에서)."""
        return float(self.metadata.get('width', 0.0))

    def reversed(self) -> "Bridge":
        return replace(self)