from __future__ import annotations

from collections import defaultdict
import math
from typing import TYPE_CHECKING

from myalignment.pressure.network import _CONNECTION_TOLERANCE, _pipe_connections
from myalignment.pressure.part import FittingPart, FittingType

if TYPE_CHECKING:
    from myalignment.pressure.network import PressureNetwork
    from myalignment.surface.tin_surface import TinSurface


def _turn_angle(first, second):
    ax, ay, az = first
    bx, by, bz = second
    dot = ax * bx + ay * by + az * bz
    cross = math.hypot(ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx)
    return math.degrees(math.atan2(cross, -dot))


def _matches_diameter(a, b):
    return math.isclose(a, b, rel_tol=0, abs_tol=1e-6)


def _node_errors(node, ports, max_deflection):
    part = node.part
    label = f"{part.fitting_type.value if isinstance(part, FittingPart) else part.appurtenance_type.value} {node.name!r}"
    if len(ports) != part.port_count:
        yield f"{label}: expected {part.port_count} connected ports, found {len(ports)}"
    diameters = tuple(pipe.part.nominal_diameter_mm for pipe, _ in ports)
    if isinstance(part, FittingPart) and part.fitting_type is FittingType.REDUCER:
        if len(diameters) == 2:
            small, large = sorted(diameters)
            if (not any(_matches_diameter(part.diameter_mm, d) for d in diameters)
                    or _matches_diameter(small, large)
                    or (part.outlet_diameter_mm is not None
                        and not any(_matches_diameter(part.outlet_diameter_mm, d) for d in diameters))):
                yield f"{label}: reducer requires compatible, different nominal diameters"
    elif any(not _matches_diameter(d, part.diameter_mm) for d in diameters):
        yield f"{label}: incompatible nominal diameter"

    if part.port_count == len(ports) == 2:
        angle = _turn_angle(ports[0][1], ports[1][1])
        target = 0.0
        if isinstance(part, FittingPart):
            max_deflection = min(max_deflection, part.max_deflection_deg)
            if part.fitting_type is FittingType.BEND:
                target = part.angle_deg
        residual = abs(angle - target)
        if residual > max_deflection + 1e-8:
            yield (f"{label}: deflection {residual:.2f}° exceeds {max_deflection:g}° "
                   f"(axis turn {angle:.2f}°, nominal {target:g}°)")


class PressureNetworkValidator:
    """압력관망의 연결, 치수, 토피 및 관 축 편향을 검사한다."""

    MIN_COVER = 0.9
    MAX_DEFLECTION = 11.25
    MIN_PIPE_LENGTH = 1.0

    @classmethod
    def validate(
        cls, network: PressureNetwork, surface: TinSurface | None = None, *,
        min_cover: float = MIN_COVER, max_deflection: float = MAX_DEFLECTION,
        min_pipe_length: float = MIN_PIPE_LENGTH,
    ) -> list[str]:
        if not all(math.isfinite(value) and value >= 0 for value in (min_cover, max_deflection, min_pipe_length)):
            raise ValueError("Design check limits must be finite and nonnegative")
        if max_deflection > 180:
            raise ValueError("max_deflection cannot exceed 180 degrees")
        if surface is not None:
            network = network.with_cover_from(surface)
        check_surface = network.cover_sampled or bool(network.reference_surface)
        fittings = {node.id: node for node in network.fittings}
        apps = {node.id: node for node in network.appurtenances}
        pipe_ids = {pipe.id for pipe in network.pipes}
        ports = defaultdict(list)
        linked = defaultdict(set)
        errors = []
        for pipe in network.pipes:
            label = f"Pipe {pipe.name!r}"
            length = pipe.length
            if not pipe.centerline:
                errors.append(f"{label}: missing centerline endpoint")
            elif not math.isfinite(length) or length <= _CONNECTION_TOLERANCE:
                errors.append(f"{label}: positive finite 3D length is required")
            elif length < min_pipe_length - 1e-8:
                errors.append(f"{label}: length {length:.3f} m is below {min_pipe_length:g} m")
            if pipe.part.pressure_rating_psi < network.pressure_rating_psi:
                errors.append(f"{label}: pressure rating is below the network design pressure")
            if pipe.cover is not None and pipe.cover < min_cover - 1e-8:
                errors.append(f"{label}: cover {pipe.cover:.3f} m is below {min_cover:g} m")
            elif pipe.cover is None and (check_surface or pipe.surface_name):
                errors.append(f"{label}: surface coverage is incomplete")

            start_id = pipe.start_fitting_id or pipe.start_appurtenance_id
            end_id = pipe.end_fitting_id or pipe.end_appurtenance_id
            if start_id and start_id == end_id:
                errors.append(f"{label}: both ends reference the same node")
            for side, point, fitting_id, app_id in _pipe_connections(pipe):
                if not fitting_id and not app_id:
                    continue
                nodes = fittings if fitting_id else apps
                node_id = fitting_id or app_id
                node = nodes.get(node_id)
                if node is None:
                    errors.append(f"{label}: unknown {side} connection {node_id!r}")
                    continue
                linked[node_id].add(pipe.id)
                if point is None or node.location is None or point.distance_to(node.location) > _CONNECTION_TOLERANCE:
                    errors.append(f"{label}: {side} endpoint does not coincide with {node.name!r}")
                    continue
                if math.isfinite(length) and length > _CONNECTION_TOLERANCE:
                    other = pipe.end_point if side == "start" else pipe.start_point
                    ports[node_id].append((pipe, (
                        (other.x - point.x) / length, (other.y - point.y) / length, (other.z - point.z) / length,
                    )))

        for node in (*network.fittings, *network.appurtenances):
            if node.location is None:
                errors.append(f"Node {node.name!r}: missing location")
            for pipe_id in node.connected_pipe_ids:
                if pipe_id not in pipe_ids:
                    errors.append(f"Node {node.name!r}: unknown connected pipe {pipe_id!r}")
                elif pipe_id not in linked[node.id]:
                    errors.append(f"Node {node.name!r}: pipe {pipe_id!r} has no matching endpoint reference")
            errors.extend(_node_errors(node, ports[node.id], max_deflection))
        return errors

    @classmethod
    def is_valid(
        cls, network: PressureNetwork, surface: TinSurface | None = None, *,
        min_cover: float = MIN_COVER, max_deflection: float = MAX_DEFLECTION,
        min_pipe_length: float = MIN_PIPE_LENGTH,
    ) -> bool:
        return not cls.validate(
            network, surface, min_cover=min_cover, max_deflection=max_deflection, min_pipe_length=min_pipe_length,
        )
