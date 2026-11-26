from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass, replace
import math
import operator

from myalignment.assembly.parameter.parameter import Parameter, ParameterValue
from myalignment.assembly.parameter.parameter_type import ParameterType

_BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
           ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
           ast.Pow: operator.pow}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _number(value):
    if type(value) not in (float, int) or not math.isfinite(value):
        raise ValueError("formula values must be finite numbers")
    return float(value)


def _evaluate(node, lookup):
    if isinstance(node, ast.Constant):
        return _number(node.value)
    if isinstance(node, ast.Name):
        return _number(lookup(node.id))
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        return _number(_BINARY[type(node.op)](_evaluate(node.left, lookup), _evaluate(node.right, lookup)))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_evaluate(node.operand, lookup))
    raise ValueError("only arithmetic expressions and variable names are supported")


def _evaluate_formula(expression, lookup):
    try:
        if not isinstance(expression, str):
            raise ValueError("formula must be a string")
        return _evaluate(ast.parse(expression.strip(), mode="eval").body, lookup)
    except (ArithmeticError, SyntaxError, RecursionError) as error:
        raise ValueError(str(error)) from error


@dataclass(frozen=True, slots=True)
class ParameterSet:
    """이름별 조회와 의존성 순서에 따른 수식 계산을 지원한다."""

    parameters: tuple[Parameter, ...] = ()

    def __post_init__(self):
        parameters = tuple(self.parameters)
        if len({p.name for p in parameters}) != len(parameters):
            raise ValueError("Duplicate parameter name")
        object.__setattr__(self, "parameters", parameters)

    def __len__(self) -> int:
        return len(self.parameters)

    def __iter__(self):
        return iter(self.parameters)

    def get(self, name: str) -> Parameter | None:
        return next((p for p in self if p.name == name), None)

    def get_value(self, name: str, default: ParameterValue = None) -> ParameterValue:
        param = self.get(name)
        return param.current if param is not None else default

    def set_value(self, name: str, value: ParameterValue) -> ParameterSet:
        return self.update_values(**{name: value})

    def update_values(self, **kwargs: ParameterValue) -> ParameterSet:
        if not kwargs:
            return self
        for name in kwargs:
            if self.get(name) is None:
                raise KeyError(f"Unknown parameter {name!r}")
        return ParameterSet(tuple(
            p.with_value(kwargs[p.name]) if p.name in kwargs else replace(p, value=None) if p.expression else p
            for p in self
        ))

    def evaluate_computed(self, context: Mapping[str, ParameterValue] | None = None) -> ParameterSet:
        """수식과 연결된 출력값을 계산하고 잘못된 참조나 순환을 보고한다."""
        variables = context or {}
        parameters = {p.name: p for p in self}
        resolved = {}
        active = set()

        def lookup(name):
            param = parameters.get(name)
            if param is None:
                if name in variables:
                    return variables[name]
                raise ValueError(f"Unknown formula variable {name!r}")
            if not param.expression:
                return param.current
            if name in active:
                raise ValueError(f"Circular parameter dependency at {name!r}")
            if name not in resolved:
                active.add(name)
                try:
                    resolved[name] = replace(param, value=_evaluate_formula(param.expression, lookup))
                except ValueError as error:
                    raise ValueError(f"{name}: {error}") from error
                finally:
                    active.remove(name)
            return resolved[name].current

        for p in self:
            if p.expression:
                lookup(p.name)
        return ParameterSet(tuple(resolved.get(p.name, p) for p in self))

    def inputs(self) -> dict[str, ParameterValue]:
        return {p.name: p.current for p in self if p.param_type is ParameterType.INPUT}

    def outputs(self) -> dict[str, ParameterValue]:
        return {p.name: p.current for p in self if p.param_type is ParameterType.OUTPUT}
