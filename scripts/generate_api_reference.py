"""Generate Markdown pages for top-level classes and selected public functions."""

import ast
from collections import defaultdict
from pathlib import Path, PurePosixPath
from posixpath import relpath

import mkdocs_gen_files


PUBLIC_FUNCTIONS = {"myalignment.utils.coordinate_utils.convert_coordinates"}


def generate() -> None:
    root = Path(__file__).resolve().parents[1]
    reference = PurePosixPath("reference")
    groups = defaultdict(list)
    for source in sorted((root / "myalignment").rglob("*.py")):
        relative = source.relative_to(root)
        if relative.parts[1] == "examples":
            continue

        module_parts = relative.with_suffix("").parts
        if module_parts[-1] == "__init__":
            module_parts = module_parts[:-1]
        if any(part.startswith("_") for part in module_parts):
            continue

        module = ".".join(module_parts)
        parsed = ast.parse(source.read_text(encoding="utf-8-sig"), filename=str(relative))
        for node in parsed.body:
            if not isinstance(node, (ast.ClassDef, ast.FunctionDef)) or node.name.startswith("_"):
                continue
            qualified_name = f"{module}.{node.name}"
            if isinstance(node, ast.FunctionDef) and qualified_name not in PUBLIC_FUNCTIONS:
                continue
            page = reference.joinpath(*module_parts[1:], f"{node.name}.md")
            group = relative.parts[1] if len(relative.parts) > 2 else "myalignment"
            groups[group].append((node.name, qualified_name, page))
            with mkdocs_gen_files.open(page, "w") as output:
                print(f"---\ntitle: {node.name}\n---\n", file=output)
                package_link = relpath(reference / group / "index.md", page.parent)
                print(f"[패키지 API 목록]({package_link})\n", file=output)
                print(f"`{qualified_name}`\n", file=output)
                print(f"::: {qualified_name}", file=output)

    with mkdocs_gen_files.open(reference / "index.md", "w") as output:
        print("# API 레퍼런스\n", file=output)
        print("공개 클래스의 생성자, 메서드, 속성과 주요 함수를 패키지별로 찾을 수 있습니다. "
              "각 페이지 상단에 전체 Python 경로가 표시됩니다.\n", file=output)
        print("작업 흐름과 실행 예제는 [시작하기](../getting-started.md)와 "
              "[모듈 찾아보기](../modules.md)에 있습니다.\n", file=output)
        print("| 패키지 | 항목 수 |\n| --- | ---: |", file=output)
        for group, members in sorted(groups.items()):
            print(f"| [`{group}`]({group}/index.md) | {len(members)} |", file=output)
            package_page = reference / group / "index.md"
            with mkdocs_gen_files.open(package_page, "w") as index:
                package = "myalignment" if group == "myalignment" else f"myalignment.{group}"
                print(f"# `{package}`\n", file=index)
                print("[API 레퍼런스](../index.md)\n", file=index)
                for name, qualified_name, page in sorted(members, key=lambda entry: (entry[0].casefold(), entry[1])):
                    print(f"- [`{name}`]({relpath(page, package_page.parent)}) · `{qualified_name}`", file=index)


generate()
