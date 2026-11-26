from collections.abc import Iterable
from html import escape
import os
from pathlib import Path
from urllib.parse import quote


class SvgGallery:
    """SVG 파일을 한 HTML 페이지에서 비교할 수 있게 표시한다."""

    @staticmethod
    def create(
        svg_paths: Iterable[tuple[str, str | Path]], html_path: str | Path, title: str = "SVG Gallery",
    ) -> None:
        destination = Path(html_path)
        cards = []
        for name, svg_path in svg_paths:
            relative = Path(os.path.relpath(svg_path, destination.parent)).as_posix()
            url = quote(relative, safe="/")
            label = escape(name, quote=True)
            cards.append(
                f'<figure><figcaption>{label}</figcaption><img src="{url}" alt="{label}" loading="lazy"></figure>'
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(_GALLERY.format(title=escape(title), cards="\n".join(cards)), encoding="utf-8")


_GALLERY = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ font-family: system-ui, sans-serif; background: #f1f4f6; color: #17232d; }}
body {{ margin: 24px; }}
h1 {{ margin: 0 0 24px; font-size: 1.5rem; overflow-wrap: anywhere; }}
main {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 360px), 1fr)); gap: 16px; }}
figure {{ margin: 0; background: white; border: 1px solid #d2dbe1; border-radius: 8px; overflow: hidden; }}
figcaption {{ padding: 12px 16px; border-bottom: 1px solid #d2dbe1; overflow-wrap: anywhere; }}
img {{ display: block; width: 100%; height: auto; }}
</style>
</head>
<body>
<h1>{title}</h1>
<main>{cards}</main>
</body>
</html>
"""
