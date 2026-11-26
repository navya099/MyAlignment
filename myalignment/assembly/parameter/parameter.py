from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import TypeAlias

from myalignment.assembly.parameter.parameter_type import ParameterType

ParameterValue: TypeAlias = float | int | str | bool | None


@dataclass(frozen=True, slots=True)
class Parameter:
    """기본값, 허용 범위와 표시 정보를 가진 불변 파라미터."""

    name: str
    param_type: ParameterType = ParameterType.INPUT
    default: ParameterValue = 0.0
    value: ParameterValue = None
    display_name: str = ""
    unit: str = ""
    min_value: float | None = None
    max_value: float | None = None
    options: tuple[ParameterValue, ...] = ()
    expression: str = ""
    description: str = ""

    def __post_init__(self):
        if not self.name.isidentifier():
            raise ValueError("Parameter name must be an identifier")
        if not isinstance(self.param_type, ParameterType):
            raise ValueError("param_type must be a ParameterType")
        object.__setattr__(self, "options", tuple(self.options))
        if self.param_type is ParameterType.ENUM and not self.options:
            raise ValueError(f"{self.name}: enum options are required")
        if any(type(option) not in (str, bool, int, float) for option in self.options):
            raise ValueError(f"{self.name}: invalid enum option")
        if self.param_type is ParameterType.COMPUTED and not self.expression.strip():
            raise ValueError(f"{self.name}: computed expression is required")
        if self.expression and self.param_type not in (ParameterType.COMPUTED, ParameterType.OUTPUT):
            raise ValueError(f"{self.name}: only computed and output parameters accept expressions")
        for bound in (self.min_value, self.max_value):
            if bound is not None and not math.isfinite(bound):
                raise ValueError(f"{self.name}: bounds must be finite")
        if self.min_value is not None and self.max_value is not None and self.min_value > self.max_value:
            raise ValueError(f"{self.name}: minimum exceeds maximum")
        if not self.display_name:
            object.__setattr__(self, "display_name", self.name)
        self._validate(self.default, default=True)
        if self.value is not None:
            self._validate(self.value)

    def _validate(self, value: ParameterValue, *, default: bool = False) -> None:
        if default and self.expression:
            # An unevaluated field may carry a placeholder default.
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
                raise ValueError(f"{self.name}: formula defaults must be finite numbers")
            return
        if value is None and self.param_type in (ParameterType.TARGET, ParameterType.OUTPUT):
            return
        if type(value) not in (str, bool, int, float):
            raise ValueError(f"{self.name}: invalid parameter value")
        if type(value) in (float, int) and not math.isfinite(value):
            raise ValueError(f"{self.name}: value must be finite")
        if self.param_type is ParameterType.ENUM and not any(
            type(value) is type(option) and value == option for option in self.options
        ):
            raise ValueError(f"{self.name}: value must be one of {self.options}")
        if self.param_type is ParameterType.TARGET and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"{self.name}: target must be a logical name")
        if self.min_value is not None or self.max_value is not None:
            if type(value) not in (int, float):
                raise ValueError(f"{self.name}: value must be numeric")
            if self.min_value is not None and value < self.min_value:
                raise ValueError(f"{self.name}: value below minimum {self.min_value}")
            if self.max_value is not None and value > self.max_value:
                raise ValueError(f"{self.name}: value above maximum {self.max_value}")

    @property
    def current(self) -> ParameterValue:
        """값을 설정하지 않았으면 기본값을 반환한다."""
        return self.default if self.value is None else self.value

    def with_value(self, value: ParameterValue) -> Parameter:
        """입력값을 변경하거나 None으로 기본값을 복원한다."""
        if self.param_type in (ParameterType.OUTPUT, ParameterType.COMPUTED):
            raise ValueError(f"{self.name}: parameter is read-only")
        return replace(self, value=value)
