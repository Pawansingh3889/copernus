#!/usr/bin/env python3
# This checker stops Windows-style paths like C:/ from getting into the project.
"""No Windows drive-letter paths in code or documentation.

A regression guard. No `C:/` path exists in this repository today, and the
point is to keep it that way: the source system and the checkweigher are both
Windows-attached, so a developer path like `C:/Users/.../export.csv` is a
plausible thing to paste in and an impossible thing for CI, a container, or a
colleague to resolve.

Serial port names (`COM1`) are **not** paths and are not flagged — they are
legitimate configuration for the checkweigher, and they live in `.env`.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from _guard import repo_root, report, require_paths

# A drive letter followed by a separator: C:\ or C:/ — but not a bare "C:".
DRIVE_PATH = re.compile(r"\b[A-Za-z]:[\\/]")

SUFFIXES = {".py", ".md", ".toml", ".yml", ".yaml", ".cfg", ".ini", ".sh", ".example"}
SKIP_PARTS = {".venv", "node_modules", ".git", ".ruff_cache", ".pytest_cache", "__pycache__"}


def check_file(path: Path) -> list[str]:
    violations: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return violations

    for number, line in enumerate(text.splitlines(), start=1):
        if DRIVE_PATH.search(line):
            violations.append(
                f"{path}:{number} — Windows drive path. "
                "Use a relative path or configuration instead."
            )
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=repo_root())
    args = parser.parse_args()

    files = [
        p
        for p in sorted(args.root.rglob("*"))
        if p.is_file()
        and p.suffix in SUFFIXES
        and not any(part in SKIP_PARTS for part in p.parts)
        # This guard's own regex and docstring describe the pattern it hunts.
        and p.resolve() != Path(__file__).resolve()
    ]
    require_paths(files, "source and documentation files")

    violations: list[str] = []
    for path in files:
        violations.extend(check_file(path))

    return report("no Windows paths", violations, len(files))


if __name__ == "__main__":
    raise SystemExit(main())
