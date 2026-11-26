from __future__ import annotations

from typing import Self

from myalignment.assembly.conditional.branch import ConditionalBranch
from myalignment.assembly.conditional.condition import Condition
from myalignment.assembly.conditional.conditional_subassembly import ConditionalSubassembly
from myalignment.assembly.subassembly import Subassembly


class ConditionalSubassemblyBuilder:
    """평가 순서대로 조건 분기와 마지막 else를 설정한다."""

    def __init__(self, name: str = "Conditional"):
        self._name = name
        self._side = 1
        self._branches: list[ConditionalBranch] = []
        self._else_subassembly: Subassembly | None = None

    def with_side(self, side: int) -> Self:
        self._side = side
        return self

    def add_branch(self, condition: Condition, subassembly: Subassembly) -> Self:
        if not isinstance(condition, Condition):
            raise TypeError("condition must be a Condition")
        self._branches.append(ConditionalBranch(subassembly, condition))
        return self

    def else_(self, subassembly: Subassembly) -> Self:
        self._else_subassembly = subassembly
        return self

    def build(self) -> ConditionalSubassembly:
        if self._else_subassembly is None:
            raise ValueError("An else branch is required")
        return ConditionalSubassembly(
            name=self._name, side=self._side,
            branches=(*self._branches, ConditionalBranch(self._else_subassembly)),
        )
