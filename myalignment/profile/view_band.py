from dataclasses import dataclass
from enum import Enum
import math


class BandType(Enum):
    PROFILE_DATA = "ProfileData"
    VERTICAL_GEOMETRY = "VerticalGeom"
    HORIZONTAL_GEOMETRY = "HorizontalGeom"
    CANT_DATA = "CantData"
    EARTHWORK = "Earthwork"


@dataclass(frozen=True, slots=True)
class ProfileViewBand:
    """종단 뷰의 데이터 밴드. location을 생략하면 스타일의 위치를 사용한다."""

    band_type: BandType
    style_name: str = "Standard"
    location: str | None = None
    gap: float = 0.0
    profile_names: tuple[str, ...] = ()

    def __post_init__(self):
        if self.location not in (None, "top", "bottom"):
            raise ValueError("location must be top or bottom")
        if not math.isfinite(self.gap) or self.gap < 0:
            raise ValueError("gap must be finite and nonnegative")
