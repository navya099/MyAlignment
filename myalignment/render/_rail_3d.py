"""Shared 3D primitives for paired rails and their markers."""
from collections.abc import Iterator, Sequence
from itertools import repeat
import math

from cadgeom import Point2d

from myalignment.render.primitives_3d import Point3D, Primitive3D, Style3D


def rail_top(elevation: float, rail_elevation: float, tie_spacing: float) -> float:
    top = elevation + rail_elevation
    if not math.isfinite(top) or rail_elevation < 0:
        raise ValueError("elevation and rail_elevation must be finite; rail_elevation must be nonnegative")
    if not math.isfinite(tie_spacing) or tie_spacing <= 0:
        raise ValueError("tie_spacing must be finite and positive")
    return top


def rail_polylines(
    left: Sequence[Point2d], right: Sequence[Point2d], elevation: float, style: Style3D,
    *, levels: Sequence[float] | None = None,
) -> Iterator[Primitive3D]:
    if levels is not None and (len(left) != len(levels) or len(right) != len(levels)):
        raise ValueError("track elevations must match both rail sample counts")
    for rail in (left, right):
        if len(rail) >= 2:
            offsets = repeat(0.0, len(rail)) if levels is None else levels
            yield Primitive3D.polyline(
                (Point3D(p.x, p.y, elevation + dz) for p, dz in zip(rail, offsets, strict=True)), style=style,
            )


def rail_ties(
    left: Sequence[Point2d],
    right: Sequence[Point2d],
    elevation: float,
    spacing: float,
    style: Style3D,
    *,
    overhang: float,
    levels: Sequence[float] | None = None,
) -> Iterator[Primitive3D]:
    if len(left) != len(right):
        raise ValueError("rails must have matching samples for ties")

    travelled = 0.0
    index = 0
    for segment, (l0, l1, r0, r1) in enumerate(zip(left, left[1:], right, right[1:])):
        length = math.hypot(((l1.x - l0.x) + (r1.x - r0.x)) / 2,
                            ((l1.y - l0.y) + (r1.y - r0.y)) / 2)
        if length == 0:
            continue
        end = travelled + length
        while index * spacing <= end:
            fraction = (index * spacing - travelled) / length
            lx, ly = l0.x + (l1.x - l0.x) * fraction, l0.y + (l1.y - l0.y) * fraction
            rx, ry = r0.x + (r1.x - r0.x) * fraction, r0.y + (r1.y - r0.y) * fraction
            width = math.hypot(lx - rx, ly - ry)
            if width > 0:
                dx = overhang * (lx - rx) / width
                dy = overhang * (ly - ry) / width
                z = elevation
                if levels is not None:
                    z += (1 - fraction) * levels[segment] + fraction * levels[segment + 1]
                yield Primitive3D.line(
                    Point3D(lx + dx, ly + dy, z), Point3D(rx - dx, ry - dy, z), style,
                )
            index += 1
        travelled = end


def vertical_marker(point: Point2d, elevation: float, height: float, style: Style3D) -> Primitive3D:
    return Primitive3D.line(
        Point3D(point.x, point.y, elevation), Point3D(point.x, point.y, elevation + height), style,
    )
