from dataclasses import dataclass
import math

from myalignment.assembly.subassemblies.curb_type import CurbType


_FACE_WIDTH_FRACTIONS = {
    CurbType.VERTICAL: 0.0,
    CurbType.SLOPED: 1 / 3,
    CurbType.MOUNTABLE: 2 / 3,
    CurbType.BARRIER: 1 / 6,
}


@dataclass(frozen=True, slots=True)
class CurbParams:
    """연석 높이와 총 폭, 상단 구배와 전면의 수평/수직 기울기."""

    curb_type: CurbType = CurbType.VERTICAL
    height: float = 0.15
    width: float = 0.15
    top_slope: float = 0.0
    face_slope: float | None = None

    def __post_init__(self):
        if not isinstance(self.curb_type, CurbType):
            raise ValueError("curb_type must be a CurbType")
        for name in ("height", "width"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if not math.isfinite(self.top_slope):
            raise ValueError("top_slope must be finite")
        if self.face_slope is not None and (not math.isfinite(self.face_slope) or self.face_slope < 0):
            raise ValueError("face_slope must be finite and nonnegative")
        if self.face_offset >= self.width:
            raise ValueError("face_offset must be smaller than width")
        if not math.isfinite(self.back_height) or self.back_height <= 0:
            raise ValueError("curb back height must be finite and positive")

    @property
    def face_offset(self) -> float:
        """전면 상단의 바깥쪽 오프셋."""
        if self.face_slope is None:
            return self.width * _FACE_WIDTH_FRACTIONS[self.curb_type]
        return self.height * self.face_slope

    @property
    def back_height(self) -> float:
        """연석 상단 후면의 높이."""
        return self.height + (self.width - self.face_offset) * self.top_slope


@dataclass(frozen=True, slots=True)
class SidewalkParams:
    """보도 폭·구배·두께와 통합 단면의 연석 포함 여부."""

    width: float = 2.0
    slope: float = -0.02
    thickness: float = 0.1
    include_curb: bool = True

    def __post_init__(self):
        for name in ("width", "thickness"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if not math.isfinite(self.slope) or not math.isfinite(self.width * self.slope - self.thickness):
            raise ValueError("slope must produce finite elevations")
