from dataclasses import dataclass
import math

from myalignment.assembly.codes import LinkCode, PointCode
from myalignment.corridor.surface_extraction_mode import SurfaceExtractionMode


@dataclass(frozen=True, slots=True)
class LinkSurfaceSpec:
    """코드 선택, 측점 간격, 경계와 평면도 색상을 지정한다.

    sample_frequency를 생략하면 각 영역의 측점 간격을 사용한다.
    POINT_BASED에는 하나의 point_code를 지정한다.
    """

    name: str = ""
    mode: SurfaceExtractionMode = SurfaceExtractionMode.SINGLE_LINK
    link_codes: tuple[LinkCode, ...] = ()
    link_code: LinkCode | None = None
    overhang_correction: bool = False
    use_boundary: bool = True
    color: int | None = None
    point_code: PointCode | None = None
    sample_frequency: float | None = None

    def __post_init__(self):
        codes = tuple(dict.fromkeys(self.link_codes))
        object.__setattr__(self, "link_codes", codes)
        if not self.name.strip():
            raise ValueError("name must not be empty")
        if not isinstance(self.mode, SurfaceExtractionMode):
            raise ValueError("mode must be a SurfaceExtractionMode")
        if any(not isinstance(code, LinkCode) for code in codes):
            raise ValueError("link_codes must contain LinkCode values")
        if self.mode is SurfaceExtractionMode.SINGLE_LINK and not isinstance(self.link_code, LinkCode):
            raise ValueError("SINGLE_LINK requires a link_code")
        if self.mode is SurfaceExtractionMode.MULTI_LINK and not codes:
            raise ValueError("MULTI_LINK requires link_codes")
        if self.mode is SurfaceExtractionMode.POINT_BASED and not isinstance(self.point_code, PointCode):
            raise ValueError("POINT_BASED requires a point_code")
        if self.sample_frequency is not None and (
            not math.isfinite(self.sample_frequency) or self.sample_frequency <= 0
        ):
            raise ValueError("sample_frequency must be finite and positive")
        if self.color is not None and (type(self.color) is not int or not 0 <= self.color <= 256):
            raise ValueError("color must be an ACI integer from 0 to 256")

    def get_all_codes(self) -> tuple[LinkCode, ...]:
        """사양에 명시한 링크 코드. ALL_LINKS에 코드가 없으면 전부 선택한다."""
        return (self.link_code,) if self.mode is SurfaceExtractionMode.SINGLE_LINK else self.link_codes
