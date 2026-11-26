from enum import Enum


class PipeShape(Enum):
    """관의 내측 단면 형상."""

    CIRCULAR = "Circular"
    ELLIPTICAL = "Elliptical"
    RECTANGULAR = "Rectangular"
    EGG = "Egg"


class PipeMaterial(Enum):
    """관 재질."""

    RCP = "RCP"
    CMP = "CMP"
    PVC = "PVC"
    HDPE = "HDPE"
    CONCRETE = "Concrete"


class StructureType(Enum):
    """관망 접속부의 구조물 유형."""

    MANHOLE = "Manhole"
    INLET = "Inlet"
    HEADWALL = "Headwall"
    END_SECTION = "EndSection"
    JUNCTION = "Junction"
    NULL = "Null"
