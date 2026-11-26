import json

from myalignment.export.aci_color_map import AciColorMap
from myalignment.render.primitives_3d import Primitive3D, PrimitiveType3D
from myalignment.render.scene_3d import Scene3D



class Scene3DSerializer:
    """Scene3D를 버전이 지정된 3D 뷰어 JSON 형식으로 변환한다."""

    @classmethod
    def to_dict(cls, scene: Scene3D) -> dict:
        primitives = []
        for primitive in scene.primitives:
            encoded = cls._primitive_to_dict(primitive)
            if encoded is not None:
                primitives.append(encoded)
        return {"version": "1.0", "primitives": primitives, "metadata": dict(scene.metadata)}

    @classmethod
    def to_json(cls, scene: Scene3D, indent: int | None = 2) -> str:
        return json.dumps(cls.to_dict(scene), indent=indent, ensure_ascii=False, allow_nan=False)

    @classmethod
    def _primitive_to_dict(cls, primitive: Primitive3D) -> dict | None:
        style = primitive.style
        if not style.visible:
            return None
        attributes = {"color": cls._color_to_hex(style.color), "layer": style.layer or "0"}
        kind = primitive.type
        if kind in (PrimitiveType3D.TRIANGLE, PrimitiveType3D.MESH) and style.opacity != 1:
            attributes["opacity"] = style.opacity
        points = [[point.x, point.y, point.z] for point in primitive.points]
        if kind is PrimitiveType3D.POINT:
            return {"type": "point", "position": points[0], **attributes}
        if kind is PrimitiveType3D.LINE:
            return {"type": "line", "start": points[0], "end": points[1], **attributes}
        if kind is PrimitiveType3D.POLYLINE:
            return {"type": "polyline", "points": points, "closed": primitive.closed, **attributes}
        if kind is PrimitiveType3D.TRIANGLE:
            return {"type": "mesh", "vertices": points, "indices": [[0, 1, 2]], **attributes}
        if kind is PrimitiveType3D.MESH and primitive.indices:
            return {
                "type": "mesh", "vertices": points,
                "indices": [list(face) for face in primitive.indices], **attributes,
            }
        return None

    @staticmethod
    def _color_to_hex(aci_color: int) -> str:
        return "#CCCCCC" if aci_color in (0, 256) else AciColorMap.to_css(aci_color, dark_mode=True)
