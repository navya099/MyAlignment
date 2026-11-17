# target/mapping.py
from __future__ import annotations
from dataclasses import dataclass, field

from myalignment.target.reference import TargetReference
from myalignment.target.target_type import TargetType


@dataclass(frozen=True, slots=True)
class TargetMapping:
    """
    하나의 Region에 대한 Target 매핑 (불변).

    C3D의 Region Target 설정과 호환.
    - logical_name → TargetReference 매핑.
    """
    references: tuple[TargetReference, ...] = field(default_factory=tuple)

    def __post_init__(self):
        # logical_name 중복 검증
        names = [r.logical_name for r in self.references]
        if len(names) != len(set(names)):
            raise ValueError(f"logical_name 중복: {names}")

    def get(self, logical_name: str) -> TargetReference | None:
        """logical_name으로 Target 참조 조회."""
        for r in self.references:
            if r.logical_name == logical_name:
                return r
        return None

    def by_type(self, target_type: TargetType) -> list[TargetReference]:
        """유형별 Target 참조 리스트."""
        return [r for r in self.references if r.target_type == target_type]

    def add(self, reference: TargetReference) -> "TargetMapping":
        """새 Target 참조 추가한 새 매핑."""
        # 기존 logical_name 교체
        new_refs = [r for r in self.references if r.logical_name != reference.logical_name]
        new_refs.append(reference)
        return TargetMapping(references=tuple(new_refs))

    @classmethod
    def empty(cls) -> "TargetMapping":
        return cls()