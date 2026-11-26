from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from myalignment.pipe.pipe import Pipe
from myalignment.pipe.structure import Structure

if TYPE_CHECKING:
    from myalignment.surface.tin_surface import TinSurface


@dataclass(frozen=True, slots=True)
class PipeNetwork:
    """구조물의 연결 관 목록과 최저 접속 관저고를 유지하는 불변 관망."""

    name: str = "PipeNetwork1"
    pipes: tuple[Pipe, ...] = ()
    structures: tuple[Structure, ...] = ()
    parts_list_name: str = ""
    reference_alignment: str = ""
    reference_surface: str = ""
    cover_sampled: bool = False

    def __post_init__(self):
        structures = tuple(self.structures)
        pipes = tuple(self.pipes)
        for label, parts in (("Structure", structures), ("Pipe", pipes)):
            ids = [part.id for part in parts]
            names = [part.name for part in parts]
            if any(not value.strip() for value in ids) or len(set(ids)) != len(ids):
                raise ValueError(f"{label} IDs must be nonempty and unique")
            if any(not value.strip() for value in names) or len(set(names)) != len(names):
                raise ValueError(f"{label} names must be nonempty and unique")

        connections = defaultdict(dict)
        inverts = defaultdict(list)
        for pipe in pipes:
            for structure_id, invert in (
                (pipe.start_structure_id, pipe.start_invert), (pipe.end_structure_id, pipe.end_invert),
            ):
                connections[structure_id][pipe.id] = None
                inverts[structure_id].append(invert)
        object.__setattr__(self, "pipes", pipes)
        object.__setattr__(self, "structures", tuple(
            replace(
                structure, connected_pipe_ids=tuple(connections[structure.id]),
                invert_elevation=min(inverts[structure.id], default=structure.invert_elevation),
            )
            for structure in structures
        ))

    def __len__(self) -> int:
        return len(self.pipes) + len(self.structures)

    def get_structure(self, struct_id: str) -> Structure | None:
        return next((structure for structure in self.structures if structure.id == struct_id), None)

    def get_pipe(self, pipe_id: str) -> Pipe | None:
        return next((pipe for pipe in self.pipes if pipe.id == pipe_id), None)

    def add_structure(self, struct: Structure) -> PipeNetwork:
        return replace(self, structures=(*self.structures, struct))

    def add_pipe(self, pipe: Pipe) -> PipeNetwork:
        """존재하는 구조물 사이에 관을 추가하고 두 끝점의 위치를 연결한다."""
        start = self.get_structure(pipe.start_structure_id)
        end = self.get_structure(pipe.end_structure_id)
        if start is None or end is None:
            raise ValueError(f"Pipe {pipe.name!r} requires two existing structures")
        pipe = self._connect_pipe(pipe, start, end)
        return replace(self, pipes=(*self.pipes, pipe))

    @staticmethod
    def _connect_pipe(pipe: Pipe, start: Structure, end: Structure) -> Pipe:
        if (start.id == end.id or start.point is None or end.point is None
                or start.point.distance_to(end.point) <= 1e-8):
            raise ValueError(f"Pipe {pipe.name!r} requires two distinct located endpoints")
        for given, expected in ((pipe.start_point, start.point), (pipe.end_point, end.point)):
            if given is not None and given.distance_to(expected) > 1e-8:
                raise ValueError(f"Pipe {pipe.name!r} endpoint does not match its structure")
        return replace(pipe, start_point=start.point, end_point=end.point)

    @property
    def total_pipe_length(self) -> float:
        return sum(pipe.length for pipe in self.pipes)

    @property
    def min_cover(self) -> float | None:
        """표고가 확인된 관 끝점의 최소 토피."""
        return min((value for pipe in self.pipes for value in (pipe.cover_start, pipe.cover_end)
                    if value is not None), default=None)

    def with_cover_from(self, surface: TinSurface) -> PipeNetwork:
        """TIN이 덮는 관 끝점의 지표 표고를 저장한다."""

        def elevation(point):
            if point is None or surface.triangle_at(point.x, point.y) is None:
                return None
            return surface.elevation_at(point.x, point.y)

        return replace(self, cover_sampled=True, reference_surface=surface.name or self.reference_surface, pipes=tuple(
            replace(
                pipe, surface_name=surface.name or pipe.surface_name or self.reference_surface,
                start_surface_elevation=elevation(pipe.start_point), end_surface_elevation=elevation(pipe.end_point),
            )
            for pipe in self.pipes
        ))
