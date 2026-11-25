import math

import pytest

from myalignment.export.dxf_writer import DxfWriter
from myalignment.profile import (
    DepthLabel,
    ProfileBuilder,
    ProfileType,
    ProfileViewSplitConfig,
    ProfileViewSplitMethod,
    ProfileViewSplitter,
)
from myalignment.profile.band_style import VerticalGeometryBandStyle
from myalignment.profile.station_label import StationElevationLabel
from myalignment.profile.view_band import BandType, ProfileViewBand
from myalignment.profile.view_style import ProfileViewStyle
from myalignment.render.depth_label_renderer import DepthLabelRenderer
from myalignment.render.primitives import PrimitiveType
from myalignment.render.profile_view_renderer import ProfileViewRenderer
from myalignment.render.profile_view_split_composer import ProfileViewSplitComposer
from myalignment.render.profile_view_split_renderer import ProfileViewSplitRenderer
from myalignment.render.station_label_renderer import StationLabelRenderer


@pytest.fixture
def profile():
    return (
        ProfileBuilder("FG", ProfileType.FG)
        .add_tangent(1000, 1120, 99, 101.4)
        .add_symmetric_parabola(1150, 102, 0.02, -0.02, 60)
        .add_tangent(1180, 1220, 101.4, 100.6)
        .add_tangent(1220, 1300, 100.6, 102.2)
        .build()
    )


def _ranges(segments):
    return [(item.start_station, item.end_station) for item in segments]


def test_split_modes_and_real_pvi_boundaries(profile):
    config = ProfileViewSplitConfig(max_station_per_view=120, overlap_station=10, align_to_pvi=False)
    segments = ProfileViewSplitter.split(profile, config)
    assert _ranges(segments) == [(1000, 1110), (1090, 1210), (1190, 1300)]
    assert segments[1].contains(1090)
    assert [(item.view_index, item.total_views) for item in segments] == [(0, 3), (1, 3), (2, 3)]

    pvi = ProfileViewSplitConfig(method=ProfileViewSplitMethod.PVI_COUNT, max_pvi_per_view=1, overlap_station=0)
    assert _ranges(ProfileViewSplitter.split(profile, pvi)) == [(1000, 1150), (1150, 1300)]

    manual = ProfileViewSplitConfig(
        method=ProfileViewSplitMethod.MANUAL, manual_split_stations=(990, 1125, 1310), overlap_station=0,
    )
    assert _ranges(ProfileViewSplitter.split(profile, manual)) == [(1000, 1125), (1125, 1300)]
    none = ProfileViewSplitConfig(method=ProfileViewSplitMethod.NONE)
    assert _ranges(ProfileViewSplitter.split(profile, none)) == [(1000, 1300)]


def test_station_split_snaps_to_pvi_only_within_length_limits(profile):
    config = ProfileViewSplitConfig(max_station_per_view=180, min_view_length=120, overlap_station=0)
    assert _ranges(ProfileViewSplitter.split(profile, config)) == [(1000, 1150), (1150, 1300)]
    tighter = ProfileViewSplitConfig(max_station_per_view=125, min_view_length=80, overlap_station=0)
    assert all(80 <= item.length <= 125 for item in ProfileViewSplitter.split(profile, tighter))


@pytest.mark.parametrize("kwargs", [
    {"max_station_per_view": math.inf}, {"overlap_station": -1}, {"columns": 0},
    {"method": ProfileViewSplitMethod.MANUAL, "manual_split_stations": (1200, 1200)},
    {"method": ProfileViewSplitMethod.PVI_COUNT, "max_pvi_per_view": 1.5},
])
def test_invalid_split_inputs_are_rejected(kwargs):
    with pytest.raises(ValueError):
        ProfileViewSplitConfig(**kwargs)


