from enum import Enum


class SheetSize(Enum):
    """ISO A계열 가로 도면의 종이 치수(mm)."""

    A4 = ("A4", 297, 210)
    A3 = ("A3", 420, 297)
    A2 = ("A2", 594, 420)
    A1 = ("A1", 841, 594)
    A0 = ("A0", 1189, 841)

    def __init__(self, label: str, width_mm: int, height_mm: int):
        self.label = label
        self.width_mm = width_mm
        self.height_mm = height_mm

    @property
    def aspect_ratio(self) -> float:
        return self.width_mm / self.height_mm
