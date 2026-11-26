from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from myalignment.alignment.profile_geometry_label import ProfileGeometryLabel
from myalignment.alignment.profile_geometry_label_type import ProfileGeometryPointLabelType as Kind
from myalignment.profile.vertical_geometry_extractor import VerticalGeometryExtractor
from myalignment.profile.vertical_geometry_type import VerticalGeometryPointType

if TYPE_CHECKING:
    from myalignment.profile.profile import Profile


class ProfileGeometryLabelExtractor:
    """공통 종단 기하점으로부터 평면 선형의 레이블 데이터를 추출한다."""

    TYPE_MAP = {
        VerticalGeometryPointType.PVI: Kind.PVI,
        VerticalGeometryPointType.VPC: Kind.VPC,
        VerticalGeometryPointType.VPT: Kind.VPT,
        VerticalGeometryPointType.HIGH_POINT: Kind.HIGH_POINT,
        VerticalGeometryPointType.LOW_POINT: Kind.LOW_POINT,
        VerticalGeometryPointType.GRADE_BREAK: Kind.GRADE_BREAK,
    }

    @classmethod
    def extract(
        cls, profile: Profile, labeled_points: Iterable[Kind] | None = None,
    ) -> list[ProfileGeometryLabel]:
        """종단 시작·끝을 내부 PVI와 구분하고 선택한 유형을 반환한다."""
        if not profile.is_valid:
            return []
        allowed = set(Kind if labeled_points is None else labeled_points)
        labels = []
        first, last = profile.entities[0], profile.entities[-1]
        if Kind.PROFILE_START in allowed:
            labels.append(ProfileGeometryLabel(
                Kind.PROFILE_START, first.start_station, first.start_elevation,
                grade_out=first.start_grade, profile_name=profile.name,
            ))
        if Kind.PROFILE_END in allowed:
            labels.append(ProfileGeometryLabel(
                Kind.PROFILE_END, last.end_station, last.end_elevation,
                grade_in=last.end_grade, profile_name=profile.name,
            ))
        for point in VerticalGeometryExtractor.extract(profile):
            kind = cls.TYPE_MAP.get(point.point_type)
            if kind not in allowed:
                continue
            if kind is Kind.PVI and point.station in (first.start_station, last.end_station):
                continue
            labels.append(ProfileGeometryLabel(
                kind, point.station, point.elevation, point.grade_in, point.grade_out,
                profile.name, point.curve_length, point.radius / 100 if point.curve_length else None,
            ))
        return sorted(labels, key=lambda label: (label.station, label.point_type.value))
