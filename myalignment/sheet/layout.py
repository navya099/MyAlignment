from __future__ import annotations

from dataclasses import dataclass, replace
import math

from myalignment.sheet.sheet_size import SheetSize


@dataclass(frozen=True, slots=True)
class Viewport:
    """시트의 좌하단 배치점, 크기(mm)와 1:N 축척의 분모."""

    name: str = ""
    x_mm: float = 0.0
    y_mm: float = 0.0
    width_mm: float = 0.0
    height_mm: float = 0.0
    scale: float = 500.0

    def __post_init__(self):
        if not all(map(math.isfinite, (self.x_mm, self.y_mm, self.width_mm, self.height_mm, self.scale))):
            raise ValueError("Viewport coordinates, dimensions and scale must be finite")
        if min(self.width_mm, self.height_mm, self.scale) <= 0:
            raise ValueError("Viewport dimensions and scale must be positive")

    @property
    def mm_per_m(self) -> float:
        """월드 1m를 표현하는 도면 길이(mm)."""
        return 1000.0 / self.scale

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        return self.x_mm, self.y_mm, self.x_mm + self.width_mm, self.y_mm + self.height_mm


@dataclass(frozen=True, slots=True)
class SheetLayout:
    """도면 크기, 뷰포트 및 하단 표제·범례 영역."""

    size: SheetSize = SheetSize.A1
    margin_mm: float = 10.0
    title_height_mm: float = 30.0
    legend_height_mm: float = 20.0
    plan_viewport: Viewport | None = None
    profile_viewport: Viewport | None = None
    show_title_block: bool = True
    show_legend: bool = True
    show_scale_bar: bool = True
    show_north_arrow: bool = True
    title: str = "PLAN AND PROFILE"
    project_name: str = ""
    drawing_number: str = ""
    date: str = ""
    designer: str = ""

    def __post_init__(self):
        for value in (self.margin_mm, self.title_height_mm, self.legend_height_mm):
            if not math.isfinite(value) or value < 0:
                raise ValueError("Margins and footer heights must be finite and nonnegative")
        x, y, w, h = self.plot_area
        if w <= 0 or h <= self.footer_height_mm:
            raise ValueError("Sheet margins and footer must leave room for drawing")
        viewports = tuple(vp for vp in (self.plan_viewport, self.profile_viewport) if vp is not None)
        for viewport in viewports:
            left, bottom, right, top = viewport.bounds
            if (left < x - 1e-8 or bottom < y + self.footer_height_mm - 1e-8
                    or right > x + w + 1e-8 or top > y + h + 1e-8):
                raise ValueError("Viewport must fit inside the sheet above the footer")
        if len(viewports) == 2:
            a, b = (vp.bounds for vp in viewports)
            if min(a[2], b[2]) - max(a[0], b[0]) > 1e-8 and min(a[3], b[3]) - max(a[1], b[1]) > 1e-8:
                raise ValueError("Plan and profile viewports must not overlap")

    @property
    def footer_height_mm(self) -> float:
        title = self.title_height_mm if self.show_title_block else 0.0
        legend = self.legend_height_mm if self.show_legend else 0.0
        scale_bar = 9.0 if self.show_scale_bar else 0.0
        return max(title, legend + scale_bar)

    @property
    def plot_area(self) -> tuple[float, float, float, float]:
        margin = self.margin_mm
        return margin, margin, self.size.width_mm - 2 * margin, self.size.height_mm - 2 * margin

    @classmethod
    def standard_a1(cls, **options) -> SheetLayout:
        return cls.custom(SheetSize.A1, **options)

    @classmethod
    def standard_a3(cls, **options) -> SheetLayout:
        sizes = {"margin_mm": 5.0, "title_height_mm": 20.0, "legend_height_mm": 15.0, **options}
        sizes.setdefault("plan_scale", 1000)
        sizes.setdefault("profile_scale", 1000)
        return cls.custom(SheetSize.A3, **sizes)

    @classmethod
    def custom(
        cls, size: SheetSize, plan_ratio: float = 0.4, profile_ratio: float = 0.6, *,
        plan_scale: float = 500, profile_scale: float = 500, viewport_gap_mm: float = 6, **options,
    ) -> SheetLayout:
        """하단에 종단도를 배치하고 남은 높이를 주어진 비율로 나눈다."""
        ratios = plan_ratio, profile_ratio
        if not all(math.isfinite(ratio) and ratio >= 0 for ratio in ratios) or not any(ratios):
            raise ValueError("Viewport ratios must be finite, nonnegative and not both zero")
        if not math.isfinite(viewport_gap_mm) or viewport_gap_mm < 0:
            raise ValueError("viewport_gap_mm must be finite and nonnegative")
        layout = cls(size=size, **options)
        x, y, width, height = layout.plot_area
        gap = viewport_gap_mm if all(ratios) else 0.0
        height -= layout.footer_height_mm + gap
        if height <= 0:
            raise ValueError("Sheet must leave space for the viewports")
        y += layout.footer_height_mm
        # 두 비율의 합을 1로 정규화한다.
        profile_height = height * (profile_ratio / sum(ratios))
        plan_height = height - profile_height
        profile = Viewport("Profile", x, y, width, profile_height, profile_scale) if profile_ratio else None
        plan = Viewport("Plan", x, y + profile_height + gap, width, plan_height, plan_scale) if plan_ratio else None
        return replace(layout, plan_viewport=plan, profile_viewport=profile)
