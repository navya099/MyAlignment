from dataclasses import dataclass
import math

from myalignment.pipe.pipe_type import PipeMaterial, PipeShape, StructureType


@dataclass(frozen=True, slots=True)
class PipePart:
    """관 부품 치수. 비원형 관의 diameter_mm은 내측 수직 높이이다."""

    name: str = ""
    material: PipeMaterial = PipeMaterial.RCP
    shape: PipeShape = PipeShape.CIRCULAR
    diameter_mm: float = 450.0
    wall_thickness_mm: float = 50.0
    width_mm: float | None = None

    def __post_init__(self):
        if not isinstance(self.material, PipeMaterial) or not isinstance(self.shape, PipeShape):
            raise ValueError("material and shape must be pipe enums")
        if not math.isfinite(self.diameter_mm) or self.diameter_mm <= 0:
            raise ValueError("diameter_mm must be finite and positive")
        if not math.isfinite(self.wall_thickness_mm) or self.wall_thickness_mm < 0:
            raise ValueError("wall_thickness_mm must be finite and nonnegative")
        if self.width_mm is not None:
            if not math.isfinite(self.width_mm) or self.width_mm <= 0:
                raise ValueError("width_mm must be finite and positive")
            if self.shape is PipeShape.CIRCULAR and self.width_mm != self.diameter_mm:
                raise ValueError("circular pipe width must equal its diameter")

    @property
    def outer_diameter_mm(self) -> float:
        """외측 수직 치수."""
        return self.diameter_mm + 2 * self.wall_thickness_mm

    @property
    def diameter_m(self) -> float:
        return self.diameter_mm / 1000

    @property
    def width_m(self) -> float:
        return (self.diameter_mm if self.width_mm is None else self.width_mm) / 1000


@dataclass(frozen=True, slots=True)
class StructurePart:
    """맨홀·집수정 등 관망 구조물의 부품 치수."""

    name: str = ""
    structure_type: StructureType = StructureType.MANHOLE
    diameter_mm: float = 1200.0
    depth_m: float = 3.0
    rim_elevation_offset: float = 0.0
    has_frame: bool = True

    def __post_init__(self):
        if not isinstance(self.structure_type, StructureType):
            raise ValueError("structure_type must be a StructureType")
        for name in ("diameter_mm", "depth_m"):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0 or (not value and self.structure_type is not StructureType.NULL):
                raise ValueError(f"{name} must be finite and positive for a visible structure")
        if not math.isfinite(self.rim_elevation_offset):
            raise ValueError("rim_elevation_offset must be finite")

    @property
    def diameter_m(self) -> float:
        return self.diameter_mm / 1000
