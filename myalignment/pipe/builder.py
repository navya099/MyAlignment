from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.pipe.network import PipeNetwork
from myalignment.pipe.pipe import Pipe
from myalignment.pipe.pipe_part import PipePart, StructurePart
from myalignment.pipe.pipe_type import PipeMaterial, StructureType
from myalignment.pipe.structure import Structure

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.surface.tin_surface import TinSurface


class PipeNetworkBuilder:
    """구조물과 연결 관을 선언하고 참조 선형·지표에서 위치와 토피를 구한다."""

    def __init__(self, name: str = "PipeNetwork1"):
        self._name = name
        self._pipes: list[Pipe] = []
        self._structures: list[Structure] = []
        self._parts_list = ""
        self._alignment_name = ""
        self._surface_name = ""
        self._alignment: Alignment | None = None
        self._surface: TinSurface | None = None

    def with_parts_list(self, name: str) -> PipeNetworkBuilder:
        self._parts_list = name
        return self

    def with_alignment(self, name: str | Alignment) -> PipeNetworkBuilder:
        """이름을 참조로 저장하거나 선형 객체로 원시 측점과 좌표를 변환한다."""
        self._alignment = None if isinstance(name, str) else name
        self._alignment_name = name if isinstance(name, str) else name.name
        return self

    def with_surface(self, name: str | TinSurface) -> PipeNetworkBuilder:
        """이름을 참조로 저장하거나 TIN에서 관 끝점 표고를 읽는다."""
        self._surface = None if isinstance(name, str) else name
        self._surface_name = name if isinstance(name, str) else name.name
        return self

    def add_structure(
        self, name: str, part: StructurePart, point: Point2d | None = None,
        station: float | None = None, offset: float = 0.0, rim_elevation: float = 0.0,
        invert_elevation: float = 0.0, *, sump_elevation: float | None = None,
    ) -> PipeNetworkBuilder:
        if not name.strip() or any(structure.name == name for structure in self._structures):
            raise ValueError(f"Structure name must be nonempty and unique: {name!r}")
        self._structures.append(Structure(
            id=f"S_{len(self._structures):03d}", name=name, part=part, point=point,
            station=station, offset=offset, rim_elevation=rim_elevation, invert_elevation=invert_elevation,
            sump_elevation=sump_elevation,
        ))
        return self

    def add_manhole(
        self, name: str, point: Point2d | None = None, station: float | None = None, offset: float = 0.0,
        rim_elevation: float = 0.0, invert_elevation: float = 0.0, diameter_mm: float = 1200.0,
        *, sump_elevation: float | None = None,
    ) -> PipeNetworkBuilder:
        return self.add_structure(
            name, StructurePart(name=f"MH {diameter_mm:g} mm", diameter_mm=diameter_mm),
            point, station, offset, rim_elevation, invert_elevation, sump_elevation=sump_elevation,
        )

    def add_null_structure(
        self, name: str, point: Point2d | None = None, station: float | None = None,
        offset: float = 0.0, invert_elevation: float = 0.0,
    ) -> PipeNetworkBuilder:
        part = StructurePart(structure_type=StructureType.NULL, diameter_mm=0, depth_m=0, has_frame=False)
        return self.add_structure(name, part, point, station, offset, invert_elevation=invert_elevation)

    def _structure(self, key: str) -> Structure:
        matches = [structure for structure in self._structures if key in (structure.id, structure.name)]
        if len(matches) != 1:
            raise ValueError(f"Expected one structure for {key!r}, found {len(matches)}")
        return matches[0]

    def add_pipe(
        self, name: str, start_struct_id: str, end_struct_id: str,
        material: PipeMaterial = PipeMaterial.RCP, diameter_mm: float = 450.0,
        start_invert: float | None = None, end_invert: float | None = None, *, part: PipePart | None = None,
    ) -> PipeNetworkBuilder:
        """구조물 ID 또는 이름으로 관을 연결한다."""
        if not name.strip() or any(pipe.name == name for pipe in self._pipes):
            raise ValueError(f"Pipe name must be nonempty and unique: {name!r}")
        start, end = self._structure(start_struct_id), self._structure(end_struct_id)
        if start.id == end.id:
            raise ValueError("A pipe must connect two different structures")
        if part is None:
            part = PipePart(material=material, diameter_mm=diameter_mm)
        self._pipes.append(Pipe(
            id=f"P_{len(self._pipes):03d}", name=name, part=part, start_structure_id=start.id,
            end_structure_id=end.id, start_invert=start.invert_elevation if start_invert is None else start_invert,
            end_invert=end.invert_elevation if end_invert is None else end_invert,
        ))
        return self

    def _locate(self, structure: Structure) -> Structure:
        alignment = self._alignment
        if structure.point is not None:
            if alignment is None:
                return structure
            projection = alignment.project(structure.point)
            return replace(structure, station=projection.station, offset=projection.offset)
        if alignment is None or structure.station is None:
            raise ValueError(f"Structure {structure.name!r} requires XY or station with a reference alignment")
        point = alignment.point_at(structure.station, structure.offset)
        return replace(structure, point=point)

    def build(self) -> PipeNetwork:
        structures = {structure.id: self._locate(structure) for structure in self._structures}
        pipes = tuple(
            PipeNetwork._connect_pipe(
                replace(pipe, alignment_name=self._alignment_name, surface_name=self._surface_name),
                structures[pipe.start_structure_id], structures[pipe.end_structure_id],
            )
            for pipe in self._pipes
        )
        network = PipeNetwork(
            self._name, pipes, tuple(structures.values()), self._parts_list, self._alignment_name, self._surface_name,
        )
        return network if self._surface is None else network.with_cover_from(self._surface)
