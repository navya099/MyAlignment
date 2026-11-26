from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from myalignment.pressure.appurtenance import PressureAppurtenance
from myalignment.pressure.cover import _minimum_covers
from myalignment.pressure.fitting import PressureFitting
from myalignment.pressure.part import _positive
from myalignment.pressure.pipe import PressurePipe

if TYPE_CHECKING:
    from myalignment.surface.tin_surface import TinSurface


_CONNECTION_TOLERANCE = 1e-8


def _pipe_connections(pipe):
    return (
        ("start", pipe.start_point, pipe.start_fitting_id, pipe.start_appurtenance_id),
        ("end", pipe.end_point, pipe.end_fitting_id, pipe.end_appurtenance_id),
    )


def _resolve_endpoint_claims(pipe, claims):
    updates = {}
    for side, point, fitting_id, app_id in _pipe_connections(pipe):
        if point is None or fitting_id or app_id:
            continue
        candidates = [
            (field, node.id) for field, node in claims
            if node.location is not None and point.distance_to(node.location) <= _CONNECTION_TOLERANCE
        ]
        if len(candidates) == 1:
            field, node_id = candidates[0]
            updates[f"{side}_{field}_id"] = node_id
    return replace(pipe, **updates) if updates else pipe


@dataclass(frozen=True, slots=True)
class PressureNetwork:
    """피팅, 부속품과 관 중심선을 관리하는 불변 압력관망."""

    name: str = "PressureNetwork1"
    pipes: tuple[PressurePipe, ...] = ()
    fittings: tuple[PressureFitting, ...] = ()
    appurtenances: tuple[PressureAppurtenance, ...] = ()
    parts_list_name: str = ""
    reference_alignment: str = ""
    reference_surface: str = ""
    pressure_rating_psi: float = 150.0
    cover_sampled: bool = False

    def __post_init__(self):
        _positive(self.pressure_rating_psi, "pressure_rating_psi")
        pipes = tuple(self.pipes)
        fittings = tuple(self.fittings)
        appurtenances = tuple(self.appurtenances)
        ids = [item.id for item in (*pipes, *fittings, *appurtenances)]
        if any(not value.strip() for value in ids) or len(set(ids)) != len(ids):
            raise ValueError("Pressure network part IDs must be nonempty and unique")

        claims = defaultdict(list)
        for field, nodes in (("fitting", fittings), ("appurtenance", appurtenances)):
            for node in nodes:
                for pipe_id in node.connected_pipe_ids:
                    claims[pipe_id].append((field, node))
        pipes = tuple(_resolve_endpoint_claims(pipe, claims[pipe.id]) for pipe in pipes)
        fitting_ids = {node.id for node in fittings}
        app_ids = {node.id for node in appurtenances}
        links = defaultdict(list)
        for pipe in pipes:
            for _, _, fitting_id, app_id in _pipe_connections(pipe):
                if fitting_id in fitting_ids or app_id in app_ids:
                    links[fitting_id or app_id].append(pipe.id)
        object.__setattr__(self, "pipes", pipes)
        for field, nodes in (("fittings", fittings), ("appurtenances", appurtenances)):
            object.__setattr__(self, field, tuple(
                replace(node, connected_pipe_ids=(*node.connected_pipe_ids, *links[node.id]))
                for node in nodes
            ))

    def __len__(self) -> int:
        return len(self.pipes) + len(self.fittings) + len(self.appurtenances)

    def get_pipe(self, pipe_id: str) -> PressurePipe | None:
        return next((pipe for pipe in self.pipes if pipe.id == pipe_id), None)

    def get_fitting(self, fitting_id: str) -> PressureFitting | None:
        return next((fitting for fitting in self.fittings if fitting.id == fitting_id), None)

    def get_appurtenance(self, appurtenance_id: str) -> PressureAppurtenance | None:
        return next((app for app in self.appurtenances if app.id == appurtenance_id), None)

    @property
    def total_pipe_length(self) -> float:
        return sum(pipe.length for pipe in self.pipes)

    @property
    def min_cover(self) -> float | None:
        """지표면이 전체 길이를 덮는 관 중 최소 토피."""
        return min((pipe.cover for pipe in self.pipes if pipe.cover is not None), default=None)

    def add_pipe(self, pipe: PressurePipe) -> PressureNetwork:
        return replace(self, pipes=(*self.pipes, pipe))

    def add_fitting(self, fitting: PressureFitting) -> PressureNetwork:
        return replace(self, fittings=(*self.fittings, fitting))

    def add_appurtenance(self, app: PressureAppurtenance) -> PressureNetwork:
        return replace(self, appurtenances=(*self.appurtenances, app))

    def with_cover_from(self, surface: TinSurface) -> PressureNetwork:
        """TIN 위쪽 표고와 외측 관정고로 관별 최소 토피를 평가한다."""
        return replace(
            self, cover_sampled=True, reference_surface=surface.name or self.reference_surface,
            pipes=tuple(
                replace(pipe, cover=cover, surface_name=surface.name or pipe.surface_name or self.reference_surface)
                for pipe, cover in zip(self.pipes, _minimum_covers(self.pipes, surface), strict=True)
            ),
        )
