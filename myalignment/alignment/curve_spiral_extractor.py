from __future__ import annotations

import math
from typing import TYPE_CHECKING

from myalignment.enitity.arc_entity import ArcEntity
from myalignment.enitity.spiral_entity import SpiralEntity
from myalignment.enum.spiraltype import SpiralType
from myalignment.profile.geometry_extractor import GeometryPointExtractor

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment


def _curve_parameters(entity: ArcEntity) -> dict[str, float | None]:
    radius, delta = entity.geometry.radius, entity.geometry.delta
    half = delta / 2
    middle = 2 * radius * math.sin(half / 2) ** 2
    return {
        "radius": radius, "delta": delta, "length": entity.length,
        "tangent": radius * math.tan(half) if delta < math.pi else None,
        "external": middle / math.cos(half) if delta < math.pi else None,
        "mid_ordinate": middle, "chord": 2 * radius * math.sin(half),
    }


def _spiral_parameters(entity: SpiralEntity) -> dict:
    geometry = entity.geometry
    return {
        "radius": geometry.radius, "length": entity.length,
        "a_value": (
            math.sqrt(geometry.params.length) * math.sqrt(geometry.params.radius)
            if geometry.spiral_type in (SpiralType.Clothoid, SpiralType.OffsetClothoid) else None
        ),
        "theta": abs(entity.end_azimuth - entity.start_azimuth),
        "spiral_type": geometry.spiral_type.name,
    }


class CurveSpiralExtractor:
    """평면선형의 원곡선과 완화곡선 제원을 읽는다."""

    @staticmethod
    def extract_curves(alignment: Alignment) -> list[dict]:
        """원곡선의 측점, 좌표와 제원을 원시 측점 순서로 반환한다."""
        return [
            {
                **_curve_parameters(entity), "entity": entity,
                "start_station": entity.start_station, "end_station": entity.end_station,
                "mid_station": entity.start_station + entity.length / 2,
                "bc_point": entity.start_coord, "ec_point": entity.end_coord,
            }
            for entity in alignment.entities if isinstance(entity, ArcEntity)
        ]

    @staticmethod
    def extract_spirals(alignment: Alignment) -> list[dict]:
        """완화곡선의 제원과 실제 인접 요소에 해당하는 전이 측점을 반환한다."""
        transitions = {point.station: point.point_type.value for point in GeometryPointExtractor.extract(alignment)}
        result = []
        entities = alignment.entities.entities
        for index, entity in enumerate(entities):
            if not isinstance(entity, SpiralEntity):
                continue
            start, end = entity.start_station, entity.end_station
            before = transitions.get(entities[index - 1].end_station) if index else None
            after = transitions.get(end)
            endpoint = entity.end_coord
            dx, dy = endpoint.x - entity.start_coord.x, endpoint.y - entity.start_coord.y
            cos, sin = math.cos(entity.start_azimuth), math.sin(entity.start_azimuth)
            result.append({
                **_spiral_parameters(entity), "entity": entity, "start_station": start,
                "end_station": end, "mid_station": start + entity.length / 2,
                "x": dx * cos + dy * sin, "y": -dx * sin + dy * cos,
                "is_entry": before == "TS" and after == "SC",
                "is_exit": before == "CS" and after == "ST",
                "ts_station": start if before == "TS" else None,
                "sc_station": end if after == "SC" else None,
                "cs_station": start if before == "CS" else None,
                "st_station": end if after == "ST" else None,
            })
        return result

    @staticmethod
    def format_angle(radians: float, format: str = "dms") -> str:
        """라디안을 십진도 또는 도·분·초 문자열로 변환한다."""
        if not math.isfinite(radians):
            raise ValueError("angle must be finite")
        degrees = math.degrees(radians)
        if format == "decimal":
            return f"{degrees:.4f}°"
        if format != "dms":
            raise ValueError("angle_format must be dms or decimal")
        tenths = round(abs(degrees) * 36000)
        degree, remainder = divmod(tenths, 36000)
        minute, seconds = divmod(remainder, 600)
        sign = "-" if degrees < 0 and tenths else ""
        return f"{sign}{degree}°{minute:02d}'{seconds / 10:04.1f}\""
