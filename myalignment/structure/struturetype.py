# structure/structure_type.py
from enum import Enum


class StructureType(Enum):
    """구조물 종류 (C3D 호환)."""
    BRIDGE = "교량"
    TUNNEL = "터널"
    CULVERT = "암거"
    RETAINING_WALL = "옹벽"
    OVERPASS = "과선교"
    UNDERPASS = "지하차도"