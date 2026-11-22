"""Run the guide examples against an installed MyAlignment distribution."""

import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def main() -> None:
    docs = Path(__file__).resolve().parents[1] / "docs"
    count = 0
    for guide in sorted(docs.glob("*.md")):
        markdown = guide.read_text(encoding="utf-8")
        for example in re.finditer(r"^```python\n(.*?)^```$", markdown, re.MULTILINE | re.DOTALL):
            line = markdown.count("\n", 0, example.start()) + 1
            with TemporaryDirectory() as directory:
                folder = Path(directory)
                script = folder / "example.py"
                script.write_text(example[1], encoding="utf-8")
                print(f"{guide.name}:{line}", flush=True)
                subprocess.run([sys.executable, "-I", "-X", "utf8", str(script)], cwd=folder, check=True)

                if guide.name == "getting-started.md":
                    for name in ("plan.dxf", "section.dxf", "corridor-3d.dxf"):
                        data = (folder / "output" / name).read_text(encoding="utf-8")
                        if "ENTITIES" not in data.splitlines() or not data.rstrip().endswith("EOF"):
                            raise ValueError(f"Incomplete DXF: {name}")
            count += 1

    print(f"{count} installed package examples passed")


if __name__ == "__main__":
    main()
