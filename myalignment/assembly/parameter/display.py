from myalignment.assembly.parameter.parameter import Parameter
from myalignment.assembly.parameter.parameter_type import ParameterType


def format_parameter(parameter: Parameter) -> str:
    """표시 이름, 값과 단위를 문자열로 만든다."""
    value = parameter.current
    if isinstance(value, float):
        value = f"{value:.3f}"
    unit = f" {parameter.unit}" if parameter.unit and parameter.param_type is not ParameterType.ENUM else ""
    return f"{parameter.display_name}: {value}{unit}"


def show_parameters(subassembly) -> str:
    """서브어셈블리의 현재 파라미터를 줄별로 표시한다."""
    params = getattr(subassembly, "param_set", None)
    if params is None:
        return f"{subassembly.name}: (파라미터 없음)"
    return "\n".join((f"[{subassembly.name}]", *(f"  {format_parameter(p)}" for p in params)))
