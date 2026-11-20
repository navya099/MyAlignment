from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class ProfileViewStyle:
    """종단 뷰의 그리드, 수직 과장과 기본 밴드 위치."""

    name: str = "Standard"
    grid_major_interval_station: float = 100.0
    grid_minor_interval_station: float = 20.0
    grid_major_interval_elevation: float = 10.0
    grid_minor_interval_elevation: float = 2.0
    vertical_exaggeration: float = 10.0
    band_location: str = "bottom"

    def __post_init__(self):
        for name in (
            "grid_major_interval_station",
            "grid_minor_interval_station",
            "grid_major_interval_elevation",
            "grid_minor_interval_elevation",
            "vertical_exaggeration",
        ):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if self.band_location not in ("top", "bottom"):
            raise ValueError("band_location must be top or bottom")
