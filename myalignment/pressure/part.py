from dataclasses import dataclass
from enum import Enum
import math

from myalignment.pipe.pipe_type import PipeMaterial


class FittingType(Enum):
    """압력관을 연결하는 피팅 유형."""

    BEND = "Bend"
    TEE = "Tee"
    CROSS = "Cross"
    REDUCER = "Reducer"
    COUPLING = "Coupling"


class AppurtenanceType(Enum):
    """압력관의 밸브·소화전 등 기능 부속품 유형."""

    VALVE = "Valve"
    HYDRANT = "Hydrant"
    METER = "Meter"
    BLOWOFF = "Blowoff"


def _positive(value: float, name: str) -> None:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")


@dataclass(frozen=True, slots=True)
class PressurePipePart:
    """공칭경, 내경, 벽 두께와 압력 등급을 갖는 관 부품."""

    name: str = ""
    material: PipeMaterial = PipeMaterial.PVC
    nominal_diameter_mm: float = 150.0
    inner_diameter_mm: float = 150.0
    pressure_rating_psi: float = 150.0
    wall_thickness_mm: float = 10.0

    def __post_init__(self):
        if not isinstance(self.material, PipeMaterial):
            raise ValueError("material must be a PipeMaterial")
        for name in ("nominal_diameter_mm", "inner_diameter_mm", "pressure_rating_psi"):
            _positive(getattr(self, name), name)
        if not math.isfinite(self.wall_thickness_mm) or self.wall_thickness_mm < 0:
            raise ValueError("wall_thickness_mm must be finite and nonnegative")
        _positive(self.outer_diameter_m, "outer_diameter_m")

    @property
    def inner_diameter_m(self) -> float:
        return self.inner_diameter_mm / 1000

    @property
    def outer_diameter_m(self) -> float:
        return self.inner_diameter_m + 2 * (self.wall_thickness_mm / 1000)


@dataclass(frozen=True, slots=True)
class FittingPart:
    """피팅의 공칭경, 엘보 방향 전환각, 허용 편향각."""

    name: str = ""
    fitting_type: FittingType = FittingType.BEND
    diameter_mm: float = 150.0
    angle_deg: float = 90.0
    max_deflection_deg: float = 11.25
    outlet_diameter_mm: float | None = None

    def __post_init__(self):
        if not isinstance(self.fitting_type, FittingType):
            raise ValueError("fitting_type must be a FittingType")
        _positive(self.diameter_mm, "diameter_mm")
        for name in ("angle_deg", "max_deflection_deg"):
            value = getattr(self, name)
            if not math.isfinite(value) or not 0 <= value <= 180:
                raise ValueError(f"{name} must be between 0 and 180 degrees")
        if self.outlet_diameter_mm is not None:
            _positive(self.outlet_diameter_mm, "outlet_diameter_mm")
            if self.fitting_type is not FittingType.REDUCER or self.diameter_mm == self.outlet_diameter_mm:
                raise ValueError("outlet_diameter_mm is a different nominal diameter on a reducer")

    @property
    def port_count(self) -> int:
        return {FittingType.TEE: 3, FittingType.CROSS: 4}.get(self.fitting_type, 2)


@dataclass(frozen=True, slots=True)
class AppurtenancePart:
    """밸브, 계량기와 말단 부속품의 공칭경."""

    name: str = ""
    appurtenance_type: AppurtenanceType = AppurtenanceType.VALVE
    diameter_mm: float = 150.0

    def __post_init__(self):
        if not isinstance(self.appurtenance_type, AppurtenanceType):
            raise ValueError("appurtenance_type must be an AppurtenanceType")
        _positive(self.diameter_mm, "diameter_mm")

    @property
    def port_count(self) -> int:
        return 2 if self.appurtenance_type in (AppurtenanceType.VALVE, AppurtenanceType.METER) else 1
