from __future__ import annotations

from dataclasses import dataclass, replace

from myalignment.alignment.style.display_rule import AlignmentComponent, DisplayRule, ViewType


@dataclass(frozen=True, slots=True)
class AlignmentStyle:
    """선형 구성요소와 뷰에 따른 표시 스타일."""

    name: str = "Basic"
    description: str = ""
    display_rules: tuple[DisplayRule, ...] = ()

    def get_rule(self, component: AlignmentComponent, view: ViewType) -> DisplayRule | None:
        return next(
            (rule for rule in self.display_rules if rule.component == component and rule.view == view),
            None,
        )

    def is_visible(self, component: AlignmentComponent, view: ViewType) -> bool:
        rule = self.get_rule(component, view)
        return rule.visible if rule else False

    def color_of(self, component: AlignmentComponent, view: ViewType) -> int:
        rule = self.get_rule(component, view)
        return rule.color if rule else 256

    def with_rule(self, rule: DisplayRule) -> AlignmentStyle:
        style = self.without_rule(rule.component, rule.view)
        return replace(style, display_rules=style.display_rules + (rule,))

    def without_rule(self, component: AlignmentComponent, view: ViewType) -> AlignmentStyle:
        return replace(
            self,
            display_rules=tuple(
                rule for rule in self.display_rules
                if (rule.component, rule.view) != (component, view)
            ),
        )

    @classmethod
    def basic(cls) -> AlignmentStyle:
        """평면 뷰의 직선, 곡선, 완화곡선, 진행 방향 화살표를 표시한다."""
        return cls(
            name="Basic",
            display_rules=tuple(
                DisplayRule(component, ViewType.PLAN)
                for component in (
                    AlignmentComponent.LINE,
                    AlignmentComponent.CURVE,
                    AlignmentComponent.SPIRAL,
                    AlignmentComponent.ARROW,
                )
            ),
        )

    @classmethod
    def design_only(cls) -> AlignmentStyle:
        """평면 뷰에서 직선과 곡선을 표시한다."""
        return cls(
            name="Design Only",
            display_rules=(
                DisplayRule(AlignmentComponent.LINE, ViewType.PLAN),
                DisplayRule(AlignmentComponent.CURVE, ViewType.PLAN),
                DisplayRule(AlignmentComponent.ARROW, ViewType.PLAN, visible=False),
            ),
        )
