# entity/pi_input.py
from __future__ import annotations
from dataclasses import dataclass, field
import math

from cadgeom import Point2d

from myalignment.enum.spiraltype import SpiralType
from myalignment.exception.alignment_error import NotEnoughPIPointError


@dataclass(frozen=True, slots=True)
class PICurveSpec:
    """하나의 PI에 대한 곡선 사양."""
    radius: float | None = None  # None = 직선 (곡선 없음)
    spiral_type: SpiralType = SpiralType.Clothoid
    entry_length: float = 0.0  # 진입 완화곡선장 (L1)
    exit_length: float = 0.0  # 진출 완화곡선장 (L2)
    is_symmetric: bool = True  # 대칭 여부 (entry == exit)

    def __post_init__(self):
        if self.radius is not None and self.radius <= 0:
            raise ValueError(f"radius > 0 필요: {self.radius}")
        if self.entry_length < 0 or self.exit_length < 0:
            raise ValueError("완화곡선장은 ≥ 0 필요")
        if self.is_symmetric and self.entry_length != self.exit_length:
            raise ValueError(
                f"대칭인데 L1({self.entry_length}) ≠ L2({self.exit_length})"
            )

    @property
    def is_straight(self) -> bool:
        return self.radius is None

    @property
    def has_spiral(self) -> bool:
        return self.entry_length > 0 or self.exit_length > 0

    def normalized(self) -> "PICurveSpec":
        """대칭이면 entry/exit 통일."""
        if self.is_symmetric:
            L = max(self.entry_length, self.exit_length)
            return PICurveSpec(
                radius=self.radius,
                spiral_type=self.spiral_type,
                entry_length=L,
                exit_length=L,
                is_symmetric=True,
            )
        return self


@dataclass(frozen=True, slots=True)
class PIInput:
    """
    PI 좌표 + 곡선 사양 입력.

    C3D의 Alignment.CreateFromPolyline 등에 대응.
    """
    pi_coords: tuple[Point2d, ...] = field(default_factory=tuple)
    curve_specs: tuple[PICurveSpec, ...] = field(default_factory=tuple)
    start_station: float = 0.0

    def __post_init__(self):
        if len(self.pi_coords) < 2:
            raise NotEnoughPIPointError()
        if len(self.pi_coords) != len(self.curve_specs):
            raise ValueError(
                f"PI({len(self.pi_coords)}) ≠ specs({len(self.curve_specs)})"
            )
        # 첫/끝 PI는 반드시 직선
        if not self.curve_specs[0].is_straight:
            raise ValueError("첫 PI는 직선이어야 합니다.")
        if not self.curve_specs[-1].is_straight:
            raise ValueError("끝 PI는 직선이어야 합니다.")

    @classmethod
    def from_coords_and_radii(
            cls,
            coords: list[tuple[float, float]] | list[Point2d],
            radii: list[float | None],
            start_station: float = 0.0,
            spiral_type: SpiralType = SpiralType.Clothoid,
            entry_lengths: list[float] | None = None,
            exit_lengths: list[float] | None = None,
    ) -> "PIInput":
        """좌표/반경 리스트로부터 편의 생성."""
        pts = tuple(
            c if isinstance(c, Point2d) else Point2d(c[0], c[1])
            for c in coords
        )
        n = len(pts)
        if entry_lengths is None:
            entry_lengths = [0.0] * n
        if exit_lengths is None:
            exit_lengths = [0.0] * n

        specs = tuple(
            PICurveSpec(
                radius=radii[i],
                spiral_type=spiral_type,
                entry_length=entry_lengths[i],
                exit_length=exit_lengths[i],
                is_symmetric=(entry_lengths[i] == exit_lengths[i]),
            )
            for i in range(n)
        )
        return cls(pi_coords=pts, curve_specs=specs, start_station=start_station)