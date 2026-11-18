# quantity/report.py
from __future__ import annotations
from dataclasses import dataclass

from myalignment.quantity.takeoff import TakeoffResult


@dataclass(frozen=True, slots=True)
class QTOReport:
    """QTO 리포트 (C3D QTO Report 호환)."""
    result: TakeoffResult = None

    def to_text(self) -> str:
        lines = [
            "=" * 70,
            "Quantity Takeoff Report",
            "=" * 70,
            "",
            f"{'재료':<20} {'수량':>15} {'단가':>15} {'총액':>20}",
            "-" * 70,
        ]
        for mq in self.result.material_quantities:
            lines.append(
                f"{mq.material_name:<20} "
                f"{mq.total_quantity:>13,.2f} {mq.unit_type.value} "
                f"{mq.total_cost / max(mq.total_quantity, 1e-9):>12,.0f}원 "
                f"{mq.total_cost:>18,.0f}원"
            )
        lines.append("-" * 70)
        lines.append(f"{'합계':<20} {'':>15} {'':>15} {self.result.total_cost:>18,.0f}원")
        lines.append("=" * 70)
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            'materials': [
                {
                    'name': mq.material_name,
                    'quantity': mq.total_quantity,
                    'unit': mq.unit_type.value,
                    'cost': mq.total_cost,
                }
                for mq in self.result.material_quantities
            ],
            'total_cost': self.result.total_cost,
        }