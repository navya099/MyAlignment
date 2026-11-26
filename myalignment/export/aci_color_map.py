from colorsys import hsv_to_rgb


_ACI_COLORS = (
    "#CCCCCC", "#FF0000", "#FFFF00", "#00FF00", "#00FFFF",
    "#0000FF", "#FF00FF", "#FFFFFF", "#808080", "#C0C0C0",
)


class AciColorMap:
    """AutoCAD 색상 인덱스의 CSS 팔레트."""

    @staticmethod
    def to_css(aci: int, dark_mode: bool = False) -> str:
        """ACI 인덱스를 CSS 색으로 변환한다."""
        if aci in (0, 7, 256):
            return "#FFFFFF" if dark_mode else "#000000"
        if 0 <= aci < len(_ACI_COLORS):
            return _ACI_COLORS[aci]
        if 10 <= aci <= 249:
            hue, shade = divmod(aci - 10, 10)
            value = (255, 165, 127, 76, 38)[shade // 2]
            rgb = hsv_to_rgb(hue / 24, 0.5 if shade % 2 else 1.0, value)
            return "#" + "".join(f"{int(channel):02X}" for channel in rgb)
        if 250 <= aci <= 255:
            gray = (51, 80, 105, 130, 190, 255)[aci - 250]
            return f"#{gray:02X}{gray:02X}{gray:02X}"
        return "#CCCCCC"
