#!/usr/bin/env python3
"""No executable Python inside Markdown.

This repository began as four design documents with two working scripts pasted
inside them. Code in a Markdown fence cannot be imported, linted, tested, or
run. It has no tests by construction, and it drifts from whatever is actually
executing — silently, because nothing compares the two. One of the pasted
scripts referenced a source path that no longer existed anywhere in the tree.

Scripts live in `scripts/`. Documentation links to them.

Short illustrative snippets are still fine: a fence under `--min-lines` is a
worked example, not a program. The line is drawn at "long enough that somebody
will copy and run it".
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from _guard import repo_root, report, require_paths

FENCE = re.compile(r"^```(\w*)\s*$")
DEFAULT_MIN_LINES = 12

# Markers that mean "this is a program", not "this is an example expression".
EXECUTABLE_MARKERS = (
    "import ",
    "from ",
    "def ",
    "class ",
    "__name__",
)


def python_blocks(text: str) -> list[tuple[int, list[str]]]:
    """Return (start_line, body_lines) for each ```python fence.

    Fences of other languages are tracked so that their contents are never
    mistaken for Python, but only Python ones are returned.
    """
    blocks: list[tuple[int, list[str]]] = []
    language: str | None = None
    start = 0
    body: list[str] = []

    for number, line in enumerate(text.splitlines(), start=1):
        match = FENCE.match(line)

        if match is None:
            if language is not None:
                body.append(line)
            continue

        if language is None:
            # Opening fence.
            language = (match.group(1) or "text").lower()
            start, body = number, []
        else:
            # Closing fence.
            if language in {"python", "py"}:
                blocks.append((start, body))
            language, body = None, []

    return blocks


def check_file(path: Path, min_lines: int) -> list[str]:
    violations: list[str] = []
    for start, body in python_blocks(path.read_text(encoding="utf-8")):
        code = [line for line in body if line.strip()]
        if len(code) < min_lines:
            continue
        if not any(marker in line for line in code for marker in EXECUTABLE_MARKERS):
            continue
        violations.append(
            f"{path}:{start} — {len(code)}-line executable Python block. "
            "Move it to scripts/ and link to it."
        )
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=repo_root())
    parser.add_argument("--min-lines", type=int, default=DEFAULT_MIN_LINES)
    args = parser.parse_args()

    docs = [
        p
        for p in sorted(args.root.rglob("*.md"))
        if not any(part in {".venv", "node_modules", ".git"} for part in p.parts)
    ]
    require_paths(docs, "Markdown files")

    violations: list[str] = []
    for path in docs:
        violations.extend(check_file(path, args.min_lines))

    return report("no Python in Markdown", violations, len(docs))


if __name__ == "__main__":
    raise SystemExit(main())
