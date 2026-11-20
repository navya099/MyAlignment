from pathlib import Path
from typing import TextIO

from myalignment.export.dxf_writer import DxfWriter, _groups, _linetype, _xyz
from myalignment.render.primitives_3d import Primitive3D, PrimitiveType3D
from myalignment.render.scene_3d import Scene3D


class Dxf3DWriter(DxfWriter):
    """3차원 좌표를 DXF R12 POINT, LINE, POLYLINE과 3DFACE로 저장한다."""

    def __init__(self, scene: Scene3D):
        super().__init__(scene)

    def write(self, path: str | Path) -> None:
        self._write_scene(path, tuple(p for p in self.scene.primitives if p.style.visible), ())

    @staticmethod
    def _write_primitive(stream: TextIO, primitive: Primitive3D, layer: str) -> None:
        kind, points, style = primitive.type, primitive.points, primitive.style
        attributes = (8, layer), (62, style.color), (6, _linetype(style.linetype))
        if kind in (PrimitiveType3D.POINT, PrimitiveType3D.LINE):
            _groups(stream, (0, kind.value), *attributes, *_xyz(points[0]))
            if kind is PrimitiveType3D.LINE:
                _groups(stream, *_xyz(points[1], 11))
        elif kind is PrimitiveType3D.POLYLINE:
            closed = primitive.closed or (len(points) > 2 and points[0] == points[-1])
            if closed and points[0] == points[-1]:
                points = points[:-1]
            _groups(stream, (0, "POLYLINE"), *attributes, (66, 1),
                    (10, 0.0), (20, 0.0), (30, 0.0), (70, 8 | int(closed)))
            for point in points:
                _groups(stream, (0, "VERTEX"), (8, layer), *_xyz(point), (70, 32))
            _groups(stream, (0, "SEQEND"), (8, layer))
        elif kind in (PrimitiveType3D.TRIANGLE, PrimitiveType3D.MESH):
            faces = ((0, 1, 2),) if kind is PrimitiveType3D.TRIANGLE else primitive.indices
            for a, b, c in faces:
                _groups(stream, (0, "3DFACE"), *attributes,
                        *_xyz(points[a]), *_xyz(points[b], 11), *_xyz(points[c], 12), *_xyz(points[c], 13))
