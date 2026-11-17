# structure/tunnel.py
from __future__ import annotations
from dataclasses import dataclass, replace

from myalignment.structure.structure import Structure
from myalignment.structure.struturetype import StructureType

@dataclass(frozen=True, slots=True)
class Tunnel(Structure):
    """
    터널 (C3D Tunnel 호환).

    metadata 예시:
        - 'tunnel_type': 'NATM', 'TBM', 'Shield'
        - 'diameter': 직경 (m)
        - 'ventilation': '자연', '기계'
    """
    structure_type: StructureType = StructureType.TUNNEL

    @classmethod
    def create(
            cls,
            name: str,
            start_station: float,
            end_station: float,
            **metadata,
    ) -> "Tunnel":
        return cls(
            name=name,
            start_station=start_station,
            end_station=end_station,
            structure_type=StructureType.TUNNEL,
            metadata=metadata,
        )

    @property
    def tunnel_type(self) -> str:
        return self.metadata.get('tunnel_type', '')

    @property
    def diameter(self) -> float:
        return float(self.metadata.get('diameter', 0.0))

    def reversed(self) -> "Tunnel":
        return replace(self)