def test_native_view_range_preserves_curve_ends_and_filters_band_and_labels(profile):
    scene = ProfileViewRenderer.render(
        [profile], "Main", ProfileViewStyle(vertical_exaggeration=3),
        bands=[ProfileViewBand(BandType.VERTICAL_GEOMETRY)],
        labels=[StationElevationLabel(1100), StationElevationLabel(1155)],
        depth_labels=[DepthLabel(1130, 1160), DepthLabel(1160, 1200)],
        render_labels=False,
        station_range=(1125, 1175),
    )
    curve = next(item for item in scene.primitives if item.style.layer == ProfileViewRenderer.FG_LAYER)
    assert curve.points[0].x == 1125 and curve.points[-1].x == 1175
    assert curve.points[0].y == pytest.approx(3 * profile.elevation_at(1125))
    assert curve.points[-1].y == pytest.approx(3 * profile.elevation_at(1175))
    labels = [item.text for item in scene.primitives if item.type is PrimitiveType.TEXT
              and item.style.layer == StationLabelRenderer.LAYER]
    assert labels[0] == "STA 1155.00" and len(labels) == 2
    depth = [item.text for item in scene.primitives if item.type is PrimitiveType.TEXT
             and item.style.layer == DepthLabelRenderer.LAYER]
    assert depth[0] == "STA 1130.00 → 1160.00" and len(depth) == 4
    band = [item for item in scene.primitives if item.style.layer == VerticalGeometryBandStyle().layer]
    assert (band[0].points[0].x, band[0].points[1].x) == (1125, 1175)
    vertical_ticks = [item.points[0].x for item in band if item.type is PrimitiveType.LINE
                      and item.points[0].x == item.points[1].x]
    assert vertical_ticks and set(vertical_ticks) == {1150}


def test_split_layout_uses_local_plot_sizes_and_exports_dxf(profile, tmp_path):
    config = ProfileViewSplitConfig(
        method=ProfileViewSplitMethod.MANUAL, manual_split_stations=(1115, 1200),
        overlap_station=5, columns=2, column_gap=17, row_gap=22, include_start_label=False,
    )
    scene = ProfileViewSplitComposer.compose(
        [profile], "Main", ProfileViewStyle(vertical_exaggeration=3), config,
        bands=[ProfileViewBand(BandType.PROFILE_DATA)],
    )
    panels = scene.metadata["panels"]
    assert scene.metadata["view_count"] == 3
    first, second, third = (panel["bounds"] for panel in panels)
    assert second[0] - first[2] >= 17 - 1e-8
    assert min(first[1], second[1]) - third[3] >= 22 - 1e-8
    assert first[3] == pytest.approx(second[3])
    for panel, line in zip(panels, [p for p in scene.primitives if p.style.layer == ProfileViewRenderer.FG_LAYER]):
        start, end = panel["start_station"], panel["end_station"]
        dx, dy = panel["translation"]
        assert (line.points[0].x - dx, line.points[-1].x - dx) == pytest.approx((start, end))
        assert line.points[0].y - dy == pytest.approx(3 * profile.elevation_at(start))
    assert sum(p.style.layer == ProfileViewSplitRenderer.OVERLAP_LAYER for p in scene.primitives) == 4
    assert [p.text for p in scene.primitives if p.style.layer == ProfileViewSplitRenderer.INDEX_LAYER] == [
        "VIEW 1/3", "VIEW 2/3", "VIEW 3/3",
    ]
    dxf = tmp_path / "split.dxf"
    DxfWriter(scene).write(dxf)
    assert "VIEW 3/3" in dxf.read_text(encoding="cp949")


def test_split_covers_all_profiles_even_across_empty_panels():
    first = ProfileBuilder("First").add_tangent(100, 200, 31, 32).build()
    second = ProfileBuilder("Second").add_tangent(400, 500, 41, 42).build()
    scene = ProfileViewSplitRenderer.render(
        [first, second], "Main",
        ProfileViewStyle(grid_major_interval_elevation=100, grid_minor_interval_elevation=50),
        ProfileViewSplitConfig(max_station_per_view=100, overlap_station=0),
    )
    assert scene.metadata["view_count"] == 4
    assert scene.metadata["panels"][-1]["end_station"] == 500
    assert sum(p.style.layer == ProfileViewRenderer.EG_LAYER for p in scene.primitives) == 2
