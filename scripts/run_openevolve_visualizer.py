"""
Run OpenEvolve's Flask visualizer using a vendored clone under third_party/openevolve.

Must execute with cwd = openevolve's scripts/ so Flask finds templates/ and static/.
Uses this repo's Python (uv venv), not a separate venv inside third_party.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLONE_ROOT = REPO_ROOT / "third_party" / "openevolve"
SCRIPT_DIR = CLONE_ROOT / "scripts"
VISUALIZER = SCRIPT_DIR / "visualizer.py"


def main() -> int:
    if not VISUALIZER.is_file():
        print(
            "找不到 OpenEvolve visualizer。請在專案根目錄執行一次：\n"
            "  git clone --depth 1 "
            "https://github.com/algorithmicsuperintelligence/openevolve.git "
            "third_party/openevolve\n",
            file=sys.stderr,
        )
        return 2

    args = list(sys.argv[1:])
    if "--path" not in args:
        args = [
            "--path",
            str((REPO_ROOT / "config" / "openevolve_output").resolve()),
            *args,
        ]
    else:
        i = args.index("--path")
        if i + 1 < len(args):
            p = Path(args[i + 1])
            if not p.is_absolute():
                args[i + 1] = str((REPO_ROOT / p).resolve())

    cmd = [sys.executable, str(VISUALIZER), *args]
    return int(subprocess.call(cmd, cwd=str(SCRIPT_DIR)))


if __name__ == "__main__":
    raise SystemExit(main())
