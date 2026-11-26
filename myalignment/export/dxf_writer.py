from __future__ import annotations

import math
from pathlib import Path
from typing import TextIO

from shapely import constrained_delaunay_triangles
from shapely.geometry import Polygon

from myalignment.render.primitives import Primitive, PrimitiveType
from myalignment.render.scene import Layer, Scene


_LINETYPE_PATTERNS = {
    "CONTINUOUS": (),
    "DASHED": (0.5, -0.25),
    "HIDDEN": (0.25, -0.125),
    "CENTER": (1.25, -0.25, 0.25, -0.25),
    "DOT": (0.0, -0.25),
    "DASHDOT": (0.5, -0.25, 0.0, -0.25),
    "PHANTOM": (1.25, -0.25, 0.25, -0.25, 0.25, -0.25),
}
_INHERITED_LINETYPES = {"BYLAYER", "BYBLOCK"}


def _linetype(name: str) -> str:
    return name.upper() if name else "BYLAYER"


def _escape_character(character: str) -> str:
    try:
        character.encode("cp949")
    except UnicodeEncodeError:
        pass
    else:
        return character
    data = character.encode("utf-16-be")
    return "".join(
        f"\\U+{int.from_bytes(data[i:i + 2], 'big'):04X}"
        for i in range(0, len(data), 2)
    )


def _groups(stream: TextIO, *pairs: tuple[int, object]) -> None:
    for code, value in pairs:
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"Non-finite DXF value for group {code}")
        raw = str(value)
        if any(ord(character) < 32 for character in raw):
            raise ValueError(f"Control character in DXF group {code}")
        text = "".join(map(_escape_character, raw)) if not raw.isascii() else raw
        stream.write(f"{code}\n{text}\n")


def _xyz(point, x_code: int = 10) -> tuple[tuple[int, float], ...]:
    return (x_code, point.x), (x_code + 10, point.y), (x_code + 20, getattr(point, "z", 0.0))


