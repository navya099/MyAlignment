from dataclasses import dataclass
from enum import Enum
import math


@dataclass(frozen=True, slots=True)
class CorridorFeatureLineSpec:
    """코드 또는 고정 횡거로 코리더 종방향 선을 선택한다.

    링크의 시작과 끝을 모두 선택하면 중점을 사용한다. 양쪽에서
    후보가 발견되면 중심선에 가까운 점을, 좌측 또는 우측만 선택하면
    그쪽에서 가장 바깥 점을 사용한다.
    """

    name: str = ""
    extraction_method: str = "point_code"
    point_code: Enum | None = None
    link_code: Enum | None = None
    use_start: bool = True
    use_end: bool = False
    offset: float = 0.0
    side: str = "both"
    layer: str = "C-CORRIDOR-FL"
    color: int = 7
    lineweight: float = 0.3

    def __post_init__(self):
        if not self.name.strip() or any(ord(char) < 32 for char in self.name):
            raise ValueError("name must be nonempty single-line text")
        if self.extraction_method not in ("point_code", "link_code", "offset"):
            raise ValueError("extraction_method must be point_code, link_code, or offset")
        if self.extraction_method == "point_code" and not isinstance(self.point_code, Enum):
            raise ValueError("point_code mode requires a point_code")
        if self.extraction_method == "link_code":
            if not isinstance(self.link_code, Enum):
                raise ValueError("link_code mode requires a link_code")
            if not self.use_start and not self.use_end:
                raise ValueError("link_code mode requires use_start or use_end")
        if not math.isfinite(self.offset):
            raise ValueError("offset must be finite")
        if self.side not in ("left", "right", "both"):
            raise ValueError("side must be left, right, or both")
        if self.extraction_method == "offset" and (
            (self.side == "left" and self.offset >= 0) or (self.side == "right" and self.offset <= 0)
        ):
            raise ValueError("offset must be on the requested side")
        if not self.layer.strip() or any(ord(char) < 32 for char in self.layer):
            raise ValueError("layer must be nonempty single-line text")
        if type(self.color) is not int or not 0 <= self.color <= 256:
            raise ValueError("color must be an ACI integer from 0 to 256")
        if not math.isfinite(self.lineweight) or self.lineweight < 0:
            raise ValueError("lineweight must be finite and nonnegative")
