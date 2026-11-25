"""Analytic sampling of the idealized straight-lead / circular-arc turnout model.

Coordinates are centre-lines, not rails.  This is not catalogue turnout geometry.
"""
from __future__ import annotations
from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class SamplePoint:
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class TurnoutCurve:
    """Branch path between a main-line toe and the diagonal connector.

    reverse=False: toe -> connector, in increasing main-line station.
    reverse=True: connector -> toe, in increasing main-line station.
    The latter is the mirror of the former about the toe's normal axis.
    """
    toe: SamplePoint
    azimuth: float
    lead_length: float
    radius: float
    frog_angle: float
    side_sign: int
    reverse: bool = False

    def __post_init__(self):
        if self.side_sign not in (-1, 1):
            raise ValueError('side_sign must be -1 or +1')
        if self.lead_length < 0 or self.radius <= 0 or self.frog_angle <= 0:
            raise ValueError('invalid turnout geometry')

    def _local_to_world(self, x: float, y: float) -> SamplePoint:
        c, s = math.cos(self.azimuth), math.sin(self.azimuth)
        return SamplePoint(self.toe.x + x*c - y*s,
                           self.toe.y + x*s + y*c)

    @property
    def connector_point(self) -> SamplePoint:
        d = -1 if self.reverse else 1
        return self._local_to_world(d*(self.lead_length + self.radius*math.sin(self.frog_angle)),
                                    d*self.side_sign*self.radius*(1-math.cos(self.frog_angle)))

    def sample_points(self, step: float = 0.5) -> tuple[SamplePoint, ...]:
        """Return ordered points toe->connector (forward), connector->toe (reverse).

        step is maximum *arc length* of a circular-arc chord, in metres.
        """
        return tuple(point for point, _ in self.sample_frames(step))

    def sample_frames(self, step: float = 0.5) -> tuple[tuple[SamplePoint, float], ...]:
        """Sample points and their forward tangent azimuths in path order."""
        if not math.isfinite(step) or step <= 0:
            raise ValueError('step must be finite and > 0')
        direction = -1 if self.reverse else 1
        n_lead = max(1, math.ceil(self.lead_length / step))
        n_arc = max(1, math.ceil(self.radius*self.frog_angle / step))
        frames = [
            (self._local_to_world(direction*self.lead_length*i/n_lead, 0), self.azimuth)
            for i in range(n_lead+1)
        ]
        for i in range(1, n_arc+1):
            angle = self.frog_angle*i/n_arc
            point = self._local_to_world(
                direction*(self.lead_length+self.radius*math.sin(angle)),
                direction*self.side_sign*self.radius*(1-math.cos(angle)))
            frames.append((point, self.azimuth + self.side_sign*angle))
        return tuple(reversed(frames)) if self.reverse else tuple(frames)


@dataclass(frozen=True, slots=True)
class CompleteConnection:
    """A continuous path: first turnout + diagonal + second turnout."""
    name: str
    first: TurnoutCurve
    second: TurnoutCurve

    def sample_points(self, step: float = 0.5) -> tuple[SamplePoint, ...]:
        return tuple(point for point, _ in self.sample_frames(step))

    def sample_frames(self, step: float = 0.5) -> tuple[tuple[SamplePoint, float], ...]:
        """Sample the turnout curves and straight connector with forward tangents."""
        left = self.first.sample_frames(step)
        right = self.second.sample_frames(step)
        # The two turnout endpoints are joined by an analytic straight line.
        start, end = left[-1][0], right[0][0]
        dx, dy = end.x - start.x, end.y - start.y
        length = math.hypot(dx, dy)
        n = max(1, math.ceil(length/step))
        azimuth = math.atan2(dy, dx)
        middle = tuple(
            (SamplePoint(start.x + dx * i / n, start.y + dy * i / n), azimuth)
            for i in range(1, n)
        )
        return left + middle + right
