from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from myalignment.corridor.mesh_mode import MeshMode
from myalignment.drive.drive_config import DriveViewConfig
from myalignment.drive.drive_generator import DriveViewGenerator
from myalignment.export.drive_html_exporter import DriveViewHTMLExporter

if TYPE_CHECKING:
    from myalignment.alignment.alignment import Alignment
    from myalignment.corridor.corridor import Corridor
    from myalignment.profile.profile import Profile


class DriveViewPreview:
    """선형과 선택한 코리더에서 재생 가능한 주행 뷰를 만든다."""

    @staticmethod
    def preview(
        alignment: Alignment, config: DriveViewConfig, html_path: str | Path, corridor: Corridor | None = None,
        surface_elevation_func: Callable[[float, float], float] | None = None, *,
        profile: Profile | None = None, baseline_name: str | None = None, three_module_base: str | None = None,
    ) -> str:
        """코리더가 있으면 배경에 메시를 표시하고 HTML 경로를 반환한다."""
        grade = profile
        if grade is None and corridor is not None:
            names = {
                baseline.profile_name for baseline in corridor.baselines
                if baseline.alignment_name == alignment.name
                and (baseline_name is None or baseline.name == baseline_name)
            }
            if len(names) == 1:
                name = next(iter(names))
                grade = next((item for item in alignment.profiles if item.name == name), None)
        path = DriveViewGenerator.generate(alignment, config, surface_elevation_func, profile=grade)
        scene = None
        if corridor is not None:
            scene = corridor.build_3d_mesh(
                alignment, MeshMode.QUAD_STRIP, config.sample_interval, profile=profile, baseline_name=baseline_name,
            )
        DriveViewHTMLExporter.export(
            path, html_path, title=f"3D Drive View — {alignment.name}", scene=scene,
            three_module_base=three_module_base,
        )
        return str(html_path)
