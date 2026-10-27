from dataclasses import dataclass

from .profileentity import ProfileEntity

@dataclass
class ProfileTangent(ProfileEntity):
    grade: float = 0.0
