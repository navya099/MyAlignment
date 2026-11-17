# profile/profile_tangent.py
from __future__ import annotations
from dataclasses import dataclass

from myalignment.profile.profileentity import ProfileEntity
from myalignment.profile.profileentitytype import ProfileEntityType


@dataclass(frozen=True, slots=True)
class ProfileTangent(ProfileEntity):
    """직선 종단 요소 (Tangent)."""
    entity_type: ProfileEntityType = ProfileEntityType.Tangent

    @classmethod
    def create(
        cls,
        start_station: float,
        end_station: float,
        start_elevation: float,
        end_elevation: float,
    ) -> "ProfileTangent":
        return cls(
            start_station=start_station,
            end_station=end_station,
            start_elevation=start_elevation,
            end_elevation=end_elevation,
        )

    @property
    def grade(self) -> float:
        if self.length <= 0:
            return 0.0
        return (self.end_elevation - self.start_elevation) / self.length

    def elevation_at(self, station: float) -> float:
        s = self._clamp_station(station) - self.start_station
        return self.start_elevation + self.grade * s

    def grade_at(self, station: float) -> float:
        return self.grade

    def reversed(self, total_length: float) -> "ProfileTangent":
        L = total_length
        return ProfileTangent.create(
            start_station=L - self.end_station,
            end_station=L - self.start_station,
            start_elevation=self.end_elevation,
            end_elevation=self.start_elevation,
        )