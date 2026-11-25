from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from myalignment.render.profile_view_split_renderer import ProfileViewSplitRenderer
from myalignment.render.scene import Scene

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.profile.depth_label import DepthLabel
    from myalignment.profile.profile import Profile
    from myalignment.profile.station_label import StationElevationLabel
    from myalignment.profile.view_band import ProfileViewBand
    from myalignment.profile.view_split_config import ProfileViewSplitConfig
    from myalignment.profile.view_style import ProfileViewStyle
    from myalignment.render.stagger_config import StaggerConfig


class ProfileViewSplitComposer:
    """분할 종단 뷰와 밴드, 레이블을 한 장면으로 구성한다."""

    @classmethod
    def compose(
        cls,
        profiles: Sequence[Profile],
        alignment_name: str,
        view_style: ProfileViewStyle,
        split_config: ProfileViewSplitConfig,
        alignment: Alignment | None = None,
        bands: Sequence[ProfileViewBand] | None = None,
        labels: Sequence[StationElevationLabel] | None = None,
        depth_labels: Sequence[DepthLabel] | None = None,
        stagger_config: StaggerConfig | None = None,
        **view_options,
    ) -> Scene:
        """각 패널에서 밴드와 레이블을 배치하고 겹침 방지를 적용한다."""
        return ProfileViewSplitRenderer.render(
            profiles, alignment_name, view_style, split_config, alignment, bands, labels, depth_labels,
            stagger_config=stagger_config, **view_options,
        )
