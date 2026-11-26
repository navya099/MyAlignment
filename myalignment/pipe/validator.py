from __future__ import annotations

import math
from typing import TYPE_CHECKING

from myalignment.pipe.pipe_type import StructureType

if TYPE_CHECKING:
    from myalignment.pipe.network import PipeNetwork
    from myalignment.surface.tin_surface import TinSurface


class PipeNetworkValidator:
    """구조물 연결, 흐름 방향과 관 끝점의 토피를 검사한다."""

    MIN_COVER = 0.6
    MIN_SLOPE = 0.005

    @classmethod
    def validate(
        cls, network: PipeNetwork, *, surface: TinSurface | None = None,
        min_cover: float = MIN_COVER, min_slope: float = MIN_SLOPE,
    ) -> list[str]:
        """지표면이 지정된 경우 양 끝점의 TIN 범위와 최소 토피를 검사한다."""
        if not all(math.isfinite(value) and value >= 0 for value in (min_cover, min_slope)):
            raise ValueError("min_cover and min_slope must be finite and nonnegative")
        if surface is not None:
            network = network.with_cover_from(surface)
        check_surface = network.cover_sampled or bool(network.reference_surface)
        structures = {structure.id: structure for structure in network.structures}
        errors = []
        for structure in structures.values():
            if structure.point is None:
                errors.append(f"Structure {structure.name!r}: missing XY location")
            if structure.part.structure_type is not StructureType.NULL:
                if structure.depth < -1e-8:
                    errors.append(f"Structure {structure.name!r}: rim is below its invert")
                if structure.bottom_elevation > structure.invert_elevation + 1e-8:
                    errors.append(f"Structure {structure.name!r}: sump is above its invert")
        for pipe in network.pipes:
            label = f"Pipe {pipe.name!r}"
            endpoints = (
                ("start", pipe.start_structure_id, pipe.start_point, pipe.cover_start),
                ("end", pipe.end_structure_id, pipe.end_point, pipe.cover_end),
            )
            for side, structure_id, point, cover in endpoints:
                structure = structures.get(structure_id)
                if structure is None:
                    errors.append(f"{label}: missing {side} structure {structure_id!r}")
                elif point is not None and structure.point is not None and point.distance_to(structure.point) > 1e-8:
                    errors.append(f"{label}: {side} endpoint does not match its structure")
                if point is None:
                    errors.append(f"{label}: missing {side} XY location")
                if cover is not None and cover < min_cover - 1e-8:
                    errors.append(f"{label}: {side} cover {cover:.3f} m is below {min_cover:g} m")
                elif cover is None and (check_surface or pipe.surface_name):
                    errors.append(f"{label}: {side} surface elevation is unavailable")
            if pipe.start_structure_id == pipe.end_structure_id:
                errors.append(f"{label}: start and end must use different structures")
            if pipe.length <= 1e-8:
                errors.append(f"{label}: positive plan length is required")
            elif pipe.slope < 0:
                errors.append(f"{label}: adverse slope ({pipe.slope_percent:.2f}%)")
            elif pipe.slope < min_slope - 1e-12:
                errors.append(f"{label}: slope {pipe.slope_percent:.2f}% is below {min_slope * 100:g}%")
        return errors

    @classmethod
    def is_valid(
        cls, network: PipeNetwork, *, surface: TinSurface | None = None,
        min_cover: float = MIN_COVER, min_slope: float = MIN_SLOPE,
    ) -> bool:
        return not cls.validate(network, surface=surface, min_cover=min_cover, min_slope=min_slope)