class DxfWriter:
    """2D 선, 원호, 텍스트와 채운 면을 DXF R12 텍스트 형식으로 저장한다.

    한글은 ANSI_949 코드페이지로 저장한다. R12에는 선가중치 속성이 없다. 알려지지 않은 선종류 이름은 연속선
    패턴으로 등록하며, 사용자 패턴은 linotypes로 지정할 수 있다.
    """

    def __init__(
        self, scene: Scene, *, linotypes: dict[str, tuple[float, ...]] | None = None
    ):
        self.scene = scene
        self._patterns = dict(_LINETYPE_PATTERNS)
        if linotypes:
            self._patterns.update((name.upper(), pattern) for name, pattern in linotypes.items())

    def write(self, path: str | Path) -> None:
        primitives = tuple(p for p in self.scene.primitives if p.style.opacity > 0)
        self._write_scene(path, primitives, self.scene.layers)

    def _write_scene(self, path, primitives, explicit_layers):
        layers = {"0": Layer("0")}
        layers.update((layer.name.casefold(), layer) for layer in explicit_layers)
        for primitive in primitives:
            name = primitive.style.layer or "0"
            layers.setdefault(name.casefold(), Layer(name))

        with open(path, "w", encoding="cp949", newline="\n") as stream:
            _groups(
                stream, (0, "SECTION"), (2, "HEADER"), (9, "$ACADVER"), (1, "AC1009"),
                (9, "$DWGCODEPAGE"), (3, "ANSI_949"), (0, "ENDSEC"),
            )
            self._write_tables(stream, layers.values(), primitives)
            _groups(stream, (0, "SECTION"), (2, "BLOCKS"), (0, "ENDSEC"))
            _groups(stream, (0, "SECTION"), (2, "ENTITIES"))
            for primitive in primitives:
                layer = layers[(primitive.style.layer or "0").casefold()]
                self._write_primitive(stream, primitive, layer.name)
            _groups(stream, (0, "ENDSEC"), (0, "EOF"))

    def _write_tables(self, stream: TextIO, layers, primitives) -> None:
        linetypes = {"CONTINUOUS"}
        linetypes.update(_linetype(layer.linetype) for layer in layers)
        linetypes.update(_linetype(primitive.style.linetype) for primitive in primitives)
        linetypes.difference_update(_INHERITED_LINETYPES)
        _groups(stream, (0, "SECTION"), (2, "TABLES"))
        _groups(stream, (0, "TABLE"), (2, "LTYPE"), (70, len(linetypes)))
        for name in sorted(linetypes):
            pattern = self._patterns.get(name, ())
            _groups(
                stream, (0, "LTYPE"), (2, name), (70, 0), (3, name), (72, 65),
                (73, len(pattern)), (40, sum(abs(length) for length in pattern)),
                *((49, length) for length in pattern),
            )
        _groups(stream, (0, "ENDTAB"), (0, "TABLE"), (2, "LAYER"), (70, len(layers)))
        for layer in layers:
            color = layer.color if 1 <= layer.color <= 255 else 7
            linetype = _linetype(layer.linetype)
            _groups(
                stream, (0, "LAYER"), (2, layer.name), (70, 0),
                (62, color if layer.visible else -color),
                (6, "CONTINUOUS" if linetype in _INHERITED_LINETYPES else linetype),
            )
        _groups(
            stream, (0, "ENDTAB"),
            (0, "TABLE"), (2, "STYLE"), (70, 1), (0, "STYLE"), (2, "STANDARD"),
            (70, 0), (40, 0.0), (41, 1.0), (50, 0.0), (71, 0), (42, 2.5),
            (3, "txt"), (4, ""), (0, "ENDTAB"), (0, "ENDSEC"),
        )

    @staticmethod
    def _write_primitive(stream: TextIO, primitive: Primitive, layer: str) -> None:
        kind = primitive.type
        points = primitive.points
        style = primitive.style
        if kind is PrimitiveType.POLYGON:
            polygon = Polygon([(point.x, point.y) for point in points])
            if not polygon.is_valid or not polygon.area:
                raise ValueError("DXF filled polygon must have a valid exterior and positive area")
            for triangle in constrained_delaunay_triangles(polygon).geoms:
                a, b, c = tuple(triangle.exterior.coords)[:3]
                _groups(
                    stream, (0, "SOLID"), (8, layer), (62, style.color),
                    *((10 + index, x) for index, (x, _) in enumerate((a, b, c, c))),
                    *((20 + index, y) for index, (_, y) in enumerate((a, b, c, c))),
                    *((30 + index, 0.0) for index in range(4)),
                )
            return
        _groups(
            stream, (0, kind.value), (8, layer), (62, style.color),
            (6, _linetype(style.linetype)),
        )
        if kind is PrimitiveType.LINE:
            start, end = points
            _groups(stream, *_xyz(start), *_xyz(end, 11))
        elif kind is PrimitiveType.POLYLINE:
            if len(points) < 2:
                raise ValueError("A DXF polyline requires at least two points")
            closed = primitive.closed or (len(points) > 2 and points[0] == points[-1])
            if closed and points[0] == points[-1]:
                points = points[:-1]
            _groups(stream, (66, 1), (10, 0.0), (20, 0.0), (30, 0.0), (70, int(closed)))
            for point in points:
                _groups(stream, (0, "VERTEX"), (8, layer), *_xyz(point), (70, 0))
            _groups(stream, (0, "SEQEND"), (8, layer))
        elif kind in (PrimitiveType.ARC, PrimitiveType.CIRCLE):
            if primitive.radius <= 0:
                raise ValueError("A DXF radius must be positive")
            _groups(stream, *_xyz(points[0]), (40, primitive.radius))
            if kind is PrimitiveType.ARC:
                _groups(stream, (50, primitive.start_angle % 360), (51, primitive.end_angle % 360))
        elif kind is PrimitiveType.TEXT:
            if primitive.text_height <= 0:
                raise ValueError("DXF text height must be positive")
            _groups(
                stream, *_xyz(points[0]), (40, primitive.text_height),
                (1, primitive.contents), (50, math.degrees(primitive.rotation)),
            )
