# structure/structure_collection.py
from __future__ import annotations
from dataclasses import dataclass, field, replace
from typing import Iterator

from myalignment.structure.structure import Structure
from myalignment.structure.struturetype import StructureType


@dataclass(frozen=True, slots=True)
class StructureCollection:
    """
    구조물 컬렉션 (불변).

    C3D의 StructureCollection과 호환.
    - station 순서로 정렬 보장.
    - 겹침 검증.
    """
    structures: tuple[Structure, ...] = field(default_factory=tuple)

    def __post_init__(self):
        # 정렬 검증
        for i in range(len(self.structures) - 1):
            a, b = self.structures[i], self.structures[i + 1]
            if a.start_station > b.start_station:
                raise ValueError(
                    f"구조물이 station 순서가 아님: "
                    f"[{i}] {a.start_station} > [{i + 1}] {b.start_station}"
                )

    # ---- 기본 속성 ----
    def __len__(self) -> int:
        return len(self.structures)

    def __iter__(self) -> Iterator[Structure]:
        return iter(self.structures)

    def __getitem__(self, idx):
        return self.structures[idx]

    # ---- 조회 ----
    def get_by_type(self, structure_type: StructureType) -> list[Structure]:
        """타입별 구조물 리스트."""
        return [s for s in self.structures if s.structure_type == structure_type]

    def find_at_station(self, station: float) -> Structure | None:
        """주어진 측점에 포함된 첫 번째 구조물."""
        for s in self.structures:
            if s.contains_station(station):
                return s
        return None

    def find_overlapping(self, other: Structure) -> list[Structure]:
        """주어진 구조물과 겹치는 구조물들."""
        return [s for s in self.structures if s.overlaps_with(other)]

    def structure_type_at(self, station: float) -> StructureType | None:
        """주어진 측점의 구조물 타입 (없으면 None = 토공)."""
        s = self.find_at_station(station)
        return s.structure_type if s else None

    def total_length_by_type(self, structure_type: StructureType) -> float:
        """타입별 총 길이."""
        return sum(s.length for s in self.get_by_type(structure_type))

    # ---- 집계 ----
    @property
    def bridge_count(self) -> int:
        return len(self.get_by_type(StructureType.BRIDGE))

    @property
    def tunnel_count(self) -> int:
        return len(self.get_by_type(StructureType.TUNNEL))

    @property
    def total_bridge_length(self) -> float:
        return self.total_length_by_type(StructureType.BRIDGE)

    @property
    def total_tunnel_length(self) -> float:
        return self.total_length_by_type(StructureType.TUNNEL)

    @property
    def start_station(self) -> float:
        return self.structures[0].start_station if self.structures else 0.0

    @property
    def end_station(self) -> float:
        return self.structures[-1].end_station if self.structures else 0.0

    # ---- 불변 변환 ----
    def add(self, structure: Structure) -> "StructureCollection":
        """새 구조물 추가한 새 컬렉션 (정렬 유지)."""
        new_list = list(self.structures) + [structure]
        new_list.sort(key=lambda s: s.start_station)
        return StructureCollection(structures=tuple(new_list))

    def remove(self, structure_id: int) -> "StructureCollection":
        """structure_id로 삭제한 새 컬렉션."""
        new_list = [s for s in self.structures if s.structure_id != structure_id]
        return StructureCollection(structures=tuple(new_list))

    def replace_structure(self, new_structure: Structure) -> "StructureCollection":
        """같은 structure_id의 구조물 교체."""
        new_list = [
            new_structure if s.structure_id == new_structure.structure_id else s
            for s in self.structures
        ]
        new_list.sort(key=lambda s: s.start_station)
        return StructureCollection(structures=tuple(new_list))

    def __repr__(self) -> str:
        return f"StructureCollection(count={len(self)}, {list(self.structures)})"