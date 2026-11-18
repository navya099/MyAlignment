# quantity/material.py
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class UnitType(Enum):
    """수량 단위."""
    AREA = "m²"
    VOLUME = "m³"
    LENGTH = "m"
    COUNT = "개"


@dataclass(frozen=True, slots=True)
class Material:
    """
    재료 (불변).

    C3D Material과 호환.
    - 단가/단위 포함.
    """
    name: str = ""
    shape_code: str = ""  # 매핑된 ShapeCode (name)
    unit_type: UnitType = UnitType.VOLUME
    unit_price: float = 0.0  # 원/단위

    def __post_init__(self):
        if self.unit_price < 0:
            raise ValueError(f"unit_price ≥ 0 필요: {self.unit_price}")

    def __repr__(self) -> str:
        return (
            f"Material('{self.name}', "
            f"{self.unit_type.value}, {self.unit_price:,.0f}원/{self.unit_type.value})"
        )