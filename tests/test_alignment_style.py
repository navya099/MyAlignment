from dataclasses import FrozenInstanceError

import pytest

from myalignment.alignment.alignment import Alignment
from myalignment.alignment.alignment_builder import AlignmentBuilder
from myalignment.alignment.style.alignment_style import AlignmentStyle
from myalignment.alignment.style.display_rule import AlignmentComponent, DisplayRule, ViewType
from myalignment.alignment.style.label_style import LabelComponent, LabelComponentType, LabelStyle
from myalignment.rail.rail_alignment import RailAlignment


def test_style_rules_are_keyed_by_component_and_view():
    line = AlignmentComponent.LINE
    plan, model = ViewType.PLAN, ViewType.MODEL
    basic = AlignmentStyle.basic()
    plan_rule = DisplayRule(line, plan, visible=False, color=1, linetype="Dashed", lineweight=0.25)
    model_rule = DisplayRule(line, model, color=2)
    custom = basic.with_rule(plan_rule).with_rule(model_rule)

    assert basic.is_visible(line, plan)
    assert custom.get_rule(line, plan) == plan_rule
    assert not custom.is_visible(line, plan)
    assert custom.color_of(line, model) == 2
    assert len(custom.display_rules) == len(basic.display_rules) + 1
    removed = custom.without_rule(line, plan)
    assert removed.get_rule(line, plan) is None
    assert removed.color_of(line, plan) == 256
    assert removed.get_rule(line, model) == model_rule


def test_style_presets():
    basic, design = AlignmentStyle.basic(), AlignmentStyle.design_only()
    assert {component for component in AlignmentComponent if basic.is_visible(component, ViewType.PLAN)} == {
        AlignmentComponent.LINE, AlignmentComponent.CURVE, AlignmentComponent.SPIRAL, AlignmentComponent.ARROW,
    }
    assert {component for component in AlignmentComponent if design.is_visible(component, ViewType.PLAN)} == {
        AlignmentComponent.LINE, AlignmentComponent.CURVE,
    }
    assert not basic.is_visible(AlignmentComponent.LINE, ViewType.PROFILE)


@pytest.mark.parametrize("color", [-1, 257, 1.5])
def test_display_rule_rejects_invalid_aci_color(color):
    with pytest.raises(ValueError, match="ACI"):
        DisplayRule(AlignmentComponent.LINE, ViewType.PLAN, color=color)


@pytest.mark.parametrize("rail", [False, True])
def test_builder_and_alignment_support_styles(rail):
    builder = AlignmentBuilder("Main").with_pi_coords([(0, 0), (100, 0)])
    if rail:
        builder.as_rail_alignment(gauge=1.6)

    original = builder.build()
    assert original.style == AlignmentStyle.basic()
    assert Alignment().style == original.style
    style = AlignmentStyle.design_only()
    styled = original.with_style(style)
    assert styled.style is style
    assert original.style.name == "Basic"
    assert styled.entities is original.entities
    assert isinstance(styled, RailAlignment) is rail
    if rail:
        assert styled.gauge == 1.6
    assert builder.with_style(style).build().style is style


def test_label_style_appends_components_immutably():
    text = LabelComponent(LabelComponentType.TEXT, "<[Station Value]>", height=2.5)
    tick = LabelComponent(LabelComponentType.TICK, visible=False)
    original = LabelStyle("Station").with_component(text)
    changed = original.with_component(tick)

    assert original.components == (text,)
    assert changed.components == (text, tick)
    with pytest.raises(FrozenInstanceError):
        text.visible = False
