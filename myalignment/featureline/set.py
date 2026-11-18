# featureline/set.py
from __future__ import annotations
from dataclasses import dataclass, field
from myalignment.featureline.feature_line import FeatureLine


@dataclass(frozen=True, slots=True)
class FeatureLineSet:
    """FeatureLine 집합 (불변)."""
    feature_lines: tuple[FeatureLine, ...] = field(default_factory=tuple)

    def __len__(self) -> int:
        return len(self.feature_lines)

    def __iter__(self):
        return iter(self.feature_lines)

    def by_site(self, site_id: str) -> tuple[FeatureLine, ...]:
        return tuple(fl for fl in self.feature_lines if fl.site_id == site_id)

    def total_length_3d(self) -> float:
        return sum(fl.length_3d for fl in self.feature_lines)

    def add(self, fl: FeatureLine) -> "FeatureLineSet":
        return FeatureLineSet(feature_lines=self.feature_lines + (fl,))

    def remove(self, name: str) -> "FeatureLineSet":
        return FeatureLineSet(
            feature_lines=tuple(fl for fl in self.feature_lines if fl.name != name)
        )

    def __repr__(self) -> str:
        return f"FeatureLineSet(n={len(self.feature_lines)}, L3D={self.total_length_3d():.1f}m)"