from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from fractions import Fraction
from itertools import chain
import math
from typing import TYPE_CHECKING

from cadgeom import Point2d

from myalignment.surface.contour_line import ContourLine, ContourSet
from myalignment.surface.contour_style import ContourStyle
from myalignment.surface.contour_type import ContourType

if TYPE_CHECKING:
    from myalignment.surface.tin_surface import TinSurface


def _multiples(low, high, interval):
    first, last = math.ceil(low / interval), math.floor(high / interval)
    return (index * interval for index in range(first, last + 1))


def _elevation_levels(low, high, style):
    low, high = Fraction(str(_neighbor(low, -math.inf))), Fraction(str(_neighbor(high, math.inf)))
    major = Fraction(str(style.major_interval))
    levels = {}
    if style.show_minor:
        minor = Fraction(str(style.minor_interval))
        levels.update((float(z), ContourType.MINOR) for z in _multiples(low, high, minor) if z % major)
    if style.show_major:
        levels.update((float(z), ContourType.MAJOR) for z in _multiples(low, high, major))
    levels.update((z, ContourType.USER) for z in style.user_contours if low <= Fraction(str(z)) <= high)
    distinct = {}
    priority = {ContourType.MINOR: 0, ContourType.MAJOR: 1, ContourType.USER: 2}
    for elevation, kind in sorted(levels.items()):
        previous = next(reversed(distinct), None)
        if previous is not None and _same_level(previous, elevation):
            if priority[kind] > priority[distinct[previous]]:
                del distinct[previous]
                distinct[elevation] = kind
        else:
            distinct[elevation] = kind
    return distinct


def _neighbor(value, direction):
    boundary = math.nextafter(value, direction)
    return boundary if math.isfinite(boundary) else value


def _level_ranges(bounds):
    intervals = iter(sorted(bounds))
    low, high = next(intervals)
    for start, end in intervals:
        if start <= high or _same_level(start, high):
            high = max(high, end)
        else:
            yield low, high
            low, high = start, end
    yield low, high


def _same_level(a, b):
    return abs(a - b) <= max(math.ulp(a), math.ulp(b))


def _edge(a, b):
    return (a, b) if a < b else (b, a)


class _ContourGraph:
    def __init__(self):
        self.positions = {}
        self.segments = {}
        self.plateau_edges = Counter()

    def add_triangle(self, indices, points, elevation):
        prior = indices[-1]
        on_level = {index for index in indices if _same_level(points[index].z, elevation)}
        hits = {}
        on_plane = []
        for current in indices:
            a, b = points[prior], points[current]
            if current in on_level:
                key = (current, current)
                on_plane.append(key)
                hits[key] = (b.x, b.y)
            if prior not in on_level and current not in on_level and min(a.z, b.z) < elevation < max(a.z, b.z):
                key = _edge(prior, current)
                if key not in self.positions:
                    p, q = (points[index] for index in key)
                    fraction = (elevation - p.z) / (q.z - p.z)
                    self.positions[key] = (p.x + fraction * (q.x - p.x), p.y + fraction * (q.y - p.y))
                hits[key] = self.positions[key]
            prior = current
        if len(on_plane) == 3:
            self.positions.update(hits)
            self.plateau_edges.update(_edge(a, b) for a, b in zip(on_plane, (*on_plane[1:], on_plane[0])))
        elif len(hits) == 2:
            self.positions.update(hits)
            self.segments.setdefault(_edge(*hits), None)

    def paths(self):
        adjacent = defaultdict(dict)
        perimeter = (edge for edge, count in self.plateau_edges.items() if count == 1)
        for a, b in chain(self.segments, perimeter):
            if self.plateau_edges.get((a, b), 0) > 1 or self.positions[a] == self.positions[b]:
                continue
            adjacent[a][b] = None
            adjacent[b][a] = None
        unused = {_edge(a, b): None for a, neighbors in adjacent.items() for b in neighbors}

        def walk(start, neighbor):
            chain = [start]
            current = start
            while True:
                del unused[_edge(current, neighbor)]
                current = neighbor
                if current == start:
                    return chain, True
                chain.append(current)
                if len(adjacent[current]) != 2:
                    return chain, False
                next_node = next((b for b in adjacent[current] if _edge(current, b) in unused), None)
                if next_node is None:
                    return chain, False
                neighbor = next_node

        for start, neighbors in adjacent.items():
            if len(neighbors) != 2:
                for neighbor in neighbors:
                    if _edge(start, neighbor) in unused:
                        yield walk(start, neighbor)
        while unused:
            yield walk(*next(iter(unused)))


class ContourGenerator:
    """TIN의 삼각형과 수평면의 교선을 실제 메시 접속 관계로 연결한다."""

    @staticmethod
    def generate(surface: TinSurface, style: ContourStyle | None = None) -> ContourSet:
        if not surface.triangles:
            return ContourSet()
        style = style or ContourStyle.standard()
        points = surface.points
        triangles = dict.fromkeys(tuple(sorted((tri.a, tri.b, tri.c))) for tri in surface.triangles)
        bounds = []
        for face in triangles:
            elevations = [points[index].z for index in face]
            bounds.append((min(elevations), max(elevations)))
        kinds = {
            elevation: kind for low, high in _level_ranges(bounds)
            for elevation, kind in _elevation_levels(low, high, style).items()
        }
        levels = sorted(kinds)
        graphs = {}
        for face, (low, high) in zip(triangles, bounds):
            first = bisect_left(levels, _neighbor(low, -math.inf))
            end = bisect_right(levels, _neighbor(high, math.inf))
            for elevation in levels[first:end]:
                graph = graphs.get(elevation)
                if graph is None:
                    graph = graphs[elevation] = _ContourGraph()
                graph.add_triangle(face, points, elevation)

        contours = []
        for elevation in levels:
            graph = graphs.get(elevation)
            if graph is None:
                continue
            for nodes, closed in graph.paths():
                path = tuple(Point2d(*graph.positions[node]) for node in nodes)
                contours.append(ContourLine(elevation, kinds[elevation], path, closed))
        return ContourSet(tuple(contours))
