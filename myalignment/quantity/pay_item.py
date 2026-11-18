# quantity/pay_item.py
from __future__ import annotations
from dataclasses import dataclass, field

from myalignment.quantity.material import Material


@dataclass(frozen=True, slots=True)
class PayItem:
    """
    지불 항목 (불변).

    C3D PayItem과 호환.
    - 재료별 수량 + 단가.
    """
    item_code: str = ""
    description: str = ""
    material: Material = None
    quantity: float = 0.0

    def __post_init__(self):
        if self.material is None:
            raise ValueError("material이 None입니다.")
        if self.quantity < 0:
            raise ValueError(f"quantity ≥ 0 필요: {self.quantity}")

    @property
    def total_cost(self) -> float:
        """총액 = 수량 × 단가."""
        return self.quantity * self.material.unit_price

    def __repr__(self) -> str:
        return (
            f"PayItem('{self.item_code}', {self.quantity:,.2f} "
            f"{self.material.unit_type.value}, {self.total_cost:,.0f}원)"
        )